from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from . import auth, chat, events
from .schemas import NewMessage, QuantumMessage

router = APIRouter(prefix="/bitrix", tags=["bitrix"])

INSTALL_HTML = """<!DOCTYPE html>
<script src="//api.bitrix24.com/api/v1/"></script>
<script>BX24.init(function(){BX24.installFinish();});</script>"""


@router.post("/install")
async def install(request: Request):
    form = await request.form()
    domain = form.get("DOMAIN") or form.get("auth[domain]")
    access = form.get("AUTH_ID") or form.get("auth[access_token]")
    refresh = form.get("REFRESH_ID") or form.get("auth[refresh_token]")
    auth.save(domain, access, refresh)
    return HTMLResponse(INSTALL_HTML)


@router.post("/bot")
async def bot_events(request: Request):
    msg = events.parse_agent_message(await request.form())
    if msg:
        await events.forward_to_platform(msg)
    return {"ok": True}


@router.post("/mensajes")
async def enviar_mensaje(body: NewMessage):
    mid = await chat.post(body.conversation_id, body.sender, body.text, body.system,
                          body.channel, body.account)
    return {"message_id": mid}


@router.post("/quantum")
async def quantum_webhook(body: QuantumMessage):
    ud = body.user_data or {}
    mid = await chat.post(body.user_hash, f"👤 {ud.get('nombre') or 'Cliente'}", body.message,
                          channel=body.message_channel, account=ud.get("telefono") or body.user_hash)
    return {"message_id": mid}
