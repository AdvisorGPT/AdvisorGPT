import io, json, os
from typing import Tuple, Dict, Any

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

def build_sa_drive():
    raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    if not raw:
        raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON env var is required in SERVICE_ACCOUNT mode")
    info = json.loads(raw)
    creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    return build("drive", "v3", credentials=creds, cache_discovery=False)

def list_files_in_folder(drive, folder_id: str, page_size: int = 25):
    q = f"'{folder_id}' in parents"
    res = drive.files().list(
        q=q,
        pageSize=page_size,
        fields="files(id, name, mimeType, modifiedTime, parents, owners(displayName))"
    ).execute()
    return res.get("files", [])

def search_files_in_folder(drive, folder_id: str, query: str, page_size: int = 25):
    query_escaped = query.replace("'", "\\'")
    q = f"name contains '{query_escaped}' and '{folder_id}' in parents"
    res = drive.files().list(
        q=q,
        pageSize=page_size,
        fields="files(id, name, mimeType, modifiedTime, parents, owners(displayName))"
    ).execute()
    return res.get("files", [])

def get_file_meta(drive, file_id: str) -> Dict[str, Any]:
    return drive.files().get(
        fileId=file_id,
        fields="id, name, mimeType, parents, modifiedTime, size, owners(displayName,emailAddress)"
    ).execute()

def download_file(drive, file_id):
    meta = drive.files().get(fileId=file_id, fields="id, name, mimeType, parents").execute()
    req = drive.files().get_media(fileId=file_id)
    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, req)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    buf.seek(0)
    return meta["name"], meta["mimeType"], buf

def export_google_doc_as_text(drive, file_id):
    meta = drive.files().get(fileId=file_id, fields="id, name, mimeType, parents").execute()
    req = drive.files().export_media(fileId=file_id, mimeType="text/plain")
    content = req.execute()
    return meta["name"], io.BytesIO(content)
