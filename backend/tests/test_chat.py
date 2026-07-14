import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.chat import ChatMessage, ChatRequest, ChatUpstreamError, empty_fields, get_chat_reply, load_template
from app.main import app


def test_greeting_endpoint_returns_all_null_fields():
    with TestClient(app) as client:
        response = client.get("/api/chat/greeting")

    assert response.status_code == 200
    body = response.json()
    assert body["reply"]
    assert set(body["fields"].keys()) == set(empty_fields().keys())
    assert all(value is None for value in body["fields"].values())


def test_chat_message_returns_503_without_api_key(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    with TestClient(app) as client:
        response = client.post(
            "/api/chat/message",
            json={"messages": [{"role": "user", "content": "hi"}], "fields": empty_fields()},
        )

    assert response.status_code == 503


def _mock_openrouter_response(payload: dict) -> MagicMock:
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "choices": [{"message": {"content": json.dumps(payload)}}]
    }
    return mock_response


def test_get_chat_reply_parses_llm_response(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    fields = empty_fields()
    llm_payload = {"reply": "Got it, thanks!", **{**fields, "party_a_name": "Acme Corp"}}

    with patch("app.chat.httpx.post", return_value=_mock_openrouter_response(llm_payload)):
        result = get_chat_reply(
            ChatRequest(messages=[ChatMessage(role="user", content="It's Acme Corp")], fields=fields)
        )

    assert result.reply == "Got it, thanks!"
    assert result.fields["party_a_name"] == "Acme Corp"
    assert "reply" not in result.fields


def test_get_chat_reply_raises_upstream_error_on_malformed_content(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    fields = empty_fields()
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"choices": [{"message": {"content": ""}}]}

    with patch("app.chat.httpx.post", return_value=mock_response):
        with pytest.raises(ChatUpstreamError):
            get_chat_reply(
                ChatRequest(messages=[ChatMessage(role="user", content="hi")], fields=fields)
            )


@pytest.mark.parametrize("content", [None, "null", "[]", '"just a string"'])
def test_get_chat_reply_raises_upstream_error_on_non_dict_content(monkeypatch, content):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    fields = empty_fields()
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"choices": [{"message": {"content": content}}]}

    with patch("app.chat.httpx.post", return_value=mock_response):
        with pytest.raises(ChatUpstreamError):
            get_chat_reply(
                ChatRequest(messages=[ChatMessage(role="user", content="hi")], fields=fields)
            )


def test_chat_message_returns_502_on_upstream_error(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"choices": [{"message": {"content": "not json"}}]}

    with patch("app.chat.httpx.post", return_value=mock_response):
        with TestClient(app) as client:
            response = client.post(
                "/api/chat/message",
                json={"messages": [{"role": "user", "content": "hi"}], "fields": empty_fields()},
            )

    assert response.status_code == 502


def test_response_schema_covers_all_template_fields():
    from app.chat import _response_schema

    template = load_template()
    schema = _response_schema(template)["json_schema"]["schema"]

    field_keys = {field["key"] for field in template["fields"]}
    assert field_keys.issubset(schema["properties"].keys())
    assert "reply" in schema["properties"]
    assert set(schema["required"]) == field_keys | {"reply"}
    assert schema["additionalProperties"] is False
