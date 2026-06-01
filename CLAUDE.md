# CLAUDE.md

FastAPI + Bitrix24 (webhook entrante). Run: `uv run dev` (http://localhost:8000, `/docs`, `/` = index.html).

## Layout
- `main.py` — app, `/health`, `/`, BitrixError handler, `dev()`
- `core/settings.py` — única `Settings` (pydantic-settings, lee `.env`). Toda config nueva = un campo aquí, no archivos nuevos.
- `integration/bitrix/client.py` — `call(method, params)` REST + `BitrixError`
- `integration/bitrix/conversations.py` — lógica (1 conversación = 1 chat Bitrix: `im.chat.add`/`im.message.add`/`im.dialog.messages.get`)
- `integration/bitrix/schemas.py` — modelos pydantic de request/response
- `integration/bitrix/router.py` — endpoints `/bitrix/*`
- `index.html` — página de pruebas manual

## Reglas (obligatorias)
- SIEMPRE la versión mínima posible: sin params/campos/archivos/abstracciones no usados. Menos es mejor.
- Antes de implementar API de Bitrix, verificar contra docs/internet/foros (apidocs.bitrix24.com) y, si se puede, contra la API real.
- Mantener `index.html` actualizado: cada endpoint nuevo/cambiado se refleja con su control de prueba.
- Responsabilidad única por archivo. Modelos pydantic → `schemas.py`.
- Secretos solo en `.env` (gitignored). Nunca hardcodear.
