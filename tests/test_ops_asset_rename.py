"""Tests for ops/asset_rename.py — MELVIL_OT_asset_rename."""

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


def _make_op(asset_id="", name=""):
    from melvil.ops.asset_rename import MELVIL_OT_asset_rename

    op = MELVIL_OT_asset_rename()
    op.asset_id = asset_id
    op.name = name
    return op


def _make_ctx():
    return MagicMock()


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


def test_bl_idname():
    from melvil.ops.asset_rename import MELVIL_OT_asset_rename

    assert MELVIL_OT_asset_rename.bl_idname == "melvil.asset_rename"


def test_bl_label():
    from melvil.ops.asset_rename import MELVIL_OT_asset_rename

    assert MELVIL_OT_asset_rename.bl_label == "Rename Asset"


def test_poll_always_true():
    from melvil.ops.asset_rename import MELVIL_OT_asset_rename

    assert MELVIL_OT_asset_rename.poll(MagicMock()) is True


# ---------------------------------------------------------------------------
# invoke()
# ---------------------------------------------------------------------------


def test_invoke_empty_asset_id_returns_cancelled():
    op = _make_op(asset_id="")
    result = op.invoke(_make_ctx(), MagicMock())
    assert result == {"CANCELLED"}


def test_invoke_unknown_asset_id_returns_cancelled(conn):
    op = _make_op(asset_id="unknown-id")
    with patch("melvil.ops.asset_rename.resolve_db_path", return_value=":memory:"), \
         patch("melvil.ops.asset_rename.open_db", _mock_open_db(conn)):
        result = op.invoke(_make_ctx(), MagicMock())
    assert result == {"CANCELLED"}


def test_invoke_prefills_name_from_db(conn):
    op = _make_op(asset_id=_ASSET_ID)
    ctx = _make_ctx()
    with patch("melvil.ops.asset_rename.resolve_db_path", return_value=":memory:"), \
         patch("melvil.ops.asset_rename.open_db", _mock_open_db(conn)):
        op.invoke(ctx, MagicMock())
    assert op.name == "Old Name"


# ---------------------------------------------------------------------------
# execute()
# ---------------------------------------------------------------------------


def test_execute_empty_asset_id_returns_cancelled():
    op = _make_op(asset_id="", name="New Name")
    assert op.execute(_make_ctx()) == {"CANCELLED"}


def test_execute_empty_name_returns_cancelled():
    op = _make_op(asset_id=_ASSET_ID, name="")
    assert op.execute(_make_ctx()) == {"CANCELLED"}


def test_execute_whitespace_name_returns_cancelled():
    op = _make_op(asset_id=_ASSET_ID, name="   ")
    assert op.execute(_make_ctx()) == {"CANCELLED"}


def test_execute_renames_asset_in_db(conn):
    op = _make_op(asset_id=_ASSET_ID, name="New Name")
    with patch("melvil.ops.asset_rename.resolve_db_path", return_value=":memory:"), \
         patch("melvil.ops.asset_rename.open_db", _mock_open_db(conn)):
        result = op.execute(_make_ctx())
    assert result == {"FINISHED"}
    row = assets_db.get_asset(conn, _ASSET_ID)
    assert row["name"] == "New Name"


def test_execute_unknown_asset_returns_cancelled(conn):
    op = _make_op(asset_id="unknown-id", name="New Name")
    with patch("melvil.ops.asset_rename.resolve_db_path", return_value=":memory:"), \
         patch("melvil.ops.asset_rename.open_db", _mock_open_db(conn)):
        result = op.execute(_make_ctx())
    assert result == {"CANCELLED"}


def test_execute_strips_whitespace_from_name(conn):
    op = _make_op(asset_id=_ASSET_ID, name="  Trimmed Name  ")
    with patch("melvil.ops.asset_rename.resolve_db_path", return_value=":memory:"), \
         patch("melvil.ops.asset_rename.open_db", _mock_open_db(conn)):
        op.execute(_make_ctx())
    row = assets_db.get_asset(conn, _ASSET_ID)
    assert row["name"] == "Trimmed Name"


def test_execute_db_error_returns_cancelled(conn):
    op = _make_op(asset_id=_ASSET_ID, name="New Name")
    with patch("melvil.ops.asset_rename.resolve_db_path", return_value=":memory:"), \
         patch("melvil.ops.asset_rename.open_db", side_effect=Exception("boom")):
        result = op.execute(_make_ctx())
    assert result == {"CANCELLED"}
