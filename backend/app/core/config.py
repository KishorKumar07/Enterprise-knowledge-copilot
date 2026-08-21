from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "development"

    database_url: str = "postgresql+asyncpg://ekc:ekc_dev_password@localhost:5432/enterprise_knowledge_copilot"

    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days

    session_cookie_name: str = "ekc_session"
    cookie_secure: bool = False  # set True behind HTTPS in production
    # "lax" works locally since frontend/backend share the "localhost" site
    # across different ports. Once deployed to genuinely different domains
    # (e.g. vercel.app + hf.space), cross-site fetches need "none" — which
    # browsers only honor when cookie_secure is also True.
    cookie_samesite: str = "lax"

    credential_encryption_key: str = ""

    frontend_origin: str = "http://localhost:3000"

    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/sources/google-drive/callback"

    slack_client_id: str = ""
    slack_client_secret: str = ""
    slack_redirect_uri: str = "http://localhost:8000/api/sources/slack/callback"

    # Primary LLM provider. Falls back to Groq automatically if Gemini is
    # unconfigured or a call to it fails — see app/services/llm.py.
    gemini_api_key: str = ""
    gemini_model: str = "gemini-flash-latest"
    gemini_utility_model: str = "gemini-flash-lite-latest"

    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    groq_utility_model: str = "llama-3.1-8b-instant"

    # Agent ops: OpenTelemetry traces go to a self-hosted Phoenix instance
    # (docker-compose service). Disabling this is safe — export failures are
    # non-fatal, this just avoids the background exporter entirely.
    otel_enabled: bool = True
    phoenix_endpoint: str = "http://localhost:6006"


@lru_cache
def get_settings() -> Settings:
    return Settings()
