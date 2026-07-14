import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "prelegal.db"

SCHEMA = """
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def init_db(db_path: Path = DB_PATH) -> None:
    """Recreate the SQLite database from scratch with a fresh schema."""
    db_path.unlink(missing_ok=True)
    connection = sqlite3.connect(db_path)
    try:
        connection.executescript(SCHEMA)
        connection.commit()
    finally:
        connection.close()
