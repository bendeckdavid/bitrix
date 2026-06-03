import json
from pathlib import Path

from core.settings import get_settings

from . import client

BOT_CODE = "quantum_ia"
BOT_NAME = "IA"
_BOT_FILE = Path("bot.json")


async def bot_id() -> int:
    if _BOT_FILE.exists():
        return json.loads(_BOT_FILE.read_text())["bot_id"]
    handler = f"{get_settings().app_base_url}/bitrix/bot"
    bid = (await client.call("imbot.register", {
        "CODE": BOT_CODE,
        "TYPE": "S",  # supervisor: recibe TODOS los mensajes del chat (sin @mención)
        "EVENT_MESSAGE_ADD": handler,
        "PROPERTIES": {"NAME": BOT_NAME},
    }))["result"]
    _BOT_FILE.write_text(json.dumps({"bot_id": bid}))
    return bid


async def send_message(dialog_id: str, text: str, system: bool = False) -> int:
    params = {"BOT_ID": await bot_id(), "DIALOG_ID": dialog_id, "MESSAGE": text}
    if system:
        params["SYSTEM"] = "Y"
    return (await client.call("imbot.message.add", params))["result"]
