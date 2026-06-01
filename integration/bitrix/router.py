from fastapi import APIRouter

from . import client

router = APIRouter(prefix="/bitrix", tags=["bitrix"])


@router.get("/perfil")
async def perfil():
    return await client.call("profile")
