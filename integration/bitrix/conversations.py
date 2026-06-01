from . import client


async def create(title: str) -> dict:
    chat_id = (await client.call("im.chat.add", {"TITLE": title}))["result"]
    return {"chat_id": chat_id, "dialog_id": f"chat{chat_id}"}


async def send_message(dialog_id: str, text: str) -> int:
    return (await client.call(
        "im.message.add", {"DIALOG_ID": dialog_id, "MESSAGE": text}
    ))["result"]


async def get_messages(dialog_id: str, limit: int = 20) -> dict:
    return await client.call(
        "im.dialog.messages.get", {"DIALOG_ID": dialog_id, "LIMIT": limit}
    )
