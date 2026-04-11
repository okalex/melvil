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


# ---------------------------------------------------------------------------
# normalize_tag
# ---------------------------------------------------------------------------


def test_normalize_tag_strips_whitespace():
    assert tags_db.normalize_tag("  metal  ") == "metal"


def test_normalize_tag_lowercases():
    assert tags_db.normalize_tag("Metal") == "metal"


def test_normalize_tag_collapses_internal_whitespace():
    assert tags_db.normalize_tag("  PBR  Material  ") == "pbr material"


def test_normalize_tag_empty_after_strip():
    assert tags_db.normalize_tag("   ") == ""


def test_normalize_tag_preserves_hyphens():
    assert tags_db.normalize_tag("hard-surface") == "hard-surface"


# ---------------------------------------------------------------------------
# get_or_create_tag / get_tag_by_id / get_tag_by_name
# ---------------------------------------------------------------------------


def test_get_or_create_tag_creates(conn):
    tag_id = tags_db.get_or_create_tag(conn, "metal")
    assert isinstance(tag_id, str)
    assert len(tag_id) == 36  # UUID format


def test_get_or_create_tag_is_idempotent(conn):
    id1 = tags_db.get_or_create_tag(conn, "metal")
    id2 = tags_db.get_or_create_tag(conn, "metal")
    assert id1 == id2


def test_get_or_create_tag_normalizes(conn):
    id1 = tags_db.get_or_create_tag(conn, "Metal")
    id2 = tags_db.get_or_create_tag(conn, "  metal  ")
    assert id1 == id2


def test_get_or_create_tag_raises_on_empty(conn):
    with pytest.raises(ValueError):
        tags_db.get_or_create_tag(conn, "   ")


def test_get_tag_by_id(conn):
    tag_id = tags_db.get_or_create_tag(conn, "metal")
    row = tags_db.get_tag_by_id(conn, tag_id)
    assert row is not None
    assert row["name"] == "metal"


def test_get_tag_by_name(conn):
    tags_db.get_or_create_tag(conn, "metal")
    row = tags_db.get_tag_by_name(conn, "Metal")  # case-insensitive via normalization
    assert row is not None
    assert row["name"] == "metal"


def test_get_tag_by_name_missing(conn):
    assert tags_db.get_tag_by_name(conn, "ghost") is None


# ---------------------------------------------------------------------------
# list_tags / list_tags_with_usage
# ---------------------------------------------------------------------------


def test_list_tags_empty(conn):
    assert tags_db.list_tags(conn) == []


def test_list_tags_returns_all(conn):
    tags_db.get_or_create_tag(conn, "metal")
    tags_db.get_or_create_tag(conn, "shiny")
    rows = tags_db.list_tags(conn)
    names = [r["name"] for r in rows]
    assert "metal" in names
    assert "shiny" in names


def test_list_tags_with_usage_counts(conn, asset_id):
    tags_db.add_asset_tag(conn, asset_id, "metal")
    tags_db.get_or_create_tag(conn, "unused")
    rows = tags_db.list_tags_with_usage(conn)
    by_name = {r["name"]: r["usage_count"] for r in rows}
    assert by_name["metal"] == 1
    assert by_name["unused"] == 0


# ---------------------------------------------------------------------------
# rename_tag / delete_tag
# ---------------------------------------------------------------------------


def test_rename_tag(conn):
    tag_id = tags_db.get_or_create_tag(conn, "metall")
    tags_db.rename_tag(conn, tag_id, "metal")
    row = tags_db.get_tag_by_id(conn, tag_id)
    assert row["name"] == "metal"


def test_rename_tag_normalizes(conn):
    tag_id = tags_db.get_or_create_tag(conn, "metal")
    tags_db.rename_tag(conn, tag_id, "  METAL  ")
    row = tags_db.get_tag_by_id(conn, tag_id)
    assert row["name"] == "metal"


def test_rename_tag_raises_on_empty(conn):
    tag_id = tags_db.get_or_create_tag(conn, "metal")
    with pytest.raises(ValueError):
        tags_db.rename_tag(conn, tag_id, "   ")


def test_rename_tag_raises_on_conflict(conn):
    tag_id = tags_db.get_or_create_tag(conn, "metal")
    tags_db.get_or_create_tag(conn, "shiny")
    with pytest.raises(ValueError):
        tags_db.rename_tag(conn, tag_id, "shiny")


def test_delete_tag(conn):
    tag_id = tags_db.get_or_create_tag(conn, "metal")
    tags_db.delete_tag(conn, tag_id)
    assert tags_db.get_tag_by_id(conn, tag_id) is None


def test_delete_tag_cascades_to_asset_tags(conn, asset_id):
    tags_db.add_asset_tag(conn, asset_id, "metal")
    tag_id = tags_db.get_tag_by_name(conn, "metal")["id"]
    tags_db.delete_tag(conn, tag_id)
    rows = conn.execute(
        "SELECT * FROM asset_tags WHERE tag_id = ?", (tag_id,)
    ).fetchall()
    assert rows == []


# ---------------------------------------------------------------------------
# autocomplete_tags
# ---------------------------------------------------------------------------


def test_autocomplete_tags_substring_match(conn):
    tags_db.get_or_create_tag(conn, "metal")
    tags_db.get_or_create_tag(conn, "metallic")
    tags_db.get_or_create_tag(conn, "shiny")
    results = tags_db.autocomplete_tags(conn, "met")
    names = [r["name"] for r in results]
    assert "metal" in names
    assert "metallic" in names
    assert "shiny" not in names


def test_autocomplete_tags_respects_limit(conn):
    for i in range(15):
        tags_db.get_or_create_tag(conn, f"tag{i:02d}")
    results = tags_db.autocomplete_tags(conn, "tag", limit=5)
    assert len(results) <= 5


def test_autocomplete_tags_usage_order(conn, asset_id):
    tags_db.add_asset_tag(conn, asset_id, "metal")
    tags_db.get_or_create_tag(conn, "metallic")
    results = tags_db.autocomplete_tags(conn, "met")
    # "metal" has usage_count=1, "metallic" has 0 — metal should come first
    assert results[0]["name"] == "metal"


# ---------------------------------------------------------------------------
# add_asset_tag / remove_asset_tag / get_asset_tags
# ---------------------------------------------------------------------------


def test_add_asset_tag(conn, asset_id):
    tags_db.add_asset_tag(conn, asset_id, "metal")
    assert "metal" in tags_db.get_asset_tags(conn, asset_id)


def test_add_asset_tag_normalizes(conn, asset_id):
    tags_db.add_asset_tag(conn, asset_id, "  Metal  ")
    assert "metal" in tags_db.get_asset_tags(conn, asset_id)


def test_add_asset_tag_is_idempotent(conn, asset_id):
    tags_db.add_asset_tag(conn, asset_id, "metal")
    tags_db.add_asset_tag(conn, asset_id, "metal")  # must not raise
    assert tags_db.get_asset_tags(conn, asset_id).count("metal") == 1


def test_add_asset_tag_discards_empty(conn, asset_id):
    tags_db.add_asset_tag(conn, asset_id, "   ")  # must not raise
    assert tags_db.get_asset_tags(conn, asset_id) == []


def test_remove_asset_tag(conn, asset_id):
    tags_db.add_asset_tag(conn, asset_id, "metal")
    tag_id = tags_db.get_tag_by_name(conn, "metal")["id"]
    tags_db.remove_asset_tag(conn, asset_id, tag_id)
    assert "metal" not in tags_db.get_asset_tags(conn, asset_id)


def test_remove_nonexistent_tag_is_noop(conn, asset_id):
    tags_db.remove_asset_tag(conn, asset_id, "00000000-0000-4000-8000-000000000099")


def test_get_asset_tags_empty(conn, asset_id):
    assert tags_db.get_asset_tags(conn, asset_id) == []


# ---------------------------------------------------------------------------
# list_assets_for_tag
# ---------------------------------------------------------------------------


def test_list_assets_for_tag(conn, asset_id):
    tags_db.add_asset_tag(conn, asset_id, "metal")
    rows = tags_db.list_assets_for_tag(conn, "metal")
    assert len(rows) == 1
    assert rows[0]["id"] == asset_id


def test_list_assets_for_tag_normalizes(conn, asset_id):
    tags_db.add_asset_tag(conn, asset_id, "metal")
    rows = tags_db.list_assets_for_tag(conn, "  Metal  ")
    assert len(rows) == 1


# ---------------------------------------------------------------------------
# list_tags_for_asset_ids
# ---------------------------------------------------------------------------


def test_list_tags_for_asset_ids_returns_tags(conn, asset_id):
    tags_db.add_asset_tag(conn, asset_id, "metal")
    tags_db.add_asset_tag(conn, asset_id, "pbr")
    rows = tags_db.list_tags_for_asset_ids(conn, [asset_id])
    names = {r["name"] for r in rows}
    assert names == {"metal", "pbr"}


def test_list_tags_for_asset_ids_deduplicates_across_assets(conn, asset_id):
    asset2 = "bbbbbbbb-0000-4000-8000-000000000002"
    assets_db.insert_asset(
        conn, id=asset2, name="Glass", type="MATERIAL", blend_path="glass.blend"
    )
    tags_db.add_asset_tag(conn, asset_id, "metal")
    tags_db.add_asset_tag(conn, asset2, "metal")  # same tag on both assets
    tags_db.add_asset_tag(conn, asset2, "pbr")
    rows = tags_db.list_tags_for_asset_ids(conn, [asset_id, asset2])
    names = {r["name"] for r in rows}
    assert names == {"metal", "pbr"}
    assert len(rows) == 2  # no duplicates


def test_list_tags_for_asset_ids_empty_input(conn):
    rows = tags_db.list_tags_for_asset_ids(conn, [])
    assert rows == []


def test_list_tags_for_asset_ids_sorted_by_name(conn, asset_id):
    tags_db.add_asset_tag(conn, asset_id, "zinc")
    tags_db.add_asset_tag(conn, asset_id, "aluminium")
    tags_db.add_asset_tag(conn, asset_id, "iron")
    rows = tags_db.list_tags_for_asset_ids(conn, [asset_id])
    assert [r["name"] for r in rows] == ["aluminium", "iron", "zinc"]


# ---------------------------------------------------------------------------
# get_asset_tag_memberships
# ---------------------------------------------------------------------------


def test_get_asset_tag_memberships_returns_mapping(conn, asset_id):
    tags_db.add_asset_tag(conn, asset_id, "metal")
    tags_db.add_asset_tag(conn, asset_id, "pbr")
    result = tags_db.get_asset_tag_memberships(conn, [asset_id])
    assert asset_id in result
    tag_names = {
        tags_db.get_tag_by_id(conn, tid)["name"]
        for tid in result[asset_id]
    }
    assert tag_names == {"metal", "pbr"}


def test_get_asset_tag_memberships_empty_input(conn):
    assert tags_db.get_asset_tag_memberships(conn, []) == {}


def test_get_asset_tag_memberships_asset_without_tags_omitted(conn, asset_id):
    # asset_id has no tags → should not appear in result
    result = tags_db.get_asset_tag_memberships(conn, [asset_id])
    assert result == {}


def test_get_asset_tag_memberships_multiple_assets(conn, asset_id):
    asset2 = "bbbbbbbb-0000-4000-8000-000000000002"
    assets_db.insert_asset(
        conn, id=asset2, name="Glass", type="MATERIAL", blend_path="glass.blend"
    )
    tags_db.add_asset_tag(conn, asset_id, "metal")
    tags_db.add_asset_tag(conn, asset2, "pbr")
    result = tags_db.get_asset_tag_memberships(conn, [asset_id, asset2])
    assert asset_id in result
    assert asset2 in result
    assert len(result[asset_id]) == 1
    assert len(result[asset2]) == 1


# ---------------------------------------------------------------------------
# Cascade on asset delete
# ---------------------------------------------------------------------------


def test_delete_asset_cascades_to_asset_tags(conn, asset_id):
    tags_db.add_asset_tag(conn, asset_id, "metal")
    assets_db.delete_asset(conn, asset_id)
    rows = conn.execute(
        "SELECT * FROM asset_tags WHERE asset_id = ?", (asset_id,)
    ).fetchall()
    assert rows == []


# ---------------------------------------------------------------------------
# clear_asset_tags
# ---------------------------------------------------------------------------


def test_clear_asset_tags_removes_all_associations(conn, asset_id):
    tags_db.add_asset_tag(conn, asset_id, "metal")
    tags_db.add_asset_tag(conn, asset_id, "pbr")
    tags_db.clear_asset_tags(conn, asset_id)
    result = tags_db.get_asset_tags(conn, asset_id)
    assert result == []


def test_clear_asset_tags_leaves_tag_records_intact(conn, asset_id):
    tags_db.add_asset_tag(conn, asset_id, "metal")
    tags_db.clear_asset_tags(conn, asset_id)
    tag = tags_db.get_tag_by_name(conn, "metal")
    assert tag is not None


def test_clear_asset_tags_no_op_when_asset_has_no_tags(conn, asset_id):
    # Should not raise when there are no associations to remove.
    tags_db.clear_asset_tags(conn, asset_id)
    result = tags_db.get_asset_tags(conn, asset_id)
    assert result == []


def test_clear_asset_tags_does_not_affect_other_assets(conn, asset_id):
    asset2 = "bbbbbbbb-0000-4000-8000-000000000009"
    assets_db.insert_asset(
        conn, id=asset2, name="Glass", type="MATERIAL", blend_path="glass.blend"
    )
    tags_db.add_asset_tag(conn, asset_id, "metal")
    tags_db.add_asset_tag(conn, asset2, "metal")
    tags_db.clear_asset_tags(conn, asset_id)
    # The other asset should still be tagged.
    result = tags_db.get_asset_tags(conn, asset2)
    assert "metal" in result

