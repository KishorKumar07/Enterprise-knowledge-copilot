from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors import google_drive
from app.core.encryption import decrypt_value, encrypt_value
from app.models.connection import Connection


class ConnectionUnavailableError(Exception):
    """Raised with a user-facing message when a connection needs reconnecting."""


async def get_valid_google_access_token(db: AsyncSession, connection: Connection) -> str:
    if connection.status == "disconnected":
        raise ConnectionUnavailableError("Google Drive is not connected.")

    expires_at = connection.token_expires_at
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at and expires_at > datetime.now(timezone.utc):
        return decrypt_value(connection.encrypted_access_token)

    if not connection.encrypted_refresh_token:
        connection.status = "expired"
        connection.last_error = "Google Drive connection expired. Reconnect Google Drive to continue."
        await db.commit()
        raise ConnectionUnavailableError(connection.last_error)

    try:
        tokens = await google_drive.refresh_access_token(decrypt_value(connection.encrypted_refresh_token))
    except google_drive.GoogleDriveError as exc:
        connection.status = "expired"
        connection.last_error = str(exc)
        await db.commit()
        raise ConnectionUnavailableError(str(exc)) from exc

    connection.encrypted_access_token = encrypt_value(tokens.access_token)
    connection.token_expires_at = tokens.expires_at
    connection.status = "connected"
    connection.last_error = None
    await db.commit()

    return tokens.access_token
