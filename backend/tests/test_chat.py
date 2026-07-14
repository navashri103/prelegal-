import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.chat import ChatMessage, ChatRequest, ChatUpstreamError, _ensure_follow_up, get_chat_reply, greeting_for
from app.document_templates import empty_fields, load_template
from app.main import app


def test_greeting_endpoint_returns_all_null_fields():
    with TestClient(app) as client:
        response = client.get("/api/chat/nda/greeting")

    assert response.status_code == 200
    body = response.json()
    assert body["reply"]
    assert set(body["fields"].keys()) == set(empty_fields("nda").keys())
    assert all(value is None for value in body["fields"].values())


def test_greeting_endpoint_returns_404_for_unknown_template():
    with TestClient(app) as client:
        response = client.get("/api/chat/does-not-exist/greeting")

    assert response.status_code == 404


@pytest.mark.parametrize("template_id", ["nda", "rental_agreement", "affidavit"])
def test_greeting_for_every_template_ends_in_a_question(template_id):
    assert greeting_for(template_id).strip().endswith("?")


def test_chat_message_returns_503_without_api_key(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    with TestClient(app) as client:
        response = client.post(
            "/api/chat/nda/message",
            json={"messages": [{"role": "user", "content": "hi"}], "fields": empty_fields("nda")},
        )

    assert response.status_code == 503


def test_chat_message_returns_404_for_unknown_template(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    with TestClient(app) as client:
        response = client.post(
            "/api/chat/does-not-exist/message",
            json={"messages": [{"role": "user", "content": "hi"}], "fields": {}},
        )

    assert response.status_code == 404


def _mock_openrouter_response(payload: dict) -> MagicMock:
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "choices": [{"message": {"content": json.dumps(payload)}}]
    }
    return mock_response


@pytest.mark.parametrize("template_id", ["nda", "rental_agreement"])
def test_get_chat_reply_parses_llm_response(monkeypatch, template_id):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    fields = empty_fields(template_id)
    first_field_key = next(iter(fields))
    llm_payload = {
        "reply": "Got it, thanks! What else can you tell me?",
        **{**fields, first_field_key: "Acme Corp"},
    }

    with patch("app.chat.httpx.post", return_value=_mock_openrouter_response(llm_payload)):
        result = get_chat_reply(
            template_id,
            ChatRequest(messages=[ChatMessage(role="user", content="It's Acme Corp")], fields=fields),
        )

    assert result.fields[first_field_key] == "Acme Corp"
    assert "reply" not in result.fields


def test_get_chat_reply_raises_upstream_error_on_malformed_content(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    fields = empty_fields("nda")
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"choices": [{"message": {"content": ""}}]}

    with patch("app.chat.httpx.post", return_value=mock_response):
        with pytest.raises(ChatUpstreamError):
            get_chat_reply(
                "nda", ChatRequest(messages=[ChatMessage(role="user", content="hi")], fields=fields)
            )


@pytest.mark.parametrize("content", [None, "null", "[]", '"just a string"'])
def test_get_chat_reply_raises_upstream_error_on_non_dict_content(monkeypatch, content):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    fields = empty_fields("nda")
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"choices": [{"message": {"content": content}}]}

    with patch("app.chat.httpx.post", return_value=mock_response):
        with pytest.raises(ChatUpstreamError):
            get_chat_reply(
                "nda", ChatRequest(messages=[ChatMessage(role="user", content="hi")], fields=fields)
            )


def test_chat_message_returns_502_on_upstream_error(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"choices": [{"message": {"content": "not json"}}]}

    with patch("app.chat.httpx.post", return_value=mock_response):
        with TestClient(app) as client:
            response = client.post(
                "/api/chat/nda/message",
                json={"messages": [{"role": "user", "content": "hi"}], "fields": empty_fields("nda")},
            )

    assert response.status_code == 502


def test_response_schema_covers_all_template_fields():
    from app.chat import _response_schema

    template = load_template("nda")
    schema = _response_schema(template)["json_schema"]["schema"]

    field_keys = {field["key"] for field in template["fields"]}
    assert field_keys.issubset(schema["properties"].keys())
    assert "reply" in schema["properties"]
    assert set(schema["required"]) == field_keys | {"reply", "requested_different_document"}
    assert schema["additionalProperties"] is False


def test_response_schema_requested_different_document_excludes_current_template():
    from app.chat import _response_schema

    template = load_template("nda")
    schema = _response_schema(template)["json_schema"]["schema"]

    allowed = schema["properties"]["requested_different_document"]["enum"]
    assert "nda" not in allowed
    assert "rental_agreement" in allowed


def test_get_chat_reply_returns_suggested_template_when_llm_requests_a_different_document(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    fields = empty_fields("nda")
    llm_payload = {
        "reply": "This assistant only drafts NDAs - want to start a rental agreement instead?",
        "requested_different_document": "rental_agreement",
        **fields,
    }

    with patch("app.chat.httpx.post", return_value=_mock_openrouter_response(llm_payload)):
        result = get_chat_reply(
            "nda",
            ChatRequest(messages=[ChatMessage(role="user", content="I need a rental agreement")], fields=fields),
        )

    assert result.suggested_template_id == "rental_agreement"
    assert result.reply == llm_payload["reply"]


def test_get_chat_reply_ignores_hallucinated_requested_different_document(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    fields = empty_fields("nda")
    llm_payload = {
        "reply": "Got it, thanks!",
        "requested_different_document": "not-a-real-template-id",
        **fields,
    }

    with patch("app.chat.httpx.post", return_value=_mock_openrouter_response(llm_payload)):
        result = get_chat_reply(
            "nda", ChatRequest(messages=[ChatMessage(role="user", content="hi")], fields=fields)
        )

    assert result.suggested_template_id is None


def test_get_chat_reply_ignores_requested_different_document_matching_current_template(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    fields = empty_fields("nda")
    llm_payload = {
        "reply": "Got it, thanks!",
        "requested_different_document": "nda",
        **fields,
    }

    with patch("app.chat.httpx.post", return_value=_mock_openrouter_response(llm_payload)):
        result = get_chat_reply(
            "nda", ChatRequest(messages=[ChatMessage(role="user", content="hi")], fields=fields)
        )

    assert result.suggested_template_id is None


def test_ensure_follow_up_appends_question_when_required_fields_missing():
    template = load_template("nda")
    fields = empty_fields("nda")

    result = _ensure_follow_up(template, fields, "Thanks, got that.")

    assert result.startswith("Thanks, got that.")
    assert result.strip().endswith("?")


def test_ensure_follow_up_leaves_reply_unchanged_when_already_a_question():
    template = load_template("nda")
    fields = empty_fields("nda")
    reply = "Thanks! What's the effective date?"

    assert _ensure_follow_up(template, fields, reply) == reply


def test_ensure_follow_up_leaves_reply_unchanged_when_nothing_required_is_missing():
    template = load_template("nda")
    fields = {field["key"]: "some value" for field in template["fields"]}
    reply = "All set, you're ready to download the document."

    assert _ensure_follow_up(template, fields, reply) == reply
