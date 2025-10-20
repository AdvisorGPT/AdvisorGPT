# GPT Drive Connector (Railway deploy) — OAuth via GPT Actions

A tiny FastAPI service that lets your custom GPT read **one specific Google Drive folder** and **extract text** from **Google Docs** and **PDFs**.

- **Auth model:** Your GPT uses **OAuth (Google)**. The GPT platform will attach a **Bearer token** for Google to every API call. This service accepts that token and calls the Google Drive API on your behalf.
- **Scope:** `https://www.googleapis.com/auth/drive.readonly`
- **Restriction:** Access is **locked to a single folder** (`ALLOWED_FOLDER_ID`).

## What it can do
- List files in the allowed folder
- Search by filename (within the allowed folder)
- Get file metadata
- Extract text from:
  - **Google Docs** (by exporting as `text/plain`)
  - **PDF files** (download + parse with `pdfminer.six`)

## Quick Start

### 1) Create a Google Cloud OAuth Client (Web application)
1. Create / pick a GCP project.
2. Enable **Google Drive API**.
3. Create **OAuth 2.0 Client ID** of type **Web application**.
4. You will later add your GPT’s **Callback URL** to the **Authorized redirect URIs** (after you add the Action in GPT Builder).

### 2) Create your GPT Action (in GPT Builder)
1. Add **Action** → upload `openapi.yaml` from this repo.
2. **Authentication**: choose **OAuth (Authorization Code)**.
3. **Authorization URL**: `https://accounts.google.com/o/oauth2/auth`
4. **Token URL**: `https://oauth2.googleapis.com/token`
5. **Scopes** (space-separated): `https://www.googleapis.com/auth/drive.readonly`
6. Save. The Builder will show a **Callback URL** — copy it.
7. Go back to your Google OAuth client and paste this Callback URL into **Authorized redirect URIs**. Save.
8. Back in Builder, re-save the Action so OAuth finalizes.

> The GPT platform will now manage refresh tokens and attach a fresh **Bearer** token to each request.

### 3) Restrict to a single Drive folder
Find your target folder’s **ID** in Google Drive (open the folder in the browser, copy the long alphanumeric ID from the URL).

Set env variable:
```
ALLOWED_FOLDER_ID=1eqOnCV_Ykf1yTylCmBEmdN9AllPaLuzE
```

### 4) Deploy on **Railway**

**Option A: Quick (Deploy from GitHub)**
- Push this repo to GitHub.
- Create a new Railway project → **Deploy from GitHub**.
- Railway will auto-detect the `Dockerfile`.
- Add the following environment variables in Railway:
  - `ALLOWED_FOLDER_ID=<your-folder-id>`
  - `PORT=8080` (Railway sets this automatically, but we default to 8080 in `CMD`)
- Deploy.

**Option B: Railway CLI**
```bash
railway init
railway up
railway variables set ALLOWED_FOLDER_ID=<your-folder-id>
```

### 5) Test locally (optional)
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r server/requirements.txt
export ALLOWED_FOLDER_ID=<your-folder-id>
uvicorn server.main:app --reload --port 8080
```

Open http://localhost:8080/docs to see the endpoints (they’ll require a Bearer token when used by your GPT).

---

## Endpoints (summary)

- `GET /health` → health check
- `GET /drive/files?folderId=...&pageSize=...` → list files (defaults to `ALLOWED_FOLDER_ID`)
- `GET /drive/search?q=...&pageSize=...` → search files by name (within allowed folder)
- `GET /file/{id}/meta` → get file metadata (only if under allowed folder)
- `GET /file/{id}/text` → **extract text** from Google Doc or PDF (only if under allowed folder)

> All endpoints expect **Authorization: Bearer <google_access_token>** (managed by your GPT Action after OAuth). You do **not** need to implement your own OAuth redirects here; the GPT platform handles token refresh.

---

## Security & Notes

- **Folder lock**: Every operation is filtered and/or verified against `ALLOWED_FOLDER_ID`.
- **Least privilege**: Use `drive.readonly` scope only.
- **No token storage**: This server **does not store** tokens. It depends on the GPT platform to send valid Bearer tokens.
- For PDFs, text extraction uses `pdfminer.six` (best-effort). Formatting is not preserved; the goal is to give your GPT clean text.
- For Google Docs, we export as **plain text**. If you need rich structure, extend the code to use the **Google Docs API**.

---

## Environment Variables

```
ALLOWED_FOLDER_ID=<the-only-folder-this-service-can-read>
PORT=8080  # optional for local dev; Railway injects PORT
```

No Google client secrets are required here because **the GPT platform** manages OAuth and supplies the **Bearer** token for Google to your API.

---

## OpenAPI for GPT Actions

See `openapi.yaml`. It declares an OAuth2 security scheme and `authorizationCode` flow pointing to Google’s endpoints.

---

## License

MIT


---

## 🔁 Shared-Access Mode (Service Account) — Recommended for a GPT you share with others

If you want **anyone using your GPT** to access the **same** Google Drive folder (without each person doing OAuth), switch to **Service Account** mode:

### 1) Create a Service Account & Key
1. In Google Cloud → IAM & Admin → **Service Accounts** → Create.
2. Grant no roles for now (Drive API access will be via key + sharing).
3. Create a **JSON key** and keep it safe.

### 2) Share your target Drive folder with the Service Account
- In Google Drive, open the folder `1eqOnCV_Ykf1yTylCmBEmdN9AllPaLuzE`.
- Click **Share** → add the service account email (looks like `service-account-name@project-id.iam.gserviceaccount.com`) as **Viewer** (or **Content manager** if you need export of large files).
- For **Shared Drives**, add the service account as a **member** to the drive/team.

### 3) Configure the app
Set environment variables (Railway → Variables):
```
AUTH_MODE=SERVICE_ACCOUNT
ALLOWED_FOLDER_ID=1eqOnCV_Ykf1yTylCmBEmdN9AllPaLuzE
GOOGLE_SERVICE_ACCOUNT_JSON=<paste the whole JSON key here>
```
> The app will read the JSON from `GOOGLE_SERVICE_ACCOUNT_JSON` so you don't need to mount a file.

### 4) Update `openapi.yaml` auth
In **Service Account mode**, your API no longer needs Google OAuth from the GPT. Protect it with a simple API key:

- In GPT Builder → Action → set **Authentication** to **API Key**.
- Header name: `x-api-key`
- In Railway, set: `API_KEY_FOR_GPT=<a-long-random-string>`
- Replace in `openapi.yaml`: add an `apiKey` scheme and remove OAuth security requirement (or keep both; the server accepts API key).

We've already added dual support in code below. See **`server/google_sa.py`** and **`server/main.py`** updates.

---
