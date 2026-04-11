"""Tests for ops/kit_create.py — MELVIL_OT_kit_create."""

from __future__ import annotations

import sqlite3
from unittest.mock import MagicMock, patch

import pytest

from melvil.db.connection import migrate
from melvil.db import kits as kits_db
from melvil.db.kits import DEFAULT_KIT_ID


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.execute("PRAGMA foreign_keys = ON")
    c.row_factory = sqlite3.Row
    migrate(c)
    yield c
    c.close()


def _make_op():
    from melvil.ops.kit_create import MELVIL_OT_kit_create

    op = MELVIL_OT_kit_create()
    op.name = ""
    op.description = ""
    return op


def _make_ctx():
    return MagicMock()


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


def test_bl_idname():
    from melvil.ops.kit_create import MELVIL_OT_kit_create

    assert MELVIL_OT_kit_create.bl_idname == "melvil.kit_create"


def test_bl_label():
    from melvil.ops.kit_create import MELVIL_OT_kit_create

    assert MELVIL_OT_kit_create.bl_label == "New Kit"


# ---------------------------------------------------------------------------
# poll()
# ---------------------------------------------------------------------------


def test_poll_always_true():
    from melvil.ops.kit_create import MELVIL_OT_kit_create

    assert MELVIL_OT_kit_create.poll(MagicMock()) is True


# ---------------------------------------------------------------------------
# invoke()
# ---------------------------------------------------------------------------


def test_invoke_resets_name_and_calls_dialog():
    op = _make_op()
    op.name = "Old Name"
    op.description = "Old Desc"
    ctx = _make_ctx()

    op.invoke(ctx, MagicMock())

    assert op.name == ""
    assert op.description == ""
    ctx.window_manager.invoke_props_dialog.assert_called_once_with(op)


def test_invoke_returns_dialog_result():
    op = _make_op()
    ctx = _make_ctx()
    ctx.window_manager.invoke_props_dialog.return_value = {"RUNNING_MODAL"}

    result = op.invoke(ctx, MagicMock())

    assert result == {"RUNNING_MODAL"}


# ---------------------------------------------------------------------------
# execute() — validation
# ---------------------------------------------------------------------------


def test_execute_empty_name_returns_cancelled():
    op = _make_op()
    op.name = "   "

    with patch("melvil.ops.kit_create.open_db"):
        result = op.execute(_make_ctx())

    assert result == {"CANCELLED"}


def test_execute_duplicate_name_returns_cancelled(conn):
    op = _make_op()
    op.name = "General"  # already exists after migration

    with patch("melvil.ops.kit_create.open_db") as mock_open, \
         patch("melvil.ops.kit_create.resolve_db_path"):
        mock_open.return_value.__enter__ = lambda s: conn
        mock_open.return_value.__exit__ = MagicMock(return_value=False)
        result = op.execute(_make_ctx())

    assert result == {"CANCELLED"}


def test_execute_duplicate_name_case_insensitive(conn):
    op = _make_op()
    op.name = "general"  # "General" exists already

    with patch("melvil.ops.kit_create.open_db") as mock_open, \
         patch("melvil.ops.kit_create.resolve_db_path"):
        mock_open.return_value.__enter__ = lambda s: conn
        mock_open.return_value.__exit__ = MagicMock(return_value=False)
        result = op.execute(_make_ctx())

    assert result == {"CANCELLED"}


# ---------------------------------------------------------------------------
# execute() — success
# ---------------------------------------------------------------------------


def test_execute_creates_kit(conn):
    op = _make_op()
    op.name = "Campaign Assets"
    op.description = "Assets for the summer campaign"

    with patch("melvil.ops.kit_create.open_db") as mock_open, \
         patch("melvil.ops.kit_create.resolve_db_path"):
        mock_open.return_value.__enter__ = lambda s: conn
        mock_open.return_value.__exit__ = MagicMock(return_value=False)
        result = op.execute(_make_ctx())

    assert result == {"FINISHED"}
    row = kits_db.get_kit_by_name(conn, "Campaign Assets")
    assert row is not None
    assert row["description"] == "Assets for the summer campaign"


def test_execute_strips_name_whitespace(conn):
    op = _make_op()
    op.name = "  Game Project  "

    with patch("melvil.ops.kit_create.open_db") as mock_open, \
         patch("melvil.ops.kit_create.resolve_db_path"):
        mock_open.return_value.__enter__ = lambda s: conn
        mock_open.return_value.__exit__ = MagicMock(return_value=False)
        op.execute(_make_ctx())

    assert kits_db.get_kit_by_name(conn, "Game Project") is not None


def test_execute_empty_description_stored_as_none(conn):
    op = _make_op()
    op.name = "New Kit"
    op.description = "   "  # whitespace-only → None

    with patch("melvil.ops.kit_create.open_db") as mock_open, \
         patch("melvil.ops.kit_create.resolve_db_path"):
        mock_open.return_value.__enter__ = lambda s: conn
        mock_open.return_value.__exit__ = MagicMock(return_value=False)
        op.execute(_make_ctx())

    row = kits_db.get_kit_by_name(conn, "New Kit")
    assert row["description"] is None


def test_execute_library_not_configured_returns_cancelled():
    from melvil.core.library import LibraryNotConfiguredError

    op = _make_op()
    op.name = "Some Kit"

    with patch("melvil.ops.kit_create.resolve_db_path", side_effect=LibraryNotConfiguredError("not configured")):
        result = op.execute(_make_ctx())

    assert result == {"CANCELLED"}
