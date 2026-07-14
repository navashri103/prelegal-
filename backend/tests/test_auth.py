from fastapi.testclient import TestClient

from app.main import app


def test_signup_creates_user_and_sets_session_cookie():
    with TestClient(app) as client:
        response = client.post(
            "/api/auth/signup", json={"email": "a@example.com", "password": "correcthorse"}
        )

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "a@example.com"
    assert "id" in body
    assert "session_token" in response.cookies


def test_signup_rejects_duplicate_email():
    with TestClient(app) as client:
        client.post("/api/auth/signup", json={"email": "a@example.com", "password": "correcthorse"})
        response = client.post(
            "/api/auth/signup", json={"email": "a@example.com", "password": "differentpw"}
        )

    assert response.status_code == 409


def test_signup_rejects_invalid_email():
    with TestClient(app) as client:
        response = client.post(
            "/api/auth/signup", json={"email": "not-an-email", "password": "correcthorse"}
        )

    assert response.status_code == 400


def test_signup_rejects_short_password():
    with TestClient(app) as client:
        response = client.post(
            "/api/auth/signup", json={"email": "a@example.com", "password": "short"}
        )

    assert response.status_code == 400


def test_signup_rejects_password_over_72_utf8_bytes_not_just_72_characters():
    # Each emoji is 4 UTF-8 bytes: 20 of them is only 20 *characters* (well under a
    # naive 72-character check) but 80 *bytes* - over bcrypt's real 72-byte limit.
    password = "\U0001F600" * 20

    with TestClient(app) as client:
        response = client.post(
            "/api/auth/signup", json={"email": "a@example.com", "password": password}
        )

    assert response.status_code == 400


def test_signup_stores_hashed_not_plaintext_password():
    with TestClient(app) as client:
        client.post("/api/auth/signup", json={"email": "a@example.com", "password": "correcthorse"})

    from app.db import get_connection

    connection = get_connection()
    try:
        row = connection.execute(
            "SELECT password_hash FROM users WHERE email = 'a@example.com'"
        ).fetchone()
    finally:
        connection.close()

    assert row["password_hash"] != "correcthorse"
    assert row["password_hash"].startswith("$2b$")


def test_login_succeeds_with_correct_credentials():
    with TestClient(app) as client:
        client.post("/api/auth/signup", json={"email": "a@example.com", "password": "correcthorse"})
        response = client.post(
            "/api/auth/login", json={"email": "a@example.com", "password": "correcthorse"}
        )

    assert response.status_code == 200
    assert response.json()["email"] == "a@example.com"


def test_login_fails_with_wrong_password():
    with TestClient(app) as client:
        client.post("/api/auth/signup", json={"email": "a@example.com", "password": "correcthorse"})
        response = client.post(
            "/api/auth/login", json={"email": "a@example.com", "password": "wrongpassword"}
        )

    assert response.status_code == 401


def test_login_fails_for_unknown_email():
    with TestClient(app) as client:
        response = client.post(
            "/api/auth/login", json={"email": "nobody@example.com", "password": "correcthorse"}
        )

    assert response.status_code == 401


def test_me_returns_401_when_signed_out():
    with TestClient(app) as client:
        response = client.get("/api/auth/me")

    assert response.status_code == 401


def test_me_returns_user_when_signed_in():
    with TestClient(app) as client:
        client.post("/api/auth/signup", json={"email": "a@example.com", "password": "correcthorse"})
        response = client.get("/api/auth/me")

    assert response.status_code == 200
    assert response.json()["email"] == "a@example.com"


def test_logout_clears_session():
    with TestClient(app) as client:
        client.post("/api/auth/signup", json={"email": "a@example.com", "password": "correcthorse"})
        logout_response = client.post("/api/auth/logout")
        me_response = client.get("/api/auth/me")

    assert logout_response.status_code == 204
    assert me_response.status_code == 401


def test_logout_without_a_session_is_a_no_op():
    with TestClient(app) as client:
        response = client.post("/api/auth/logout")

    assert response.status_code == 204
