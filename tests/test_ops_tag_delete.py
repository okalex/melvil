"""Tests for ops/tag_delete.py — MELVIL_OT_tag_delete."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest

from melvil.db.connection import migrate
from melvil.db import assets as assets_db
from melvil.db import tags as tags_db

TAG_ID = "cccccccc-0000-4000-8000-000000000001"
ASSET_ID = "aaaaaaaa-0000-4000-8000-000000000001"


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.execute("PRAGMA foreign_keys = ON")
    c.row_factory = sqlite3.Row
    migrate(c)
    c.execute(
        "INSERT INTO tags (id, name) VALUES (?, ?)",
        (TAG_ID, "metal"),
    )
    c.commit()
    yield c
    c.close()


@pytest.fixture
def conn_with_asset(conn):
    assets_db.insert_asset(
        conn,
        id=ASSET_ID,
        name="Red Metal",
        type="MATERIAL",
        blend_path="red_metal.blend",
    )
    conn.execute(
        "INSERT INTO asset_tags (asset_id, tag_id) VALUES (?, ?)",
        (ASSET_ID, TAG_ID),
    )
    conn.commit()
    return conn


def _mock_open_db(conn):
    @contextmanager
    def _cm(_path):
        yield conn
    return _cm


def _make_op(tag_id=""):
    from melvil.ops.tag_delete import MELVIL_OT_tag_delete
    op = MELVIL_OT_tag_delete()
    op.tag_id = tag_id
    op._tag_name = ""
    op._usage_count = 0
    return op


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


def test_bl_idname():
    from melvil.ops.tag_delete import MELVIL_OT_tag_delete
    assert MELVIL_OT_tag_delete.bl_idname == "melvil.tag_delete"


def test_poll_always_true():
    from melvil.ops.tag_delete import MELVIL_OT_tag_delete
    assert MELVIL_OT_tag_delete.poll(MagicMock()) is True


# ---------------------------------------------------------------------------
# invoke()
# ---------------------------------------------------------------------------


class TestInvoke:
    def test_no_tag_id_returns_cancelled(self):
        op = _make_op(tag_id="")
        result = op.invoke(MagicMock(), MagicMock())
        assert result == {"CANCELLED"}

    def test_missing_tag_returns_cancelled(self, conn):
        op = _make_op(tag_id="does-not-exist")
        with patch("melvil.ops.tag_delete.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ops.tag_delete.open_db", _mock_open_db(conn)):
            result = op.invoke(MagicMock(), MagicMock())
        assert result == {"CANCELLED"}

    def test_populates_name_and_usage(self, conn_with_asset):
        op = _make_op(tag_id=TAG_ID)
        ctx = MagicMock()
        with patch("melvil.ops.tag_delete.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ops.tag_delete.open_db", _mock_open_db(conn_with_asset)):
            op.invoke(ctx, MagicMock())
        assert op._tag_name == "metal"
        assert op._usage_count == 1


# ---------------------------------------------------------------------------
# execute()
# ---------------------------------------------------------------------------


class TestExecute:
    def test_no_tag_id_returns_cancelled(self):
        op = _make_op(tag_id="")
        with patch("melvil.ops.tag_delete.resolve_db_path", return_value=":memory:"):
            result = op.execute(MagicMock())
        assert result == {"CANCELLED"}

    def test_deletes_tag(self, conn):
        op = _make_op(tag_id=TAG_ID)
        with patch("melvil.ops.tag_delete.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ops.tag_delete.open_db", _mock_open_db(conn)):
            result = op.execute(MagicMock())
        assert result == {"FINISHED"}
        assert tags_db.get_tag_by_id(conn, TAG_ID) is None

    def test_cascades_to_asset_tags(self, conn_with_asset):
        op = _make_op(tag_id=TAG_ID)
        with patch("melvil.ops.tag_delete.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ops.tag_delete.open_db", _mock_open_db(conn_with_asset)):
            op.execute(MagicMock())
        rows = conn_with_asset.execute(
            "SELECT * FROM asset_tags WHERE tag_id = ?", (TAG_ID,)
        ).fetchall()
        assert rows == []

    def test_library_not_configured_returns_cancelled(self):
        from melvil.core.library import LibraryNotConfiguredError
        op = _make_op(tag_id=TAG_ID)
        with patch("melvil.ops.tag_delete.resolve_db_path", side_effect=LibraryNotConfiguredError("x")):
            result = op.execute(MagicMock())
        assert result == {"CANCELLED"}
