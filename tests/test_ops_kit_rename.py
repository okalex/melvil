"""Tests for ops/kit_rename.py — MELVIL_OT_kit_rename."""

from __future__ import annotations

import sqlite3
from unittest.mock import MagicMock, patch

import pytest

from melvil.db.connection import migrate
from melvil.db import kits as kits_db
from melvil.db.kits import DEFAULT_KIT_ID

_KIT_B_ID = "bbbbbbbb-0000-4000-8000-000000000001"
_KIT_B_NAME = "Campaign Assets"


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.execute("PRAGMA foreign_keys = ON")
    c.row_factory = sqlite3.Row
    migrate(c)
    kits_db.insert_kit(c, id=_KIT_B_ID, name=_KIT_B_NAME)
    yield c
    c.close()


def _make_op(kit_id="", name=""):
    from melvil.ops.kit_rename import MELVIL_OT_kit_rename

    op = MELVIL_OT_kit_rename()
    op.kit_id = kit_id
    op.name = name
    return op


def _make_ctx():
    return MagicMock()


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


def test_bl_idname():
    from melvil.ops.kit_rename import MELVIL_OT_kit_rename

    assert MELVIL_OT_kit_rename.bl_idname == "melvil.kit_rename"


def test_bl_label():
    from melvil.ops.kit_rename import MELVIL_OT_kit_rename

    assert MELVIL_OT_kit_rename.bl_label == "Rename Kit"


# ---------------------------------------------------------------------------
# poll()
# ---------------------------------------------------------------------------


def test_poll_always_true():
    from melvil.ops.kit_rename import MELVIL_OT_kit_rename

    assert MELVIL_OT_kit_rename.poll(MagicMock()) is True


# ---------------------------------------------------------------------------
# invoke()
# ---------------------------------------------------------------------------


def test_invoke_no_kit_id_returns_cancelled():
    op = _make_op(kit_id="")
    result = op.invoke(_make_ctx(), MagicMock())
    assert result == {"CANCELLED"}


def test_invoke_populates_name_from_db(conn):
    op = _make_op(kit_id=_KIT_B_ID)

    with patch("melvil.ops.kit_rename.open_db") as mock_open, \
         patch("melvil.ops.kit_rename.resolve_db_path"):
        mock_open.return_value.__enter__ = lambda s: conn
        mock_open.return_value.__exit__ = MagicMock(return_value=False)
        op.invoke(_make_ctx(), MagicMock())

    assert op.name == _KIT_B_NAME


def test_invoke_unknown_kit_id_returns_cancelled(conn):
    op = _make_op(kit_id="nonexistent-uuid")

    with patch("melvil.ops.kit_rename.open_db") as mock_open, \
         patch("melvil.ops.kit_rename.resolve_db_path"):
        mock_open.return_value.__enter__ = lambda s: conn
        mock_open.return_value.__exit__ = MagicMock(return_value=False)
        result = op.invoke(_make_ctx(), MagicMock())

    assert result == {"CANCELLED"}


def test_invoke_calls_dialog(conn):
    op = _make_op(kit_id=_KIT_B_ID)
    ctx = _make_ctx()

    with patch("melvil.ops.kit_rename.open_db") as mock_open, \
         patch("melvil.ops.kit_rename.resolve_db_path"):
        mock_open.return_value.__enter__ = lambda s: conn
        mock_open.return_value.__exit__ = MagicMock(return_value=False)
        op.invoke(ctx, MagicMock())

    ctx.window_manager.invoke_props_dialog.assert_called_once_with(op)


# ---------------------------------------------------------------------------
# execute() — validation
# ---------------------------------------------------------------------------


def test_execute_empty_name_returns_cancelled(conn):
    op = _make_op(kit_id=_KIT_B_ID, name="  ")

    with patch("melvil.ops.kit_rename.open_db") as mock_open, \
         patch("melvil.ops.kit_rename.resolve_db_path"):
        mock_open.return_value.__enter__ = lambda s: conn
        mock_open.return_value.__exit__ = MagicMock(return_value=False)
        result = op.execute(_make_ctx())

    assert result == {"CANCELLED"}


def test_execute_duplicate_name_returns_cancelled(conn):
    op = _make_op(kit_id=_KIT_B_ID, name="General")  # General already exists

    with patch("melvil.ops.kit_rename.open_db") as mock_open, \
         patch("melvil.ops.kit_rename.resolve_db_path"):
        mock_open.return_value.__enter__ = lambda s: conn
        mock_open.return_value.__exit__ = MagicMock(return_value=False)
        result = op.execute(_make_ctx())

    assert result == {"CANCELLED"}


def test_execute_duplicate_case_insensitive(conn):
    op = _make_op(kit_id=_KIT_B_ID, name="general")  # "General" already exists

    with patch("melvil.ops.kit_rename.open_db") as mock_open, \
         patch("melvil.ops.kit_rename.resolve_db_path"):
        mock_open.return_value.__enter__ = lambda s: conn
        mock_open.return_value.__exit__ = MagicMock(return_value=False)
        result = op.execute(_make_ctx())

    assert result == {"CANCELLED"}


def test_execute_rename_to_same_name_is_allowed(conn):
    """Renaming a kit to its own current name should succeed."""
    op = _make_op(kit_id=_KIT_B_ID, name=_KIT_B_NAME)

    with patch("melvil.ops.kit_rename.open_db") as mock_open, \
         patch("melvil.ops.kit_rename.resolve_db_path"):
        mock_open.return_value.__enter__ = lambda s: conn
        mock_open.return_value.__exit__ = MagicMock(return_value=False)
        result = op.execute(_make_ctx())

    assert result == {"FINISHED"}


# ---------------------------------------------------------------------------
# execute() — success
# ---------------------------------------------------------------------------


def test_execute_renames_kit(conn):
    op = _make_op(kit_id=_KIT_B_ID, name="Game Project")

    with patch("melvil.ops.kit_rename.open_db") as mock_open, \
         patch("melvil.ops.kit_rename.resolve_db_path"):
        mock_open.return_value.__enter__ = lambda s: conn
        mock_open.return_value.__exit__ = MagicMock(return_value=False)
        result = op.execute(_make_ctx())

    assert result == {"FINISHED"}
    row = kits_db.get_kit(conn, _KIT_B_ID)
    assert row["name"] == "Game Project"


def test_execute_strips_whitespace(conn):
    op = _make_op(kit_id=_KIT_B_ID, name="  Renamed  ")

    with patch("melvil.ops.kit_rename.open_db") as mock_open, \
         patch("melvil.ops.kit_rename.resolve_db_path"):
        mock_open.return_value.__enter__ = lambda s: conn
        mock_open.return_value.__exit__ = MagicMock(return_value=False)
        op.execute(_make_ctx())

    row = kits_db.get_kit(conn, _KIT_B_ID)
    assert row["name"] == "Renamed"


def test_execute_library_not_configured_returns_cancelled():
    from melvil.core.library import LibraryNotConfiguredError

    op = _make_op(kit_id=_KIT_B_ID, name="New Name")

    with patch("melvil.ops.kit_rename.resolve_db_path", side_effect=LibraryNotConfiguredError("not configured")):
        result = op.execute(_make_ctx())

    assert result == {"CANCELLED"}
