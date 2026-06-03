import httpx

from . import auth


class BitrixError(Exception):
    def __init__(self, code: str, description: str):
        self.code = code
        self.description = description
        super().__init__(f"{code}: {description}")


async def call(method: str, params: dict | None = None, _retry: bool = True) -> dict:
    try:
        t = auth.load()
    except FileNotFoundError:
        raise BitrixError("not_installed", "Instala la App Local en Bitrix primero (/bitrix/install)")
    url = f"https://{t['domain']}/rest/{method}.json"
    async with httpx.AsyncClient(timeout=30) as c:
        data = (await c.post(url, json={**(params or {}), "auth": t["access_token"]})).json()

    if data.get("error") == "expired_token" and _retry:
        await auth.refresh()
        return await call(method, params, _retry=False)
    if "error" in data:
        raise BitrixError(data["error"], data.get("error_description", ""))
    return data
