import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.auth import (
    SESSION_COOKIE_NAME,
    SESSION_MAX_AGE_SECONDS,
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    InvalidEmailError,
    LoginRequest,
    SignupRequest,
    UserResponse,
    WeakPasswordError,
    authenticate_user,
    create_session,
    create_user,
    delete_session,
    require_user,
)
from app.chat import (
    DISCOVERY_GREETING,
    ChatConfigError,
    ChatRequest,
    ChatResponse,
    ChatUpstreamError,
    DiscoverRequest,
    DiscoverResponse,
    discover_document,
    get_chat_reply,
    greeting_for,
)
from app.db import get_db, init_db
from app.document_templates import TemplateNotFoundError, empty_fields
from app.documents import (
    CreateDocumentRequest,
    DocumentNotFoundError,
    DocumentResponse,
    DocumentSummary,
    SaveDocumentRequest,
    create_document,
    delete_document,
    get_document,
    list_documents,
    save_document,
)

load_dotenv()

FRONTEND_DIST = Path(__file__).resolve().parent.parent / "static"
COOKIE_SECURE = os.environ.get("PRELEGAL_COOKIE_SECURE", "false").lower() == "true"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Prelegal API", lifespan=lifespan)


@app.exception_handler(TemplateNotFoundError)
async def template_not_found_handler(request: Request, exc: TemplateNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(DocumentNotFoundError)
async def document_not_found_handler(request: Request, exc: DocumentNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        SESSION_COOKIE_NAME,
        token,
        max_age=SESSION_MAX_AGE_SECONDS,
        httponly=True,
        samesite="lax",
        secure=COOKIE_SECURE,
        path="/",
    )


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/chat/{template_id}/greeting")
def chat_greeting(template_id: str) -> ChatResponse:
    return ChatResponse(reply=greeting_for(template_id), fields=empty_fields(template_id))


@app.post("/api/chat/{template_id}/message")
def chat_message(template_id: str, request: ChatRequest) -> ChatResponse:
    try:
        return get_chat_reply(template_id, request)
    except ChatConfigError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except ChatUpstreamError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@app.get("/api/discover/greeting")
def discover_greeting() -> DiscoverResponse:
    return DiscoverResponse(reply=DISCOVERY_GREETING)


@app.post("/api/discover/message")
def discover_message(request: DiscoverRequest) -> DiscoverResponse:
    try:
        return discover_document(request)
    except ChatConfigError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except ChatUpstreamError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@app.post("/api/auth/signup", status_code=201)
def signup(request: SignupRequest, response: Response, connection=Depends(get_db)) -> UserResponse:
    try:
        user = create_user(connection, request)
    except (InvalidEmailError, WeakPasswordError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except EmailAlreadyRegisteredError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    _set_session_cookie(response, create_session(connection, user.id))
    return user


@app.post("/api/auth/login")
def login(request: LoginRequest, response: Response, connection=Depends(get_db)) -> UserResponse:
    try:
        user = authenticate_user(connection, request)
    except InvalidCredentialsError as error:
        raise HTTPException(status_code=401, detail=str(error)) from error
    _set_session_cookie(response, create_session(connection, user.id))
    return user


@app.post("/api/auth/logout", status_code=204)
def logout(request: Request, response: Response, connection=Depends(get_db)) -> None:
    delete_session(connection, request.cookies.get(SESSION_COOKIE_NAME))
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")


@app.get("/api/auth/me")
def me(user: UserResponse = Depends(require_user)) -> UserResponse:
    return user


@app.post("/api/documents", status_code=201)
def create_document_route(
    request: CreateDocumentRequest,
    user: UserResponse = Depends(require_user),
    connection=Depends(get_db),
) -> DocumentResponse:
    return create_document(connection, user.id, request)


@app.get("/api/documents")
def list_documents_route(
    user: UserResponse = Depends(require_user), connection=Depends(get_db)
) -> list[DocumentSummary]:
    return list_documents(connection, user.id)


@app.get("/api/documents/{document_id}")
def get_document_route(
    document_id: int, user: UserResponse = Depends(require_user), connection=Depends(get_db)
) -> DocumentResponse:
    return get_document(connection, user.id, document_id)


@app.put("/api/documents/{document_id}")
def save_document_route(
    document_id: int,
    request: SaveDocumentRequest,
    user: UserResponse = Depends(require_user),
    connection=Depends(get_db),
) -> DocumentResponse:
    return save_document(connection, user.id, document_id, request)


@app.delete("/api/documents/{document_id}", status_code=204)
def delete_document_route(
    document_id: int, user: UserResponse = Depends(require_user), connection=Depends(get_db)
) -> None:
    delete_document(connection, user.id, document_id)


if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
