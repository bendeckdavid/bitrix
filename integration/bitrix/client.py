import httpx

from core.settings import get_settings


class BitrixError(Exception):
    def __init__(self, code: str, description: str):
        self.code = code
        self.description = description
        super().__init__(f"{code}: {description}")


async def call(method: str, params: dict | None = None) -> dict:
    base_url = get_settings().bitrix_webhook_url.rstrip("/")
    url = f"{base_url}/{method}.json"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, json=params or {})
        data = resp.json()
        if "error" in data:
            raise BitrixError(data["error"], data.get("error_description", ""))
        return data
