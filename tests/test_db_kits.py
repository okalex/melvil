"""Tests for blammo.db.kits — CRUD helpers."""

from __future__ import annotations

import sqlite3
import pytest

from blammo.db.connection import migrate
from blammo.db import kits as kits_db
from blammo.db.kits import DEFAULT_KIT_ID


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.execute("PRAGMA foreign_keys = ON")
    c.row_factory = sqlite3.Row
    migrate(c)
    yield c
    c.close()


KIT_A = dict(id="aaaaaaaa-0000-4000-8000-000000000002", name="Campaign Assets")
KIT_B = dict(id="aaaaaaaa-0000-4000-8000-000000000003", name="Game Project")


# ---------------------------------------------------------------------------
# Migration seed
# ---------------------------------------------------------------------------


def test_migration_creates_general_kit(conn):
    row = kits_db.get_kit(conn, DEFAULT_KIT_ID)
    assert row is not None
    assert row["name"] == "General"


# ---------------------------------------------------------------------------
# insert_kit
# ---------------------------------------------------------------------------


def test_insert_and_get(conn):
    kits_db.insert_kit(conn, **KIT_A)
    row = kits_db.get_kit(conn, KIT_A["id"])
    assert row is not None
    assert row["name"] == KIT_A["name"]
    assert row["description"] is None


def test_insert_with_description(conn):
    kits_db.insert_kit(conn, **KIT_A, description="Assets for the ad campaign")
    row = kits_db.get_kit(conn, KIT_A["id"])
    assert row["description"] == "Assets for the ad campaign"


def test_insert_sets_timestamps(conn):
    kits_db.insert_kit(conn, **KIT_A)
    row = kits_db.get_kit(conn, KIT_A["id"])
    assert row["created_at"] is not None
    assert row["updated_at"] is not None


# ---------------------------------------------------------------------------
# get_kit
# ---------------------------------------------------------------------------


def test_get_nonexistent_returns_none(conn):
    assert kits_db.get_kit(conn, "does-not-exist") is None


# ---------------------------------------------------------------------------
# get_kit_by_name
# ---------------------------------------------------------------------------


def test_get_kit_by_name(conn):
    kits_db.insert_kit(conn, **KIT_A)
    row = kits_db.get_kit_by_name(conn, KIT_A["name"])
    assert row is not None
    assert row["id"] == KIT_A["id"]


def test_get_kit_by_name_case_insensitive(conn):
    kits_db.insert_kit(conn, **KIT_A)
    row = kits_db.get_kit_by_name(conn, KIT_A["name"].lower())
    assert row is not None
    assert row["id"] == KIT_A["id"]


def test_get_kit_by_name_not_found(conn):
    assert kits_db.get_kit_by_name(conn, "Nonexistent") is None


# ---------------------------------------------------------------------------
# list_kits
# ---------------------------------------------------------------------------


def test_list_kits_contains_general(conn):
    rows = kits_db.list_kits(conn)
    assert len(rows) == 1
    assert rows[0]["name"] == "General"


def test_list_kits_returns_all_sorted(conn):
    kits_db.insert_kit(conn, **KIT_B)
    kits_db.insert_kit(conn, **KIT_A)
    rows = kits_db.list_kits(conn)
    # General, Campaign Assets, Game Project → sorted alphabetically
    names = [r["name"] for r in rows]
    assert names == sorted(names)
    assert len(rows) == 3


# ---------------------------------------------------------------------------
# update_kit
# ---------------------------------------------------------------------------


def test_update_kit_name(conn):
    kits_db.insert_kit(conn, **KIT_A)
    kits_db.update_kit(conn, KIT_A["id"], name="Renamed Kit")
    row = kits_db.get_kit(conn, KIT_A["id"])
    assert row["name"] == "Renamed Kit"


def test_update_kit_description(conn):
    kits_db.insert_kit(conn, **KIT_A)
    kits_db.update_kit(conn, KIT_A["id"], description="New description")
    row = kits_db.get_kit(conn, KIT_A["id"])
    assert row["description"] == "New description"


def test_update_kit_updates_updated_at(conn):
    kits_db.insert_kit(conn, **KIT_A)
    kits_db.update_kit(conn, KIT_A["id"], name="Changed")
    row = kits_db.get_kit(conn, KIT_A["id"])
    assert row["updated_at"] is not None


def test_update_kit_no_fields_is_noop(conn):
    kits_db.insert_kit(conn, **KIT_A)
    before = kits_db.get_kit(conn, KIT_A["id"])["updated_at"]
    kits_db.update_kit(conn, KIT_A["id"])
    after = kits_db.get_kit(conn, KIT_A["id"])["updated_at"]
    assert before == after


def test_update_general_kit_name(conn):
    """The General kit can be renamed like any other kit."""
    kits_db.update_kit(conn, DEFAULT_KIT_ID, name="My Library")
    row = kits_db.get_kit(conn, DEFAULT_KIT_ID)
    assert row["name"] == "My Library"
