from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt

from app.core.config import get_settings

settings = get_settings()


def create_oauth_state(user_id: UUID, provider: str) -> str:
    payload = {
        "sub": str(user_id),
        "provider": provider,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def verify_oauth_state(token: str, provider: str) -> UUID | None:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        if payload.get("provider") != provider:
            return None
        return UUID(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None
