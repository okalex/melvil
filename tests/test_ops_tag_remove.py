"""Tests for ops/tag_remove.py — MELVIL_OT_tag_remove."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest

from melvil.db.connection import migrate
from melvil.db import assets as assets_db
from melvil.db import tags as tags_db

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


def _make_op(asset_id="", tag_id=""):
    from melvil.ops.tag_remove import MELVIL_OT_tag_remove
    op = MELVIL_OT_tag_remove()
    op.asset_id = asset_id
    op.tag_id = tag_id
    return op


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


def test_bl_idname():
    from melvil.ops.tag_remove import MELVIL_OT_tag_remove
    assert MELVIL_OT_tag_remove.bl_idname == "melvil.tag_remove"


def test_poll_always_true():
    from melvil.ops.tag_remove import MELVIL_OT_tag_remove
    assert MELVIL_OT_tag_remove.poll(MagicMock()) is True


# ---------------------------------------------------------------------------
# execute()
# ---------------------------------------------------------------------------


class TestExecute:
    def test_no_asset_id_returns_cancelled(self):
        op = _make_op(asset_id="", tag_id="some-uuid")
        with patch("melvil.ops.tag_remove.resolve_db_path", return_value=":memory:"):
            result = op.execute(MagicMock())
        assert result == {"CANCELLED"}

    def test_no_tag_id_returns_cancelled(self):
        op = _make_op(asset_id=ASSET_ID, tag_id="")
        with patch("melvil.ops.tag_remove.resolve_db_path", return_value=":memory:"):
            result = op.execute(MagicMock())
        assert result == {"CANCELLED"}

    def test_removes_tag(self, conn):
        tags_db.add_asset_tag(conn, ASSET_ID, "metal")
        tag_id = tags_db.get_tag_by_name(conn, "metal")["id"]

        op = _make_op(asset_id=ASSET_ID, tag_id=tag_id)
        with patch("melvil.ops.tag_remove.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ops.tag_remove.open_db", _mock_open_db(conn)):
            result = op.execute(MagicMock())

        assert result == {"FINISHED"}
        assert "metal" not in tags_db.get_asset_tags(conn, ASSET_ID)

    def test_nonexistent_association_is_noop(self, conn):
        fake_tag_id = "00000000-0000-4000-8000-000000000099"
        op = _make_op(asset_id=ASSET_ID, tag_id=fake_tag_id)
        with patch("melvil.ops.tag_remove.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ops.tag_remove.open_db", _mock_open_db(conn)):
            result = op.execute(MagicMock())
        assert result == {"FINISHED"}

    def test_library_not_configured_returns_cancelled(self):
        from melvil.core.library import LibraryNotConfiguredError
        op = _make_op(asset_id=ASSET_ID, tag_id="some-uuid")
        with patch("melvil.ops.tag_remove.resolve_db_path", side_effect=LibraryNotConfiguredError("x")):
            result = op.execute(MagicMock())
        assert result == {"CANCELLED"}
