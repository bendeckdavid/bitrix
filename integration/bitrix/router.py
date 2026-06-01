from fastapi import APIRouter

from . import conversations
from .schemas import NewConversation, NewMessage

router = APIRouter(prefix="/bitrix", tags=["bitrix"])


@router.post("/conversaciones")
async def crear_conversacion(body: NewConversation):
    return await conversations.create(body.title)


@router.post("/conversaciones/{dialog_id}/mensajes")
async def enviar_mensaje(dialog_id: str, body: NewMessage):
    return {"message_id": await conversations.send_message(dialog_id, body.text)}


@router.get("/conversaciones/{dialog_id}/mensajes")
async def leer_mensajes(dialog_id: str, limit: int = 20):
    return await conversations.get_messages(dialog_id, limit)
