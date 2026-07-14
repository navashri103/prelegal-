import sqlite3

from app.db import init_db


def test_init_db_creates_users_table(tmp_path):
    db_path = tmp_path / "test.db"

    init_db(db_path)

    connection = sqlite3.connect(db_path)
    try:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(users)")}
    finally:
        connection.close()

    assert columns == {"id", "email", "password_hash", "created_at"}


def test_init_db_creates_sessions_table(tmp_path):
    db_path = tmp_path / "test.db"

    init_db(db_path)

    connection = sqlite3.connect(db_path)
    try:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(sessions)")}
    finally:
        connection.close()

    assert columns == {"id", "user_id", "token_hash", "created_at", "expires_at"}


def test_init_db_creates_documents_table(tmp_path):
    db_path = tmp_path / "test.db"

    init_db(db_path)

    connection = sqlite3.connect(db_path)
    try:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(documents)")}
    finally:
        connection.close()

    assert columns == {
        "id",
        "user_id",
        "template_id",
        "status",
        "fields_json",
        "messages_json",
        "created_at",
        "updated_at",
    }


def test_init_db_is_idempotent_and_preserves_existing_rows(tmp_path):
    db_path = tmp_path / "test.db"
    init_db(db_path)
    connection = sqlite3.connect(db_path)
    connection.execute(
        "INSERT INTO users (email, password_hash) VALUES ('a@example.com', 'x')"
    )
    connection.commit()
    connection.close()

    init_db(db_path)

    connection = sqlite3.connect(db_path)
    try:
        count = connection.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    finally:
        connection.close()

    assert count == 1
