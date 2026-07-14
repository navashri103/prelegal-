import pytest

from app import db


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Point every test at a fresh, isolated SQLite file instead of the real dev DB.

    Required now that init_db() no longer wipes the database on every startup -
    without this, tests would accumulate rows in a shared local file across runs.
    """
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
