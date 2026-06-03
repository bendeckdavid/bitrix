import httpx

from core.settings import get_settings

_FILES_PREFIX = "data[PARAMS][FILES]["


def parse_agent_message(form) -> dict | None:
    if form.get("event") != "ONIMBOTMESSAGEADD":
        return None
    if form.get("data[PARAMS][CHAT_ENTITY_TYPE]") != "IA_CONV":
        return None
    if form.get("data[USER][IS_BOT]") != "N":  # ignora el propio bot → evita bucle
        return None
    if form.get("data[PARAMS][SYSTEM]") == "Y":
        return None
    text = form.get("data[PARAMS][MESSAGE]", "") or _first_file_url(form)
    if not text:
        return None
    return {"conversation_id": form.get("data[PARAMS][CHAT_ENTITY_ID]"), "text": text}


def _first_file_url(form) -> str:
    ids = sorted({k[len(_FILES_PREFIX):].split("]")[0] for k in form if k.startswith(_FILES_PREFIX)})
    return next((u for i in ids if (u := form.get(f"{_FILES_PREFIX}{i}][urlDownload]"))), "")


async def forward_to_platform(msg: dict) -> None:
    s = get_settings()
    async with httpx.AsyncClient(timeout=10) as c:
        await c.post(
            f"{s.quantum_url}/api/agent-messages",
            headers={"X-API-Key": s.quantum_api_key},
            json={"user_hash": msg["conversation_id"], "message": msg["text"]},
        )
