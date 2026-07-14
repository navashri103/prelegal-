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


def test_init_db_recreates_from_scratch(tmp_path):
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

    assert count == 0
