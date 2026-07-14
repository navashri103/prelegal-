import json
import os

import httpx
from pydantic import BaseModel

from app.document_templates import (
    all_template_summaries,
    all_template_titles,
    load_template,
    missing_required_fields,
)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "google/gemma-4-26b-a4b-it:free"
REQUEST_TIMEOUT_SECONDS = 30
MAX_ATTEMPTS = 3


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    fields: dict[str, str | None]


class ChatResponse(BaseModel):
    reply: str
    fields: dict[str, str | None]
    suggested_template_id: str | None = None


class DiscoverRequest(BaseModel):
    messages: list[ChatMessage]


class DiscoverResponse(BaseModel):
    reply: str
    matched_template_id: str | None = None


class ChatConfigError(RuntimeError):
    pass


class ChatUpstreamError(RuntimeError):
    pass


DISCOVERY_GREETING = "Hi! What kind of document are you looking to create today?"


def _reads_as_question(reply: str) -> bool:
    return reply.strip().rstrip("\"')’”").endswith("?")


def _follow_up_question(missing_fields: list[dict]) -> str:
    labels = [field["label"] for field in missing_fields[:2]]
    if len(labels) == 1:
        return f"Could you tell me the {labels[0]}?"
    return f"Could you tell me the {labels[0]} and {labels[1]}?"


def _ensure_follow_up(template: dict, fields: dict[str, str | None], reply: str) -> str:
    missing = missing_required_fields(template, fields)
    if not missing or _reads_as_question(reply):
        return reply
    return f"{reply.strip()} {_follow_up_question(missing)}"


def greeting_for(template_id: str) -> str:
    template = load_template(template_id)
    intro = f"Hi! I'll help you draft your {template['title']}."
    return _ensure_follow_up(template, {}, intro)


def _response_schema(template: dict) -> dict:
    field_keys = [field["key"] for field in template["fields"]]
    other_ids = [entry["id"] for entry in all_template_titles() if entry["id"] != template["id"]]
    properties = {"reply": {"type": "string"}}
    properties.update({key: {"type": ["string", "null"]} for key in field_keys})
    properties["requested_different_document"] = {
        "type": ["string", "null"],
        "enum": [None, *other_ids],
    }
    return {
        "type": "json_schema",
        "json_schema": {
            "name": f"{template['id']}_extraction",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": properties,
                "required": ["reply", "requested_different_document", *field_keys],
                "additionalProperties": False,
            },
        },
    }


def _system_prompt(template: dict, known_fields: dict[str, str | None]) -> str:
    field_lines = "\n".join(
        f"- {field['key']} ({field['label']}, "
        f"{'required' if field['required'] else 'optional'})"
        for field in template["fields"]
    )
    known = json.dumps({k: v for k, v in known_fields.items() if v}, indent=2)
    other_entries = "\n".join(
        f"- {entry['id']}: {entry['title']}"
        for entry in all_template_titles()
        if entry["id"] != template["id"]
    )
    return (
        f"You are a friendly assistant helping a user fill out a {template['title']}. "
        "Have a natural conversation: ask about a couple of missing fields at a time, "
        "don't interrogate the user with a giant list at once. "
        "Extract field values from the whole conversation so far, including the latest "
        "message. Always return the complete set of fields you know so far (not just new "
        "ones) - if the user corrects an earlier answer, update that field. Leave a field "
        "null if it's still unknown. Do not give legal advice; if asked, politely redirect "
        "to filling out the document.\n\n"
        f"Fields to collect:\n{field_lines}\n\n"
        f"Fields already known:\n{known}\n\n"
        "If any required field is still unknown after your reply, you must end your reply "
        "with a direct question about one or two of the missing required fields - never end "
        "your turn with only an acknowledgement while required fields remain unknown. "
        "Once all required fields are known, tell the user the document is ready to "
        "download using the button on the right.\n\n"
        f"You can only help draft a {template['title']} right now. If the user's latest "
        f"message is asking for a different kind of document instead, do not guess or "
        f"extract {template['title']} field values from that request. Instead set "
        "requested_different_document to the id of the closest match from the list below, "
        "and write a short reply explaining you can't help with that here but naming the "
        "closer match. If nothing below is a reasonable match, leave "
        "requested_different_document null and say so in your reply. Otherwise always leave "
        "requested_different_document null.\n\n"
        f"Other supported documents:\n{other_entries}"
    )


def _api_key() -> str:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise ChatConfigError(
            "OPENROUTER_API_KEY is not set. Create a .env file at the project root "
            "(see .env.example) with your OpenRouter API key."
        )
    return key


def _call_openrouter(messages: list[dict], response_format: dict) -> dict:
    response = httpx.post(
        OPENROUTER_URL,
        headers={"Authorization": f"Bearer {_api_key()}"},
        json={"model": MODEL, "messages": messages, "response_format": response_format},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    content = json.loads(response.json()["choices"][0]["message"]["content"])
    if not isinstance(content, dict):
        raise ValueError(f"Expected a JSON object from the model, got {type(content).__name__}")
    return content


def get_chat_reply(template_id: str, request: ChatRequest) -> ChatResponse:
    template = load_template(template_id)
    messages = [
        {"role": "system", "content": _system_prompt(template, request.fields)},
        *[{"role": message.role, "content": message.content} for message in request.messages],
    ]
    response_format = _response_schema(template)
    valid_other_ids = {entry["id"] for entry in all_template_titles() if entry["id"] != template_id}

    last_error: Exception | None = None
    for _ in range(MAX_ATTEMPTS):
        try:
            content = _call_openrouter(messages, response_format)
            reply = content.pop("reply")
            requested_different_document = content.pop("requested_different_document", None)
            if requested_different_document in valid_other_ids:
                return ChatResponse(
                    reply=reply, fields=content, suggested_template_id=requested_different_document
                )
            reply = _ensure_follow_up(template, content, reply)
            return ChatResponse(reply=reply, fields=content)
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as error:
            last_error = error

    raise ChatUpstreamError(
        "The assistant had trouble responding just now. Please try again."
    ) from last_error


def _discovery_response_schema() -> dict:
    ids = [entry["id"] for entry in all_template_titles()]
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "document_discovery",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "reply": {"type": "string"},
                    "matched_template_id": {"type": ["string", "null"], "enum": [None, *ids]},
                },
                "required": ["reply", "matched_template_id"],
                "additionalProperties": False,
            },
        },
    }


def _discovery_system_prompt() -> str:
    entries = "\n".join(
        f"- {summary['id']}: {summary['title']} - {summary['description']}"
        for summary in all_template_summaries()
    )
    return (
        "You are a friendly assistant helping a user figure out which legal document they need. "
        "Have a short, natural conversation - most requests are clear enough to match after one "
        "message, so only ask a clarifying question if their request is genuinely ambiguous between "
        "two or more of the documents below. Do not give legal advice, and do not try to fill in any "
        "of the document's fields yourself - your only job is picking the right document type.\n\n"
        f"Available documents:\n{entries}\n\n"
        "Once you're confident which document matches, set matched_template_id to its id and write a "
        "short reply confirming what you'll help them create - the app will automatically take them "
        "to that document's chat next. If nothing above is a good match, leave matched_template_id "
        "null and say so, and suggest they browse the full list on this page instead. If you need "
        "more detail before you can be confident, leave matched_template_id null and ask one focused "
        "clarifying question."
    )


def discover_document(request: DiscoverRequest) -> DiscoverResponse:
    messages = [
        {"role": "system", "content": _discovery_system_prompt()},
        *[{"role": message.role, "content": message.content} for message in request.messages],
    ]
    response_format = _discovery_response_schema()
    valid_ids = {entry["id"] for entry in all_template_titles()}

    last_error: Exception | None = None
    for _ in range(MAX_ATTEMPTS):
        try:
            content = _call_openrouter(messages, response_format)
            reply = content.pop("reply")
            matched = content.pop("matched_template_id", None)
            matched_template_id = matched if matched in valid_ids else None
            return DiscoverResponse(reply=reply, matched_template_id=matched_template_id)
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as error:
            last_error = error

    raise ChatUpstreamError(
        "The assistant had trouble responding just now. Please try again."
    ) from last_error
