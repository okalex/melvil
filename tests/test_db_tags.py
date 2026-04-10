"""Tests for melvil.db.tags — CRUD helpers."""

from __future__ import annotations

import sqlite3
import pytest

from melvil.db.connection import migrate
from melvil.db import assets as assets_db
from melvil.db import tags as tags_db


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.execute("PRAGMA foreign_keys = ON")
    c.row_factory = sqlite3.Row
    migrate(c)
    yield c
    c.close()


@pytest.fixture
def asset_id(conn):
    id_ = "aaaaaaaa-0000-4000-8000-000000000001"
    assets_db.insert_asset(
        conn,
        id=id_,
        name="Red Metal",
        type="MATERIAL",
        blend_path="materials/red_metal.blend",
    )
    return id_


def test_get_or_create_tag_creates(conn):
    tag_id = tags_db.get_or_create_tag(conn, "metal")
    assert isinstance(tag_id, int)


def test_get_or_create_tag_is_idempotent(conn):
    id1 = tags_db.get_or_create_tag(conn, "metal")
    id2 = tags_db.get_or_create_tag(conn, "metal")
    assert id1 == id2


def test_list_tags_empty(conn):
    assert tags_db.list_tags(conn) == []


def test_list_tags_returns_all(conn):
    tags_db.get_or_create_tag(conn, "metal")
    tags_db.get_or_create_tag(conn, "shiny")
    rows = tags_db.list_tags(conn)
    names = [r["name"] for r in rows]
    assert "metal" in names
    assert "shiny" in names


def test_add_asset_tag(conn, asset_id):
    tags_db.add_asset_tag(conn, asset_id, "metal")
    assert "metal" in tags_db.get_asset_tags(conn, asset_id)


def test_add_asset_tag_is_idempotent(conn, asset_id):
    tags_db.add_asset_tag(conn, asset_id, "metal")
    tags_db.add_asset_tag(conn, asset_id, "metal")  # must not raise
    assert tags_db.get_asset_tags(conn, asset_id).count("metal") == 1


def test_remove_asset_tag(conn, asset_id):
    tags_db.add_asset_tag(conn, asset_id, "metal")
    tags_db.remove_asset_tag(conn, asset_id, "metal")
    assert "metal" not in tags_db.get_asset_tags(conn, asset_id)


def test_remove_nonexistent_tag_is_noop(conn, asset_id):
    tags_db.remove_asset_tag(conn, asset_id, "ghost")  # must not raise


def test_get_asset_tags_empty(conn, asset_id):
    assert tags_db.get_asset_tags(conn, asset_id) == []


def test_list_assets_for_tag(conn, asset_id):
    tags_db.add_asset_tag(conn, asset_id, "metal")
    rows = tags_db.list_assets_for_tag(conn, "metal")
    assert len(rows) == 1
    assert rows[0]["id"] == asset_id


def test_delete_asset_cascades_to_asset_tags(conn, asset_id):
    tags_db.add_asset_tag(conn, asset_id, "metal")
    assets_db.delete_asset(conn, asset_id)
    # ON DELETE CASCADE should have cleaned up asset_tags
    rows = conn.execute(
        "SELECT * FROM asset_tags WHERE asset_id = ?", (asset_id,)
    ).fetchall()
    assert rows == []
