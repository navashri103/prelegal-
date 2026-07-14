import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.chat import ChatMessage, ChatUpstreamError, DiscoverRequest, discover_document
from app.main import app


def _mock_openrouter_response(payload: dict) -> MagicMock:
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "choices": [{"message": {"content": json.dumps(payload)}}]
    }
    return mock_response


def test_discover_greeting_endpoint():
    with TestClient(app) as client:
        response = client.get("/api/discover/greeting")

    assert response.status_code == 200
    body = response.json()
    assert body["reply"]
    assert body["matched_template_id"] is None


def test_discover_message_returns_matched_template(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    llm_payload = {
        "reply": "Sounds like you need a Residential Rental/Lease Agreement!",
        "matched_template_id": "rental_agreement",
    }

    with patch("app.chat.httpx.post", return_value=_mock_openrouter_response(llm_payload)):
        result = discover_document(
            DiscoverRequest(messages=[ChatMessage(role="user", content="I need to lease my apartment")])
        )

    assert result.matched_template_id == "rental_agreement"
    assert result.reply == llm_payload["reply"]


def test_discover_message_ignores_hallucinated_template_id(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    llm_payload = {"reply": "Could you tell me more?", "matched_template_id": "not-a-real-template"}

    with patch("app.chat.httpx.post", return_value=_mock_openrouter_response(llm_payload)):
        result = discover_document(
            DiscoverRequest(messages=[ChatMessage(role="user", content="I need some kind of document")])
        )

    assert result.matched_template_id is None


def test_discover_message_leaves_matched_template_null_when_unclear(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    llm_payload = {"reply": "Could you tell me a bit more about what you need?", "matched_template_id": None}

    with patch("app.chat.httpx.post", return_value=_mock_openrouter_response(llm_payload)):
        result = discover_document(
            DiscoverRequest(messages=[ChatMessage(role="user", content="I need a document")])
        )

    assert result.matched_template_id is None
    assert result.reply == llm_payload["reply"]


def test_discover_message_endpoint_returns_503_without_api_key(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    with TestClient(app) as client:
        response = client.post(
            "/api/discover/message", json={"messages": [{"role": "user", "content": "hi"}]}
        )

    assert response.status_code == 503


def test_discover_message_raises_upstream_error_on_malformed_content(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"choices": [{"message": {"content": ""}}]}

    with patch("app.chat.httpx.post", return_value=mock_response):
        with pytest.raises(ChatUpstreamError):
            discover_document(DiscoverRequest(messages=[ChatMessage(role="user", content="hi")]))


def test_discovery_response_schema_enum_covers_all_template_ids():
    from app.chat import _discovery_response_schema
    from app.document_templates import all_template_titles

    schema = _discovery_response_schema()["json_schema"]["schema"]
    allowed = schema["properties"]["matched_template_id"]["enum"]

    assert set(allowed) == {entry["id"] for entry in all_template_titles()} | {None}
