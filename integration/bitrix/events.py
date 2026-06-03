import httpx

from core.settings import get_settings

_FILES_PREFIX = "data[PARAMS][FILES]["


def parse_agent_message(form) -> dict | None:
    if form.get("event") != "ONIMBOTMESSAGEADD":
        return None
    if form.get("data[PARAMS][CHAT_ENTITY_TYPE]") != "IA_CONV":
        return None
    if form.get("data[USER][IS_BOT]") != "N":
        return None
    if form.get("data[PARAMS][SYSTEM]") == "Y":
        return None
    return {
        "conversation_id": form.get("data[PARAMS][CHAT_ENTITY_ID]"),
        "text": form.get("data[PARAMS][MESSAGE]", ""),
        "author": form.get("data[USER][NAME]"),
        "files": _files(form),
    }


def _files(form) -> list[dict]:
    ids = {k[len(_FILES_PREFIX):].split("]")[0] for k in form if k.startswith(_FILES_PREFIX)}
    return [{
        "name": form.get(f"{_FILES_PREFIX}{i}][name]"),
        "url": form.get(f"{_FILES_PREFIX}{i}][urlDownload]"),
        "is_image": form.get(f"{_FILES_PREFIX}{i}][image]") == "1",
    } for i in sorted(ids)]


async def forward_to_platform(msg: dict) -> None:
    text = msg["text"] or next((f["url"] for f in msg["files"] if f.get("url")), "")
    if not text:
        return
    s = get_settings()
    async with httpx.AsyncClient(timeout=10) as c:
        await c.post(
            f"{s.quantum_url}/api/agent-messages",
            headers={"X-API-Key": s.quantum_api_key},
            json={"user_hash": msg["conversation_id"], "message": text},
        )
