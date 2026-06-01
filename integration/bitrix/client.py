import httpx

from core.settings import get_settings


async def call(method: str, params: dict | None = None) -> dict:
    base_url = get_settings().bitrix_webhook_url.rstrip("/")
    url = f"{base_url}/{method}.json"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, json=params or {})
        resp.raise_for_status()
        return resp.json()
