"""Tests for ops/tag_add.py — BLAMMO_OT_tag_add."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest

from blammo.db.connection import migrate
from blammo.db import assets as assets_db
from blammo.db import tags as tags_db
from blammo.db.kits import DEFAULT_KIT_ID

ASSET_ID = "aaaaaaaa-0000-4000-8000-000000000001"


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.execute("PRAGMA foreign_keys = ON")
    c.row_factory = sqlite3.Row
    migrate(c)
    assets_db.insert_asset(
        c,
        id=ASSET_ID,
        name="Red Metal",
        type="MATERIAL",
        blend_path="red_metal.blend",
    )
    yield c
    c.close()


def _mock_open_db(conn):
    @contextmanager
    def _cm(_path):
        yield conn
    return _cm


def _make_op(asset_id="", tags=""):
    from blammo.ops.tag_add import BLAMMO_OT_tag_add
    op = BLAMMO_OT_tag_add()
    op.asset_id = asset_id
    op.tags = tags
    return op


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


def test_bl_idname():
    from blammo.ops.tag_add import BLAMMO_OT_tag_add
    assert BLAMMO_OT_tag_add.bl_idname == "blammo.tag_add"


def test_poll_always_true():
    from blammo.ops.tag_add import BLAMMO_OT_tag_add
    assert BLAMMO_OT_tag_add.poll(MagicMock()) is True


# ---------------------------------------------------------------------------
# execute()
# ---------------------------------------------------------------------------


class TestExecute:
    def test_no_asset_id_returns_cancelled(self):
        op = _make_op(asset_id="", tags="metal")
        with patch("blammo.ops.tag_add.resolve_db_path", return_value=":memory:"):
            result = op.execute(MagicMock())
        assert result == {"CANCELLED"}

    def test_empty_tags_returns_cancelled(self):
        op = _make_op(asset_id=ASSET_ID, tags="   ,  , ")
        with patch("blammo.ops.tag_add.resolve_db_path", return_value=":memory:"):
            result = op.execute(MagicMock())
        assert result == {"CANCELLED"}

    def test_adds_single_tag(self, conn):
        op = _make_op(asset_id=ASSET_ID, tags="metal")
        with patch("blammo.ops.tag_add.resolve_db_path", return_value=":memory:"), \
             patch("blammo.ops.tag_add.open_db", _mock_open_db(conn)):
            result = op.execute(MagicMock())
        assert result == {"FINISHED"}
        assert "metal" in tags_db.get_asset_tags(conn, ASSET_ID)

    def test_adds_multiple_tags(self, conn):
        op = _make_op(asset_id=ASSET_ID, tags="metal, shiny, pbr")
        with patch("blammo.ops.tag_add.resolve_db_path", return_value=":memory:"), \
             patch("blammo.ops.tag_add.open_db", _mock_open_db(conn)):
            result = op.execute(MagicMock())
        assert result == {"FINISHED"}
        applied = tags_db.get_asset_tags(conn, ASSET_ID)
        assert "metal" in applied
        assert "shiny" in applied
        assert "pbr" in applied

    def test_normalizes_tags(self, conn):
        op = _make_op(asset_id=ASSET_ID, tags="  Metal  , PBR Material")
        with patch("blammo.ops.tag_add.resolve_db_path", return_value=":memory:"), \
             patch("blammo.ops.tag_add.open_db", _mock_open_db(conn)):
            op.execute(MagicMock())
        applied = tags_db.get_asset_tags(conn, ASSET_ID)
        assert "metal" in applied
        assert "pbr material" in applied

    def test_idempotent(self, conn):
        op = _make_op(asset_id=ASSET_ID, tags="metal")
        ctx = MagicMock()
        with patch("blammo.ops.tag_add.resolve_db_path", return_value=":memory:"), \
             patch("blammo.ops.tag_add.open_db", _mock_open_db(conn)):
            op.execute(ctx)
            op.execute(ctx)  # second call must not raise
        assert tags_db.get_asset_tags(conn, ASSET_ID).count("metal") == 1

    def test_library_not_configured_returns_cancelled(self):
        from blammo.core.library import LibraryNotConfiguredError
        op = _make_op(asset_id=ASSET_ID, tags="metal")
        with patch("blammo.ops.tag_add.resolve_db_path", side_effect=LibraryNotConfiguredError("x")):
            result = op.execute(MagicMock())
        assert result == {"CANCELLED"}
