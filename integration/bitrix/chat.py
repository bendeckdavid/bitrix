import base64
from pathlib import Path

from . import bot, client

ENTITY_TYPE = "IA_CONV"
AGENT_IDS = [1]

CHANNELS = {
    "whatsapp": ("🟢", "WhatsApp"),
    "instagram": ("🟣", "Instagram"),
    "tiktok": ("⚫", "TikTok"),
    "facebook": ("🔵", "Facebook"),
}


def _title(channel: str, account: str) -> str:
    circle, name = CHANNELS.get(channel.lower(), ("⚪", channel.title() or "Chat"))
    label = f"{circle} {name}"
    return f"{label} · {account}" if account else label

_LOGO = Path("logo.png")
AVATAR = base64.b64encode(_LOGO.read_bytes()).decode() if _LOGO.exists() else ""


async def _chat_id(conversation_id: str, channel: str = "", account: str = "") -> int:
    found = (await client.call(
        "im.chat.get", {"ENTITY_TYPE": ENTITY_TYPE, "ENTITY_ID": conversation_id}
    )).get("result")
    if found:
        return found["ID"]
    params = {
        "TITLE": _title(channel, account),
        "ENTITY_TYPE": ENTITY_TYPE,
        "ENTITY_ID": conversation_id,
        "USERS": AGENT_IDS + [await bot.bot_id()],
    }
    if AVATAR:
        params["AVATAR"] = AVATAR
    return (await client.call("im.chat.add", params))["result"]


async def post(conversation_id: str, sender: str, text: str, system: bool = False,
               channel: str = "", account: str = "") -> int:
    chat = await _chat_id(conversation_id, channel, account)
    body = text if system else f"[b]{sender}:[/b] {text}"
    return await bot.send_message(f"chat{chat}", body, system=system)
