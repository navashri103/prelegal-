from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from app.chat import (
    GREETING,
    ChatConfigError,
    ChatRequest,
    ChatResponse,
    ChatUpstreamError,
    empty_fields,
    get_chat_reply,
)
from app.db import init_db

load_dotenv()

FRONTEND_DIST = Path(__file__).resolve().parent.parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Prelegal API", lifespan=lifespan)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/chat/greeting")
def chat_greeting() -> ChatResponse:
    return ChatResponse(reply=GREETING, fields=empty_fields())


@app.post("/api/chat/message")
def chat_message(request: ChatRequest) -> ChatResponse:
    try:
        return get_chat_reply(request)
    except ChatConfigError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except ChatUpstreamError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
