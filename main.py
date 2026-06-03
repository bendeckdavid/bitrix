from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse

from integration.bitrix.client import BitrixError
from integration.bitrix.router import router as bitrix_router

app = FastAPI()
app.include_router(bitrix_router)


@app.exception_handler(BitrixError)
async def bitrix_error_handler(request: Request, exc: BitrixError):
    return JSONResponse(status_code=400, content={"error": exc.code, "detail": exc.description})


@app.get("/")
def index():
    return FileResponse("index.html")


@app.get("/health")
def health():
    return {"status": "ok"}


def dev():
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8100, reload=True)
