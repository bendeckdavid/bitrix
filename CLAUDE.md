# CLAUDE.md

FastAPI + Bitrix24 **App Local (OAuth)**. Run: `uv run dev` → http://localhost:8100 (`/docs`, `/` = index.html).

**Objetivo:** espejar en Bitrix las conversaciones Usuario↔IA de un chatbot externo para que los agentes las VEAN e INTERVENGAN. Flujo ida: app externa → `POST /bitrix/mensajes` → 1 chat de grupo de Bitrix por conversación. El **bot** publica los mensajes espejo (Usuario + IA) etiquetados; el **agente** humano es miembro del chat y escribe como él mismo. Flujo vuelta: lo que escribe el agente → evento del bot → `forward_to_platform` (TODO).
Descartado Open Lines/conector (fricción al publicar como bot/operador en sesiones).

## Layout (1 responsabilidad / archivo)
- `main.py` — app (con `lifespan` del MCP), monta router + MCP en `/mcp`, handler `BitrixError`→400, `GET /` (index.html), `GET /health`, `dev()`.
- `core/settings.py` — única `Settings` (pydantic-settings, `extra=ignore`) + `get_settings()` (lru_cache): `bitrix_client_id`, `bitrix_client_secret`, `app_base_url`, `quantum_url`, `quantum_api_key`, `openai_api_key`. **Config nueva = un campo aquí.**
- `integration/bitrix/auth.py` — OAuth en `tokens.json` (gitignored): `save/load/refresh` (refresh vía oauth.bitrix.info). Bitrix entrega los tokens al instalar.
- `integration/bitrix/client.py` — `call(method, params)` REST con token OAuth; auto-`refresh` y 1 reintento si `expired_token`; sin tokens → `BitrixError("not_installed", …)`. `BitrixError(code, description)`.
- `integration/bitrix/bot.py` — voz de la IA. `bot_id()` registra el imbot idempotente (cachea en `bot.json`), `TYPE='S'` (**supervisor**). `send_message(dialog_id, text, system=False)` vía `imbot.message.add`; `system=True`→`SYSTEM=Y` (gris). `BOT_CODE="quantum_ia"`.
- `integration/bitrix/chat.py` — 1 conversación = 1 chat de grupo; get-or-create por `ENTITY_TYPE="IA_CONV"` + `ENTITY_ID=conversation_id`. `post(conversation_id, sender, text, system=False, channel="", account="")`: publica vía el bot; cuerpo `[b]sender:[/b] text` salvo `system` (texto plano). `channel`/`account` solo al CREAR el chat → título `🟢 WhatsApp · <account>` (mapa `CHANNELS`, fallback ⚪). `AGENT_IDS=[1]` = operadores miembros. `AVATAR`= `logo.png` en base64 si existe.
- `integration/bitrix/events.py` — `parse_agent_message(form)`: devuelve `{conversation_id, text}` solo si `ONIMBOTMESSAGEADD` + `CHAT_ENTITY_TYPE=IA_CONV` + `IS_BOT=N` (ignora el propio bot → evita bucle) + no `SYSTEM=Y` + hay texto (o, en su defecto, URL del primer adjunto); si no, `None`. `forward_to_platform(msg)`: `POST {quantum_url}/api/agent-messages` con header `X-API-Key` y `{user_hash, message}`.
- `integration/bitrix/schemas.py` — pydantic. `NewMessage`: `conversation_id`, `text`, `sender=""`, `system=False`, `channel=""`, `account=""`. `QuantumMessage`: `user_hash`, `message`, `message_channel=""`, `user_data=None`.
- `integration/bitrix/router.py` — prefix `/bitrix`: `POST /install` (guarda tokens; acepta formato con UI `DOMAIN/AUTH_ID/REFRESH_ID` y evento `ONAPPINSTALL` `auth[domain]/auth[access_token]/…`), `POST /bot` (vuelta agente→plataforma), `POST /mensajes` (ida genérica, `NewMessage`), `POST /quantum` (ida desde Quantum, `QuantumMessage`: mapea `user_hash`→conversación, `👤 nombre`→sender, `telefono`→account).
- `integration/mcp/server.py` — servidor MCP (FastMCP 3, Streamable HTTP). Expone la instancia `mcp`; las tools se declaran aquí con `@mcp.tool`. Se monta en `/mcp` desde `main.py`. Tool: `scrape_destino(url, nombre, codigo) -> str` (descarga+limpia+extrae un destino avioa, lo **guarda en `destinos.json`** (clave=codigo) y devuelve **markdown** listo para un LLM; HTTP error → `ValueError` legible).
- `integration/scrape/` — pipeline de scraping (puerto mínimo de avioa-scrapper). `clean.py`: `descargar(url)` (httpx) + `contenido_a_texto(html)` (selectolax → texto/markdown, corta boilerplate por `_CORTES`, selector elementor de avioa). `extract.py`: `extraer(texto, url)` con OpenAI Structured Outputs (`responses.parse`, `MODEL="gpt-5.4-mini"`, caching automático del prefijo). `render.py`: `to_markdown(data)` → markdown compacto para el LLM (≈58% menos tokens que el JSON; omite vacíos). `store.py`: `save(codigo, nombre, url, data)` → upsert en `destinos.json` (BD local gitignored, clave=codigo). `schemas.py`: pydantic `Destino/Resumen/Hotel/Tarifa/Precio` (opcionales como `Optional[...]` nullable, exigencia de OpenAI).
- `index.html` — página de pruebas manual.
- `docker-compose.yml` — túnel `ngrok` (URL fija `APP_BASE_URL` del `.env`) → `host:8100`.

## Bitrix (verificado — no romper)
- **Scopes:** SOLO `im` + `imbot` (`im.chat.add/get`, `imbot.register/message.add`, evento `ONIMBOTMESSAGEADD`). NO `crm` ni `user`. Cambiar scopes ⇒ Guardar + **REINSTALAR** (rota tokens).
- **Bot `TYPE='S'` (supervisor):** recibe TODOS los mensajes del chat sin @mención.
- **App "Solo script":** instala por `ONAPPINSTALL` server-to-server; el install con UI falla por el interstitial de ngrok.
- Bot atado al `client_id`; si cambia la app, re-registrar (cambiar `BOT_CODE`).

## Reglas (obligatorias)
- **Versión mínima siempre:** sin params/campos/archivos/abstracciones no usados. Menos es mejor.
- Antes de usar una API de Bitrix, **verificar** contra docs/foros (apidocs.bitrix24.com) y, si se puede, contra la API real.
- Mantener `index.html` al día: cada endpoint nuevo/cambiado lleva su control de prueba.
- Modelos pydantic → `schemas.py`. Secretos solo en `.env` (gitignored); nunca hardcodear.
