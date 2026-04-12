"""Tests for ops/asset_rename.py — MELVIL_OT_asset_name_confirm."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest

from melvil.db.connection import migrate
from melvil.db import assets as assets_db

_ASSET_ID = "aaaaaaaa-0000-4000-8000-000000000001"


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.execute("PRAGMA foreign_keys = ON")
    c.row_factory = sqlite3.Row
    migrate(c)
    assets_db.insert_asset(
        c,
        id=_ASSET_ID,
        name="Old Name",
        type="MESH",
        blend_path="meshes/old_name.blend",
    )
    yield c
    c.close()


def _mock_open_db(conn):
    @contextmanager
    def _cm(_path):
        yield conn
    return _cm


def _make_confirm_op(asset_id=""):
    from melvil.ops.asset_rename import MELVIL_OT_asset_name_confirm

    op = MELVIL_OT_asset_name_confirm()
    op.asset_id = asset_id
    return op


def _make_confirm_ctx(pending_name=""):
    ctx = MagicMock()
    ctx.window_manager.melvil_pending_name = pending_name
    return ctx


# ---------------------------------------------------------------------------
# MELVIL_OT_asset_name_confirm — metadata
# ---------------------------------------------------------------------------


class TestAssetNameConfirmMetadata:
    def test_bl_idname(self):
        from melvil.ops.asset_rename import MELVIL_OT_asset_name_confirm

        assert MELVIL_OT_asset_name_confirm.bl_idname == "melvil.asset_name_confirm"

    def test_bl_label(self):
        from melvil.ops.asset_rename import MELVIL_OT_asset_name_confirm

        assert MELVIL_OT_asset_name_confirm.bl_label == "Confirm Name"

    def test_poll_always_true(self):
        from melvil.ops.asset_rename import MELVIL_OT_asset_name_confirm

        assert MELVIL_OT_asset_name_confirm.poll(MagicMock()) is True


# ---------------------------------------------------------------------------
# MELVIL_OT_asset_name_confirm — execute()
# ---------------------------------------------------------------------------


class TestAssetNameConfirmExecute:
    def test_empty_asset_id_returns_cancelled(self):
        op = _make_confirm_op(asset_id="")
        assert op.execute(_make_confirm_ctx(pending_name="New Name")) == {"CANCELLED"}

    def test_empty_pending_name_returns_cancelled(self):
        op = _make_confirm_op(asset_id=_ASSET_ID)
        assert op.execute(_make_confirm_ctx(pending_name="")) == {"CANCELLED"}

    def test_whitespace_pending_name_returns_cancelled(self):
        op = _make_confirm_op(asset_id=_ASSET_ID)
        assert op.execute(_make_confirm_ctx(pending_name="   ")) == {"CANCELLED"}

    def test_renames_asset_in_db(self, conn):
        op = _make_confirm_op(asset_id=_ASSET_ID)
        ctx = _make_confirm_ctx(pending_name="Confirmed Name")
        with patch("melvil.ops.asset_rename.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ops.asset_rename.open_db", _mock_open_db(conn)):
            result = op.execute(ctx)
        assert result == {"FINISHED"}
        row = assets_db.get_asset(conn, _ASSET_ID)
        assert row["name"] == "Confirmed Name"

    def test_strips_whitespace_from_pending_name(self, conn):
        op = _make_confirm_op(asset_id=_ASSET_ID)
        ctx = _make_confirm_ctx(pending_name="  Trimmed  ")
        with patch("melvil.ops.asset_rename.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ops.asset_rename.open_db", _mock_open_db(conn)):
            op.execute(ctx)
        row = assets_db.get_asset(conn, _ASSET_ID)
        assert row["name"] == "Trimmed"

    def test_resets_pending_name_asset_id_on_success(self, conn):
        op = _make_confirm_op(asset_id=_ASSET_ID)
        ctx = _make_confirm_ctx(pending_name="New Name")
        ctx.window_manager.melvil_pending_name_asset_id = _ASSET_ID
        with patch("melvil.ops.asset_rename.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ops.asset_rename.open_db", _mock_open_db(conn)):
            op.execute(ctx)
        assert ctx.window_manager.melvil_pending_name_asset_id == ""

    def test_unknown_asset_returns_cancelled(self, conn):
        op = _make_confirm_op(asset_id="unknown-id")
        ctx = _make_confirm_ctx(pending_name="New Name")
        with patch("melvil.ops.asset_rename.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ops.asset_rename.open_db", _mock_open_db(conn)):
            result = op.execute(ctx)
        assert result == {"CANCELLED"}

    def test_db_error_returns_cancelled(self):
        op = _make_confirm_op(asset_id=_ASSET_ID)
        ctx = _make_confirm_ctx(pending_name="New Name")
        with patch("melvil.ops.asset_rename.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ops.asset_rename.open_db", side_effect=Exception("boom")):
            result = op.execute(ctx)
        assert result == {"CANCELLED"}

