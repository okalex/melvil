"""Tests for ops/asset_edit_tags.py — BLAMMO_OT_asset_edit_tags."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest

from blammo.db.connection import migrate
from blammo.db import assets as assets_db
from blammo.db import tags as tags_db


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


def _mock_open_db(conn):
    @contextmanager
    def _cm(_path):
        yield conn
    return _cm


def _make_op(asset_id="", asset_name="", tags=""):
    from blammo.ops.asset_edit_tags import BLAMMO_OT_asset_edit_tags

    op = BLAMMO_OT_asset_edit_tags()
    op.asset_id = asset_id
    op.asset_name = asset_name
    op.tags = tags
    op.report = MagicMock()
    return op


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


def test_bl_idname():
    from blammo.ops.asset_edit_tags import BLAMMO_OT_asset_edit_tags

    assert BLAMMO_OT_asset_edit_tags.bl_idname == "blammo.asset_edit_tags"


def test_bl_options_contains_internal():
    from blammo.ops.asset_edit_tags import BLAMMO_OT_asset_edit_tags

    assert "INTERNAL" in BLAMMO_OT_asset_edit_tags.bl_options


# ---------------------------------------------------------------------------
# poll()
# ---------------------------------------------------------------------------


def test_poll_always_true():
    from blammo.ops.asset_edit_tags import BLAMMO_OT_asset_edit_tags

    assert BLAMMO_OT_asset_edit_tags.poll(MagicMock()) is True


# ---------------------------------------------------------------------------
# invoke()
# ---------------------------------------------------------------------------


def test_invoke_pre_populates_tags_from_db(conn, asset_id):
    tags_db.add_asset_tag(conn, asset_id, "metal")
    tags_db.add_asset_tag(conn, asset_id, "pbr")
    conn.commit()

    op = _make_op(asset_id=asset_id)
    ctx = MagicMock()

    with patch("blammo.ops.asset_edit_tags.resolve_db_path", return_value=":memory:"), \
         patch("blammo.ops.asset_edit_tags.open_db", _mock_open_db(conn)):
        op.invoke(ctx, MagicMock())

    # Tags are comma-separated; both names must appear
    assert "metal" in op.tags
    assert "pbr" in op.tags


def test_invoke_empty_tags_when_asset_untagged(conn, asset_id):
    op = _make_op(asset_id=asset_id)
    ctx = MagicMock()

    with patch("blammo.ops.asset_edit_tags.resolve_db_path", return_value=":memory:"), \
         patch("blammo.ops.asset_edit_tags.open_db", _mock_open_db(conn)):
        op.invoke(ctx, MagicMock())

    assert op.tags == ""


def test_invoke_cancelled_when_no_asset_id():
    op = _make_op(asset_id="")
    result = op.invoke(MagicMock(), MagicMock())
    assert result == {"CANCELLED"}


def test_invoke_cancelled_on_library_not_configured():
    from blammo.core.library import LibraryNotConfiguredError

    op = _make_op(asset_id="some-id")
    with patch("blammo.ops.asset_edit_tags.resolve_db_path",
               side_effect=LibraryNotConfiguredError("not set")):
        result = op.invoke(MagicMock(), MagicMock())

    assert result == {"CANCELLED"}


# ---------------------------------------------------------------------------
# draw()
# ---------------------------------------------------------------------------


def test_draw_shows_asset_name_label():
    op = _make_op(asset_id="x", asset_name="Red Metal")
    layout = MagicMock()
    op.layout = layout
    op.draw(MagicMock())
    layout.label.assert_called_once_with(text="Red Metal")


def test_draw_shows_tags_prop():
    op = _make_op(asset_id="x", asset_name="")
    layout = MagicMock()
    op.layout = layout
    op.draw(MagicMock())
    layout.prop.assert_called_once_with(op, "tags", text="Tags")


def test_draw_omits_label_when_no_asset_name():
    op = _make_op(asset_id="x", asset_name="")
    layout = MagicMock()
    op.layout = layout
    op.draw(MagicMock())
    layout.label.assert_not_called()


# ---------------------------------------------------------------------------
# execute()
# ---------------------------------------------------------------------------


def test_execute_applies_tags_to_asset(conn, asset_id):
    op = _make_op(asset_id=asset_id, tags="metal, pbr")

    with patch("blammo.ops.asset_edit_tags.resolve_db_path", return_value=":memory:"), \
         patch("blammo.ops.asset_edit_tags.open_db", _mock_open_db(conn)):
        result = op.execute(MagicMock())

    assert result == {"FINISHED"}
    names = tags_db.get_asset_tags(conn, asset_id)
    assert "metal" in names
    assert "pbr" in names


def test_execute_replaces_existing_tags(conn, asset_id):
    tags_db.add_asset_tag(conn, asset_id, "old-tag")
    conn.commit()

    op = _make_op(asset_id=asset_id, tags="new-tag")
    with patch("blammo.ops.asset_edit_tags.resolve_db_path", return_value=":memory:"), \
         patch("blammo.ops.asset_edit_tags.open_db", _mock_open_db(conn)):
        op.execute(MagicMock())

    names = tags_db.get_asset_tags(conn, asset_id)
    assert "old-tag" not in names
    assert "new-tag" in names


def test_execute_removes_all_tags_when_field_empty(conn, asset_id):
    tags_db.add_asset_tag(conn, asset_id, "metal")
    conn.commit()

    op = _make_op(asset_id=asset_id, tags="")
    with patch("blammo.ops.asset_edit_tags.resolve_db_path", return_value=":memory:"), \
         patch("blammo.ops.asset_edit_tags.open_db", _mock_open_db(conn)):
        op.execute(MagicMock())

    names = tags_db.get_asset_tags(conn, asset_id)
    assert names == []


def test_execute_normalizes_tag_names(conn, asset_id):
    op = _make_op(asset_id=asset_id, tags="  Metal , PBR Material  ")
    with patch("blammo.ops.asset_edit_tags.resolve_db_path", return_value=":memory:"), \
         patch("blammo.ops.asset_edit_tags.open_db", _mock_open_db(conn)):
        op.execute(MagicMock())

    names = tags_db.get_asset_tags(conn, asset_id)
    assert "metal" in names
    assert "pbr material" in names


def test_execute_cancelled_when_no_asset_id():
    op = _make_op(asset_id="")
    result = op.execute(MagicMock())
    assert result == {"CANCELLED"}


def test_execute_cancelled_on_library_not_configured():
    from blammo.core.library import LibraryNotConfiguredError

    op = _make_op(asset_id="some-id", tags="metal")
    with patch("blammo.ops.asset_edit_tags.resolve_db_path",
               side_effect=LibraryNotConfiguredError("not set")):
        result = op.execute(MagicMock())

    assert result == {"CANCELLED"}
