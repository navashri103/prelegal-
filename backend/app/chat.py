import json
import os
from functools import lru_cache
from pathlib import Path

import httpx
from pydantic import BaseModel

TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "data" / "templates" / "nda.json"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "google/gemma-4-26b-a4b-it:free"
REQUEST_TIMEOUT_SECONDS = 30
MAX_ATTEMPTS = 2

GREETING = (
    "Hi! I'll help you draft a Mutual NDA. Let's start with the basics - "
    "what are the names of the two parties entering into this agreement?"
)


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    fields: dict[str, str | None]


class ChatResponse(BaseModel):
    reply: str
    fields: dict[str, str | None]


class ChatConfigError(RuntimeError):
    pass


class ChatUpstreamError(RuntimeError):
    pass


@lru_cache
def load_template() -> dict:
    return json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))


def empty_fields() -> dict[str, None]:
    return {field["key"]: None for field in load_template()["fields"]}


def _response_schema(template: dict) -> dict:
    field_keys = [field["key"] for field in template["fields"]]
    properties = {"reply": {"type": "string"}}
    properties.update({key: {"type": ["string", "null"]} for key in field_keys})
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "nda_extraction",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": properties,
                "required": ["reply", *field_keys],
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
        "Once all required fields are known, tell the user the document is ready to "
        "download using the button on the right."
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


def get_chat_reply(request: ChatRequest) -> ChatResponse:
    template = load_template()
    messages = [
        {"role": "system", "content": _system_prompt(template, request.fields)},
        *[{"role": message.role, "content": message.content} for message in request.messages],
    ]
    response_format = _response_schema(template)

    last_error: Exception | None = None
    for _ in range(MAX_ATTEMPTS):
        try:
            content = _call_openrouter(messages, response_format)
            reply = content.pop("reply")
            return ChatResponse(reply=reply, fields=content)
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as error:
            last_error = error

    raise ChatUpstreamError(
        "The assistant had trouble responding just now. Please try again."
    ) from last_error
