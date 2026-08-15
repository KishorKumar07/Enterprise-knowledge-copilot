"""Thin wrapper around the Google OAuth + Drive v3 REST APIs.

Deliberately implemented with plain httpx calls instead of the heavy
google-api-python-client SDK, so the connector stays transparent and
easy to later re-expose as an MCP tool surface.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx

from app.core.config import get_settings

settings = get_settings()

AUTH_BASE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
DRIVE_API_BASE = "https://www.googleapis.com/drive/v3"
USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid",
]

FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"

# Google-native formats have no raw bytes and must be exported instead.
GOOGLE_EXPORT_MIME_MAP = {
    "application/vnd.google-apps.document": "text/plain",
    "application/vnd.google-apps.presentation": "text/plain",
    "application/vnd.google-apps.spreadsheet": "text/csv",
}

SUPPORTED_BINARY_MIME_TYPES = {
    "application/pdf",
    "text/plain",
    "text/markdown",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
}


class GoogleDriveError(Exception):
    pass


@dataclass
class OAuthTokens:
    access_token: str
    refresh_token: str | None
    expires_at: datetime
    scope: str


@dataclass
class DriveFolder:
    id: str
    name: str
    parent_id: str | None


@dataclass
class DriveFile:
    id: str
    name: str
    mime_type: str
    modified_time: str
    web_view_link: str | None


def is_configured() -> bool:
    return bool(settings.google_client_id and settings.google_client_secret)


def build_authorize_url(state: str) -> str:
    if not is_configured():
        raise GoogleDriveError("Google Drive integration is not configured.")

    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return f"{AUTH_BASE_URL}?{urlencode(params)}"


async def exchange_code_for_tokens(code: str) -> OAuthTokens:
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": settings.google_redirect_uri,
                "grant_type": "authorization_code",
            },
        )
    if response.status_code != 200:
        raise GoogleDriveError("Failed to complete Google authorization.")

    payload = response.json()
    return OAuthTokens(
        access_token=payload["access_token"],
        refresh_token=payload.get("refresh_token"),
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=payload.get("expires_in", 3600)),
        scope=payload.get("scope", ""),
    )


async def refresh_access_token(refresh_token: str) -> OAuthTokens:
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            TOKEN_URL,
            data={
                "refresh_token": refresh_token,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "grant_type": "refresh_token",
            },
        )
    if response.status_code != 200:
        raise GoogleDriveError("Google Drive connection expired. Reconnect Google Drive to continue.")

    payload = response.json()
    return OAuthTokens(
        access_token=payload["access_token"],
        refresh_token=refresh_token,
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=payload.get("expires_in", 3600)),
        scope=payload.get("scope", ""),
    )


async def get_account_email(access_token: str) -> str | None:
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(USERINFO_URL, headers=_auth_headers(access_token))
    if response.status_code != 200:
        return None
    return response.json().get("email")


async def list_folders(access_token: str, parent_id: str = "root") -> list[DriveFolder]:
    query = f"'{parent_id}' in parents and mimeType = '{FOLDER_MIME_TYPE}' and trashed = false"
    params = {
        "q": query,
        "fields": "files(id, name, parents)",
        "pageSize": 200,
        "orderBy": "name",
    }
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(
            f"{DRIVE_API_BASE}/files", params=params, headers=_auth_headers(access_token)
        )
    if response.status_code != 200:
        raise GoogleDriveError("Could not load Google Drive folders.")

    items = response.json().get("files", [])
    return [
        DriveFolder(id=item["id"], name=item["name"], parent_id=parent_id)
        for item in items
    ]


async def list_files_in_folder(access_token: str, folder_id: str) -> list[DriveFile]:
    query = f"'{folder_id}' in parents and mimeType != '{FOLDER_MIME_TYPE}' and trashed = false"
    params = {
        "q": query,
        "fields": "files(id, name, mimeType, modifiedTime, webViewLink)",
        "pageSize": 200,
    }
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(
            f"{DRIVE_API_BASE}/files", params=params, headers=_auth_headers(access_token)
        )
    if response.status_code != 200:
        raise GoogleDriveError("Could not list files in Drive folder.")

    items = response.json().get("files", [])
    return [
        DriveFile(
            id=item["id"],
            name=item["name"],
            mime_type=item["mimeType"],
            modified_time=item.get("modifiedTime", ""),
            web_view_link=item.get("webViewLink"),
        )
        for item in items
    ]


async def fetch_file_content(access_token: str, file: DriveFile) -> tuple[bytes, str] | None:
    """Return (raw_bytes, effective_mime_type) for a text-extractable file, or None if unsupported."""
    async with httpx.AsyncClient(timeout=30) as client:
        if file.mime_type in GOOGLE_EXPORT_MIME_MAP:
            effective_mime = GOOGLE_EXPORT_MIME_MAP[file.mime_type]
            response = await client.get(
                f"{DRIVE_API_BASE}/files/{file.id}/export",
                params={"mimeType": effective_mime},
                headers=_auth_headers(access_token),
            )
        elif file.mime_type in SUPPORTED_BINARY_MIME_TYPES:
            effective_mime = file.mime_type
            response = await client.get(
                f"{DRIVE_API_BASE}/files/{file.id}",
                params={"alt": "media"},
                headers=_auth_headers(access_token),
            )
        else:
            return None

    if response.status_code != 200:
        return None
    return response.content, effective_mime


def is_ingestible_mime_type(mime_type: str) -> bool:
    return mime_type in GOOGLE_EXPORT_MIME_MAP or mime_type in SUPPORTED_BINARY_MIME_TYPES


def _auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}
