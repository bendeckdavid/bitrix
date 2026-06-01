from fastapi import FastAPI
from fastapi.responses import FileResponse

from integration.bitrix.router import router as bitrix_router

app = FastAPI()
app.include_router(bitrix_router)


@app.get("/")
def index():
    return FileResponse("index.html")


@app.get("/health")
def health():
    return {"status": "ok"}


def dev():
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
