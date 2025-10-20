import io
from typing import Tuple, Dict, Any

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

def build_creds_from_bearer(access_token: str) -> Credentials:
    # We rely on GPT Actions to refresh tokens; we just receive a fresh Bearer here.
    return Credentials(token=access_token, scopes=SCOPES)

def build_drive(creds: Credentials):
    # cache_discovery=False avoids warnings in serverless environments
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
    # Escape single quotes in query
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

def download_file(drive, file_id: str) -> Tuple[str, str, io.BytesIO]:
    meta = drive.files().get(fileId=file_id, fields="id, name, mimeType, parents").execute()
    req = drive.files().get_media(fileId=file_id)
    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, req)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    buf.seek(0)
    return meta["name"], meta["mimeType"], buf

def export_google_doc_as_text(drive, file_id: str) -> Tuple[str, io.BytesIO]:
    # Export Google Doc to plain text for clean extraction
    meta = drive.files().get(fileId=file_id, fields="id, name, mimeType, parents").execute()
    req = drive.files().export_media(fileId=file_id, mimeType="text/plain")
    content = req.execute()
    return meta["name"], io.BytesIO(content)
