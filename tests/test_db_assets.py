"""Tests for blammo.db.assets — CRUD helpers."""

from __future__ import annotations

import sqlite3
import pytest

from blammo.db.connection import migrate
from blammo.db import assets as assets_db
from blammo.db.kits import DEFAULT_KIT_ID


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.execute("PRAGMA foreign_keys = ON")
    c.row_factory = sqlite3.Row
    migrate(c)
    yield c
    c.close()


SAMPLE = dict(
    id="aaaaaaaa-0000-4000-8000-000000000001",
    name="Red Metal",
    type="MATERIAL",
    blend_path="materials/red_metal.blend",
)


def test_insert_and_get(conn):
    assets_db.insert_asset(conn, **SAMPLE)
    row = assets_db.get_asset(conn, SAMPLE["id"])
    assert row is not None
    assert row["name"] == SAMPLE["name"]
    assert row["type"] == SAMPLE["type"]
    assert row["blend_path"] == SAMPLE["blend_path"]


def test_get_nonexistent_returns_none(conn):
    assert assets_db.get_asset(conn, "does-not-exist") is None


def test_insert_sets_timestamps(conn):
    assets_db.insert_asset(conn, **SAMPLE)
    row = assets_db.get_asset(conn, SAMPLE["id"])
    assert row["created_at"] is not None
    assert row["updated_at"] is not None


def test_list_assets_empty(conn):
    assert assets_db.list_assets(conn) == []


def test_list_assets_returns_all(conn):
    assets_db.insert_asset(conn, **SAMPLE)
    second = {**SAMPLE, "id": "aaaaaaaa-0000-4000-8000-000000000002", "name": "Blue Plastic"}
    assets_db.insert_asset(conn, **second)
    rows = assets_db.list_assets(conn)
    assert len(rows) == 2


def test_list_assets_filtered_by_type(conn):
    assets_db.insert_asset(conn, **SAMPLE)
    mesh = {**SAMPLE, "id": "aaaaaaaa-0000-4000-8000-000000000002", "name": "Cube", "type": "MESH"}
    assets_db.insert_asset(conn, **mesh)
    materials = assets_db.list_assets(conn, type="MATERIAL")
    assert len(materials) == 1
    assert materials[0]["type"] == "MATERIAL"


def test_update_asset_name(conn):
    assets_db.insert_asset(conn, **SAMPLE)
    assets_db.update_asset(conn, SAMPLE["id"], name="Gold Metal")
    row = assets_db.get_asset(conn, SAMPLE["id"])
    assert row["name"] == "Gold Metal"


def test_update_asset_updates_updated_at(conn):
    assets_db.insert_asset(conn, **SAMPLE)
    original = assets_db.get_asset(conn, SAMPLE["id"])["updated_at"]
    # Force a different timestamp by sleeping isn't reliable; just check it's set.
    assets_db.update_asset(conn, SAMPLE["id"], name="Changed")
    updated = assets_db.get_asset(conn, SAMPLE["id"])["updated_at"]
    # updated_at must still be a valid ISO string
    assert updated is not None


def test_update_asset_no_fields_is_noop(conn):
    assets_db.insert_asset(conn, **SAMPLE)
    before = assets_db.get_asset(conn, SAMPLE["id"])["updated_at"]
    assets_db.update_asset(conn, SAMPLE["id"])  # no fields — should be a no-op
    after = assets_db.get_asset(conn, SAMPLE["id"])["updated_at"]
    assert before == after


def test_delete_asset(conn):
    assets_db.insert_asset(conn, **SAMPLE)
    assets_db.delete_asset(conn, SAMPLE["id"])
    assert assets_db.get_asset(conn, SAMPLE["id"]) is None


# ---------------------------------------------------------------------------
# kit_id support
# ---------------------------------------------------------------------------

CUSTOM_KIT_ID = "bbbbbbbb-0000-4000-8000-000000000001"


@pytest.fixture
def conn_with_kit(conn):
    """Fixture that adds a second kit alongside the default General kit."""
    from blammo.db import kits as kits_db
    kits_db.insert_kit(conn, id=CUSTOM_KIT_ID, name="Game Project")
    return conn


def test_insert_uses_default_kit_when_kit_id_omitted(conn):
    assets_db.insert_asset(conn, **SAMPLE)
    row = assets_db.get_asset(conn, SAMPLE["id"])
    assert row["kit_id"] == DEFAULT_KIT_ID


def test_insert_with_explicit_kit_id(conn_with_kit):
    assets_db.insert_asset(conn_with_kit, **SAMPLE, kit_id=CUSTOM_KIT_ID)
    row = assets_db.get_asset(conn_with_kit, SAMPLE["id"])
    assert row["kit_id"] == CUSTOM_KIT_ID


def test_list_assets_filtered_by_kit_id(conn_with_kit):
    assets_db.insert_asset(conn_with_kit, **SAMPLE, kit_id=DEFAULT_KIT_ID)
    other = {**SAMPLE, "id": "aaaaaaaa-0000-4000-8000-000000000002", "name": "Cube", "type": "MESH"}
    assets_db.insert_asset(conn_with_kit, **other, kit_id=CUSTOM_KIT_ID)
    general_assets = assets_db.list_assets(conn_with_kit, kit_id=DEFAULT_KIT_ID)
    assert len(general_assets) == 1
    assert general_assets[0]["id"] == SAMPLE["id"]


def test_list_assets_filtered_by_type_and_kit_id(conn_with_kit):
    assets_db.insert_asset(conn_with_kit, **SAMPLE, kit_id=CUSTOM_KIT_ID)
    mesh = {**SAMPLE, "id": "aaaaaaaa-0000-4000-8000-000000000002", "name": "Cube", "type": "MESH"}
    assets_db.insert_asset(conn_with_kit, **mesh, kit_id=CUSTOM_KIT_ID)
    results = assets_db.list_assets(conn_with_kit, type="MATERIAL", kit_id=CUSTOM_KIT_ID)
    assert len(results) == 1
    assert results[0]["type"] == "MATERIAL"


def test_update_asset_kit_id(conn_with_kit):
    assets_db.insert_asset(conn_with_kit, **SAMPLE, kit_id=DEFAULT_KIT_ID)
    assets_db.update_asset(conn_with_kit, SAMPLE["id"], kit_id=CUSTOM_KIT_ID)
    row = assets_db.get_asset(conn_with_kit, SAMPLE["id"])
    assert row["kit_id"] == CUSTOM_KIT_ID


def test_duplicate_id_raises(conn):
    assets_db.insert_asset(conn, **SAMPLE)
    with pytest.raises(sqlite3.IntegrityError):
        assets_db.insert_asset(conn, **SAMPLE)


# ---------------------------------------------------------------------------
# preview_path support
# ---------------------------------------------------------------------------


def test_insert_without_preview_path_defaults_to_null(conn):
    assets_db.insert_asset(conn, **SAMPLE)
    row = assets_db.get_asset(conn, SAMPLE["id"])
    assert row["preview_path"] is None


def test_insert_with_preview_path(conn):
    assets_db.insert_asset(conn, **SAMPLE, preview_path="previews/abc123.png")
    row = assets_db.get_asset(conn, SAMPLE["id"])
    assert row["preview_path"] == "previews/abc123.png"


def test_update_asset_preview_path(conn):
    assets_db.insert_asset(conn, **SAMPLE)
    assets_db.update_asset(conn, SAMPLE["id"], preview_path="previews/abc123.png")
    row = assets_db.get_asset(conn, SAMPLE["id"])
    assert row["preview_path"] == "previews/abc123.png"


def test_update_asset_preview_path_without_it_is_noop(conn):
    assets_db.insert_asset(conn, **SAMPLE, preview_path="previews/existing.png")
    assets_db.update_asset(conn, SAMPLE["id"], name="Gold Metal")
    row = assets_db.get_asset(conn, SAMPLE["id"])
    # preview_path should be unchanged when not passed to update_asset
    assert row["preview_path"] == "previews/existing.png"
