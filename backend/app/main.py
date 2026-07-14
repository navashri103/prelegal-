from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from app.chat import (
    ChatConfigError,
    ChatRequest,
    ChatResponse,
    ChatUpstreamError,
    get_chat_reply,
    greeting_for,
)
from app.db import init_db
from app.document_templates import TemplateNotFoundError, empty_fields

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


@app.get("/api/chat/{template_id}/greeting")
def chat_greeting(template_id: str) -> ChatResponse:
    try:
        return ChatResponse(reply=greeting_for(template_id), fields=empty_fields(template_id))
    except TemplateNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.post("/api/chat/{template_id}/message")
def chat_message(template_id: str, request: ChatRequest) -> ChatResponse:
    try:
        return get_chat_reply(template_id, request)
    except TemplateNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ChatConfigError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except ChatUpstreamError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
