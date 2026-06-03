import json
from pathlib import Path

import httpx

from core.settings import get_settings

OAUTH_URL = "https://oauth.bitrix.info/oauth/token/"
TOKENS_FILE = Path("tokens.json")


def save(domain: str, access_token: str, refresh_token: str) -> None:
    TOKENS_FILE.write_text(json.dumps(
        {"domain": domain, "access_token": access_token, "refresh_token": refresh_token}
    ))


def load() -> dict:
    return json.loads(TOKENS_FILE.read_text())


async def refresh() -> None:
    t = load()
    s = get_settings()
    async with httpx.AsyncClient(timeout=30) as c:
        data = (await c.get(OAUTH_URL, params={
            "grant_type": "refresh_token",
            "client_id": s.bitrix_client_id,
            "client_secret": s.bitrix_client_secret,
            "refresh_token": t["refresh_token"],
        })).json()
    save(t["domain"], data["access_token"], data["refresh_token"])
