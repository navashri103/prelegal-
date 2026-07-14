from fastapi.testclient import TestClient

from app.main import app


def _signup(client: TestClient, email: str = "a@example.com") -> None:
    client.post("/api/auth/signup", json={"email": email, "password": "correcthorse"})


def test_create_document_seeds_greeting_and_empty_fields():
    with TestClient(app) as client:
        _signup(client)
        response = client.post("/api/documents", json={"template_id": "nda"})

    assert response.status_code == 201
    body = response.json()
    assert body["template_id"] == "nda"
    assert body["status"] == "in_progress"
    assert len(body["messages"]) == 1
    assert body["messages"][0]["role"] == "assistant"
    assert all(value is None for value in body["fields"].values())


def test_create_document_returns_404_for_unknown_template():
    with TestClient(app) as client:
        _signup(client)
        response = client.post("/api/documents", json={"template_id": "does-not-exist"})

    assert response.status_code == 404


def test_create_document_requires_login():
    with TestClient(app) as client:
        response = client.post("/api/documents", json={"template_id": "nda"})

    assert response.status_code == 401


def test_list_documents_returns_only_the_caller_own_documents():
    with TestClient(app) as client_a:
        _signup(client_a, "a@example.com")
        client_a.post("/api/documents", json={"template_id": "nda"})

    with TestClient(app) as client_b:
        _signup(client_b, "b@example.com")
        client_b.post("/api/documents", json={"template_id": "affidavit"})
        response = client_b.get("/api/documents")

    body = response.json()
    assert len(body) == 1
    assert body[0]["template_id"] == "affidavit"


def test_get_document_returns_full_detail():
    with TestClient(app) as client:
        _signup(client)
        created = client.post("/api/documents", json={"template_id": "nda"}).json()
        response = client.get(f"/api/documents/{created['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_document_returns_404_for_another_users_document():
    with TestClient(app) as client_a:
        _signup(client_a, "a@example.com")
        created = client_a.post("/api/documents", json={"template_id": "nda"}).json()

    with TestClient(app) as client_b:
        _signup(client_b, "b@example.com")
        response = client_b.get(f"/api/documents/{created['id']}")

    assert response.status_code == 404


def test_get_document_returns_404_for_unknown_id():
    with TestClient(app) as client:
        _signup(client)
        response = client.get("/api/documents/999999")

    assert response.status_code == 404


def test_save_document_updates_fields_and_messages():
    with TestClient(app) as client:
        _signup(client)
        created = client.post("/api/documents", json={"template_id": "nda"}).json()
        response = client.put(
            f"/api/documents/{created['id']}",
            json={
                "fields": {"party_a_name": "Acme Corp"},
                "messages": [
                    {"role": "assistant", "content": "Hi"},
                    {"role": "user", "content": "Acme Corp"},
                ],
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["fields"]["party_a_name"] == "Acme Corp"
    assert len(body["messages"]) == 2


def test_save_document_recomputes_status_to_completed_when_all_required_fields_present():
    with TestClient(app) as client:
        _signup(client)
        created = client.post("/api/documents", json={"template_id": "affidavit"}).json()
        all_fields_filled = {key: "some value" for key in created["fields"]}
        response = client.put(
            f"/api/documents/{created['id']}",
            json={"fields": all_fields_filled, "messages": created["messages"]},
        )

    assert response.status_code == 200
    assert response.json()["status"] == "completed"


def test_save_document_returns_404_for_another_users_document():
    with TestClient(app) as client_a:
        _signup(client_a, "a@example.com")
        created = client_a.post("/api/documents", json={"template_id": "nda"}).json()

    with TestClient(app) as client_b:
        _signup(client_b, "b@example.com")
        response = client_b.put(
            f"/api/documents/{created['id']}", json={"fields": {}, "messages": []}
        )

    assert response.status_code == 404


def test_delete_document_removes_it():
    with TestClient(app) as client:
        _signup(client)
        created = client.post("/api/documents", json={"template_id": "nda"}).json()
        delete_response = client.delete(f"/api/documents/{created['id']}")
        get_response = client.get(f"/api/documents/{created['id']}")

    assert delete_response.status_code == 204
    assert get_response.status_code == 404


def test_delete_document_returns_404_for_another_users_document():
    with TestClient(app) as client_a:
        _signup(client_a, "a@example.com")
        created = client_a.post("/api/documents", json={"template_id": "nda"}).json()

    with TestClient(app) as client_b:
        _signup(client_b, "b@example.com")
        response = client_b.delete(f"/api/documents/{created['id']}")

    assert response.status_code == 404
