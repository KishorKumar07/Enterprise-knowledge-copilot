"""Thin wrapper around Slack's OAuth v2 and Web API."""

from dataclasses import dataclass
from urllib.parse import urlencode

import httpx

from app.core.config import get_settings

settings = get_settings()

AUTH_BASE_URL = "https://slack.com/oauth/v2/authorize"
TOKEN_URL = "https://slack.com/api/oauth.v2.access"
API_BASE = "https://slack.com/api"

# Bot token scopes: read public/private channel metadata and history for
# channels the bot has been invited to, plus basic team info for display.
BOT_SCOPES = [
    "channels:read",
    "channels:history",
    "groups:read",
    "groups:history",
    "team:read",
]


class SlackError(Exception):
    pass


@dataclass
class SlackOAuthResult:
    access_token: str
    team_name: str
    team_id: str
    scope: str


@dataclass
class SlackChannel:
    id: str
    name: str
    is_private: bool


@dataclass
class SlackMessage:
    ts: str
    user: str | None
    text: str
    thread_ts: str | None


def is_configured() -> bool:
    return bool(settings.slack_client_id and settings.slack_client_secret)


def build_authorize_url(state: str) -> str:
    if not is_configured():
        raise SlackError("Slack integration is not configured.")

    params = {
        "client_id": settings.slack_client_id,
        "scope": ",".join(BOT_SCOPES),
        "redirect_uri": settings.slack_redirect_uri,
        "state": state,
    }
    return f"{AUTH_BASE_URL}?{urlencode(params)}"


async def exchange_code_for_token(code: str) -> SlackOAuthResult:
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.slack_client_id,
                "client_secret": settings.slack_client_secret,
                "redirect_uri": settings.slack_redirect_uri,
            },
        )
    payload = response.json()
    if not payload.get("ok"):
        raise SlackError("Failed to complete Slack authorization.")

    return SlackOAuthResult(
        access_token=payload["access_token"],
        team_name=payload.get("team", {}).get("name", "Slack workspace"),
        team_id=payload.get("team", {}).get("id", ""),
        scope=payload.get("scope", ""),
    )


async def list_channels(access_token: str) -> list[SlackChannel]:
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(
            f"{API_BASE}/conversations.list",
            params={"types": "public_channel,private_channel", "limit": 200, "exclude_archived": "true"},
            headers=_auth_headers(access_token),
        )
    payload = response.json()
    if not payload.get("ok"):
        raise SlackError("Could not load Slack channels.")

    return [
        SlackChannel(id=c["id"], name=c["name"], is_private=c.get("is_private", False))
        for c in payload.get("channels", [])
    ]


async def fetch_channel_history(access_token: str, channel_id: str, limit: int = 200) -> list[SlackMessage]:
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(
            f"{API_BASE}/conversations.history",
            params={"channel": channel_id, "limit": limit},
            headers=_auth_headers(access_token),
        )
    payload = response.json()
    if not payload.get("ok"):
        raise SlackError(f"Could not read messages from channel: {payload.get('error', 'unknown error')}")

    return [
        SlackMessage(
            ts=m["ts"],
            user=m.get("user"),
            text=m.get("text", ""),
            thread_ts=m.get("thread_ts"),
        )
        for m in payload.get("messages", [])
        if m.get("type") == "message" and m.get("text")
    ]


async def fetch_thread_replies(access_token: str, channel_id: str, thread_ts: str) -> list[SlackMessage]:
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(
            f"{API_BASE}/conversations.replies",
            params={"channel": channel_id, "ts": thread_ts, "limit": 200},
            headers=_auth_headers(access_token),
        )
    payload = response.json()
    if not payload.get("ok"):
        return []

    return [
        SlackMessage(ts=m["ts"], user=m.get("user"), text=m.get("text", ""), thread_ts=m.get("thread_ts"))
        for m in payload.get("messages", [])
        if m.get("text")
    ]


async def get_user_display_name(access_token: str, user_id: str) -> str:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(
            f"{API_BASE}/users.info", params={"user": user_id}, headers=_auth_headers(access_token)
        )
    payload = response.json()
    if not payload.get("ok"):
        return user_id
    profile = payload.get("user", {})
    return profile.get("real_name") or profile.get("name") or user_id


def _auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}
