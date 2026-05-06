"""Tests for blammo.db.connection — open_db and migration runner."""

from __future__ import annotations

import sqlite3
import pytest

from blammo.db.connection import migrate, open_db, _get_version
from blammo.db.migrations import LATEST_VERSION


@pytest.fixture
def conn():
    """In-memory DB, configured but NOT yet migrated."""
    c = sqlite3.connect(":memory:")
    c.execute("PRAGMA foreign_keys = ON")
    c.row_factory = sqlite3.Row
    yield c
    c.close()


def test_migrate_creates_assets_table(conn):
    migrate(conn)
    tables = {
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    assert "assets" in tables


def test_migrate_creates_tags_tables(conn):
    migrate(conn)
    tables = {
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    assert "tags" in tables
    assert "asset_tags" in tables


def test_migrate_sets_user_version(conn):
    migrate(conn)
    assert _get_version(conn) == LATEST_VERSION


def test_migrate_is_idempotent(conn):
    migrate(conn)
    migrate(conn)  # second call must not raise or re-apply
    assert _get_version(conn) == LATEST_VERSION


def test_open_db_creates_and_migrates(tmp_path):
    db_file = tmp_path / "test.db"
    with open_db(db_file) as c:
        assert _get_version(c) == LATEST_VERSION


def test_open_db_closes_on_exit(tmp_path):
    db_file = tmp_path / "test.db"
    with open_db(db_file) as c:
        pass
    # After exit the connection should be closed; any use raises.
    with pytest.raises(Exception):
        c.execute("SELECT 1")


def test_foreign_keys_enforced(conn):
    migrate(conn)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO asset_tags (asset_id, tag_id) VALUES (?, ?)",
            ("nonexistent-uuid", 999),
        )
        conn.commit()
