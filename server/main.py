import os
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

AUTH_MODE = os.environ.get("AUTH_MODE", "SERVICE_ACCOUNT").upper()
ALLOWED_FOLDER_ID = os.environ.get("ALLOWED_FOLDER_ID", "").strip()
if not ALLOWED_FOLDER_ID:
    raise RuntimeError("ALLOWED_FOLDER_ID env var is required.")

# OAUTH mode imports
from server.google_client import (
    build_creds_from_bearer, build_drive as build_user_drive,
    list_files_in_folder as user_list, search_files_in_folder as user_search,
    get_file_meta as user_meta, download_file as user_download, export_google_doc_as_text as user_export
)
# SERVICE ACCOUNT mode imports
from server.google_sa import (
    build_sa_drive,
    list_files_in_folder as sa_list, search_files_in_folder as sa_search,
    get_file_meta as sa_meta, download_file as sa_download, export_google_doc_as_text as sa_export
)

from pdfminer.high_level import extract_text

API_KEY = os.environ.get("API_KEY_FOR_GPT", "").strip()  # required in SA mode

app = FastAPI(title="GPT Drive Connector", version="1.1.0")

def require_api_key_if_sa(request: Request):
    if AUTH_MODE == "SERVICE_ACCOUNT":
        if not API_KEY or request.headers.get("x-api-key") != API_KEY:
            raise HTTPException(status_code=401, detail="Invalid or missing x-api-key")

def bearer_token_from_request(request: Request) -> str:
    auth = request.headers.get("authorization") or request.headers.get("Authorization")
    if not auth or not auth.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    return auth.split(" ", 1)[1].strip()

def ensure_in_allowed_folder(drive, meta: dict):
    parents = meta.get("parents", [])
    if ALLOWED_FOLDER_ID not in parents:
        raise HTTPException(status_code=403, detail="File not in allowed folder")

def get_clients(request: Request):
    if AUTH_MODE == "SERVICE_ACCOUNT":
        require_api_key_if_sa(request)
        drive = build_sa_drive()
        ops = dict(list=sa_list, search=sa_search, meta=sa_meta, download=sa_download, export=sa_export)
        return drive, ops
    else:
        token = bearer_token_from_request(request)
        drive = build_user_drive(build_creds_from_bearer(token))
        ops = dict(list=user_list, search=user_search, meta=user_meta, download=user_download, export=user_export)
        return drive, ops

@app.get("/health")
def health():
    return {"ok": True, "authMode": AUTH_MODE}

@app.get("/drive/files")
def list_files(request: Request, folderId: Optional[str] = None, pageSize: int = 25):
    drive, ops = get_clients(request)
    folder = folderId or ALLOWED_FOLDER_ID
    files = ops["list"](drive, folder, page_size=pageSize)
    return {"files": files}

@app.get("/drive/search")
def search_files(request: Request, q: str, pageSize: int = 25):
    drive, ops = get_clients(request)
    files = ops["search"](drive, ALLOWED_FOLDER_ID, q, page_size=pageSize)
    return {"files": files}

@app.get("/file/{file_id}/meta")
def file_meta(request: Request, file_id: str):
    drive, ops = get_clients(request)
    meta = ops["meta"](drive, file_id)
    ensure_in_allowed_folder(drive, meta)
    return meta

@app.get("/file/{file_id}/text")
def file_text(request: Request, file_id: str):
    drive, ops = get_clients(request)
    meta = ops["meta"](drive, file_id)
    ensure_in_allowed_folder(drive, meta)
    mime = meta.get("mimeType", "")

    if mime == "application/vnd.google-apps.document":
        name, stream = ops["export"](drive, file_id)
        text = stream.read().decode("utf-8", errors="ignore")
        return JSONResponse({"fileId": file_id, "name": name, "mimeType": mime, "text": text})

    if mime == "application/pdf":
        name, _, stream = ops["download"](drive, file_id)
        text = extract_text(stream)
        return JSONResponse({"fileId": file_id, "name": name, "mimeType": mime, "text": text})

    raise HTTPException(status_code=415, detail=f"Unsupported mimeType for text extraction: {mime}")
