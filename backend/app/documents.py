import json
import sqlite3
from typing import Literal

from pydantic import BaseModel

from app.chat import ChatMessage, greeting_for
from app.document_templates import empty_fields, load_template, missing_required_fields

DocumentStatus = Literal["in_progress", "completed"]


class CreateDocumentRequest(BaseModel):
    template_id: str


class SaveDocumentRequest(BaseModel):
    fields: dict[str, str | None]
    messages: list[ChatMessage]


class DocumentSummary(BaseModel):
    id: int
    template_id: str
    status: DocumentStatus
    updated_at: str


class DocumentResponse(DocumentSummary):
    fields: dict[str, str | None]
    messages: list[ChatMessage]


class DocumentNotFoundError(RuntimeError):
    pass


def _status_for(template: dict, fields: dict[str, str | None]) -> DocumentStatus:
    return "completed" if not missing_required_fields(template, fields) else "in_progress"


def _row_to_response(row: sqlite3.Row) -> DocumentResponse:
    return DocumentResponse(
        id=row["id"],
        template_id=row["template_id"],
        status=row["status"],
        updated_at=row["updated_at"],
        fields=json.loads(row["fields_json"]),
        messages=[ChatMessage(**message) for message in json.loads(row["messages_json"])],
    )


def create_document(
    connection: sqlite3.Connection, user_id: int, request: CreateDocumentRequest
) -> DocumentResponse:
    template = load_template(request.template_id)  # raises TemplateNotFoundError
    fields = empty_fields(request.template_id)
    messages = [ChatMessage(role="assistant", content=greeting_for(request.template_id))]
    cursor = connection.execute(
        """
        INSERT INTO documents (user_id, template_id, status, fields_json, messages_json)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            user_id,
            request.template_id,
            _status_for(template, fields),
            json.dumps(fields),
            json.dumps([message.model_dump() for message in messages]),
        ),
    )
    return get_document(connection, user_id, cursor.lastrowid)


def list_documents(connection: sqlite3.Connection, user_id: int) -> list[DocumentSummary]:
    rows = connection.execute(
        "SELECT id, template_id, status, updated_at FROM documents WHERE user_id = ? "
        "ORDER BY updated_at DESC",
        (user_id,),
    ).fetchall()
    return [
        DocumentSummary(
            id=row["id"], template_id=row["template_id"], status=row["status"], updated_at=row["updated_at"]
        )
        for row in rows
    ]


def get_document(connection: sqlite3.Connection, user_id: int, document_id: int) -> DocumentResponse:
    row = connection.execute(
        "SELECT * FROM documents WHERE id = ? AND user_id = ?", (document_id, user_id)
    ).fetchone()
    if row is None:
        raise DocumentNotFoundError(f"Document {document_id} not found.")
    return _row_to_response(row)


def save_document(
    connection: sqlite3.Connection, user_id: int, document_id: int, request: SaveDocumentRequest
) -> DocumentResponse:
    existing = connection.execute(
        "SELECT template_id FROM documents WHERE id = ? AND user_id = ?", (document_id, user_id)
    ).fetchone()
    if existing is None:
        raise DocumentNotFoundError(f"Document {document_id} not found.")
    template = load_template(existing["template_id"])
    connection.execute(
        """
        UPDATE documents
        SET fields_json = ?, messages_json = ?, status = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ? AND user_id = ?
        """,
        (
            json.dumps(request.fields),
            json.dumps([message.model_dump() for message in request.messages]),
            _status_for(template, request.fields),
            document_id,
            user_id,
        ),
    )
    return get_document(connection, user_id, document_id)


def delete_document(connection: sqlite3.Connection, user_id: int, document_id: int) -> None:
    cursor = connection.execute(
        "DELETE FROM documents WHERE id = ? AND user_id = ?", (document_id, user_id)
    )
    if cursor.rowcount == 0:
        raise DocumentNotFoundError(f"Document {document_id} not found.")
