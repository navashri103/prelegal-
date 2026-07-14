import hashlib
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Depends, HTTPException, Request
from pydantic import BaseModel

from app.db import get_db

SESSION_COOKIE_NAME = "session_token"
SESSION_MAX_AGE_SECONDS = 60 * 60 * 24 * 30  # 30 days
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 72  # bcrypt only hashes the first 72 bytes of a password


class SignupRequest(BaseModel):
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: int
    email: str


class InvalidEmailError(RuntimeError):
    pass


class WeakPasswordError(RuntimeError):
    pass


class EmailAlreadyRegisteredError(RuntimeError):
    pass


class InvalidCredentialsError(RuntimeError):
    pass


def _validate_email(email: str) -> str:
    email = email.strip().lower()
    if "@" not in email or "." not in email.split("@")[-1]:
        raise InvalidEmailError("Enter a valid email address.")
    return email


def _validate_password(password: str) -> None:
    # bcrypt's 72-byte limit is on the UTF-8 encoding, not the character count -
    # check bytes so multi-byte passwords (CJK, emoji, ...) aren't wrongly accepted
    # here only to crash bcrypt.hashpw() with a ValueError further down.
    byte_length = len(password.encode("utf-8"))
    if not (MIN_PASSWORD_LENGTH <= byte_length <= MAX_PASSWORD_LENGTH):
        raise WeakPasswordError(
            f"Password must be between {MIN_PASSWORD_LENGTH} and {MAX_PASSWORD_LENGTH} bytes long."
        )


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_user(connection: sqlite3.Connection, request: SignupRequest) -> UserResponse:
    email = _validate_email(request.email)
    _validate_password(request.password)
    password_hash = _hash_password(request.password)
    try:
        cursor = connection.execute(
            "INSERT INTO users (email, password_hash) VALUES (?, ?)",
            (email, password_hash),
        )
    except sqlite3.IntegrityError as error:
        raise EmailAlreadyRegisteredError(f"{email} is already registered.") from error
    return UserResponse(id=cursor.lastrowid, email=email)


def authenticate_user(connection: sqlite3.Connection, request: LoginRequest) -> UserResponse:
    email = request.email.strip().lower()
    row = connection.execute(
        "SELECT id, email, password_hash FROM users WHERE email = ?", (email,)
    ).fetchone()
    if row is None or not _verify_password(request.password, row["password_hash"]):
        raise InvalidCredentialsError("Invalid email or password.")
    return UserResponse(id=row["id"], email=row["email"])


def create_session(connection: sqlite3.Connection, user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=SESSION_MAX_AGE_SECONDS)
    connection.execute(
        "INSERT INTO sessions (user_id, token_hash, expires_at) VALUES (?, ?, ?)",
        (user_id, _hash_token(token), expires_at.strftime("%Y-%m-%d %H:%M:%S")),
    )
    return token


def get_user_by_session_token(connection: sqlite3.Connection, token: str | None) -> UserResponse | None:
    if not token:
        return None
    row = connection.execute(
        """
        SELECT users.id, users.email
        FROM sessions
        JOIN users ON users.id = sessions.user_id
        WHERE sessions.token_hash = ? AND sessions.expires_at > CURRENT_TIMESTAMP
        """,
        (_hash_token(token),),
    ).fetchone()
    return UserResponse(id=row["id"], email=row["email"]) if row else None


def delete_session(connection: sqlite3.Connection, token: str | None) -> None:
    if not token:
        return
    connection.execute("DELETE FROM sessions WHERE token_hash = ?", (_hash_token(token),))


def get_current_user(
    request: Request, connection: sqlite3.Connection = Depends(get_db)
) -> UserResponse | None:
    return get_user_by_session_token(connection, request.cookies.get(SESSION_COOKIE_NAME))


def require_user(user: UserResponse | None = Depends(get_current_user)) -> UserResponse:
    if user is None:
        raise HTTPException(status_code=401, detail="Not signed in")
    return user
