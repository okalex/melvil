"""Tests for ops/tag_create.py — MELVIL_OT_tag_create."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest

from melvil.db.connection import migrate
from melvil.db import tags as tags_db


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.execute("PRAGMA foreign_keys = ON")
    c.row_factory = sqlite3.Row
    migrate(c)
    yield c
    c.close()


def _mock_open_db(conn):
    @contextmanager
    def _cm(_path):
        yield conn
    return _cm


def _make_op(names=""):
    from melvil.ops.tag_create import MELVIL_OT_tag_create

    op = MELVIL_OT_tag_create()
    op.names = names
    return op


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


def test_bl_idname():
    from melvil.ops.tag_create import MELVIL_OT_tag_create

    assert MELVIL_OT_tag_create.bl_idname == "melvil.tag_create"


def test_bl_label():
    from melvil.ops.tag_create import MELVIL_OT_tag_create

    assert "Tag" in MELVIL_OT_tag_create.bl_label


# ---------------------------------------------------------------------------
# poll()
# ---------------------------------------------------------------------------


def test_poll_always_returns_true():
    from melvil.ops.tag_create import MELVIL_OT_tag_create

    assert MELVIL_OT_tag_create.poll(MagicMock()) is True


# ---------------------------------------------------------------------------
# invoke()
# ---------------------------------------------------------------------------


class TestInvoke:
    def test_invoke_shows_props_dialog(self):
        op = _make_op()
        ctx = MagicMock()
        ctx.window_manager.invoke_props_dialog.return_value = {"RUNNING_MODAL"}
        result = op.invoke(ctx, MagicMock())
        ctx.window_manager.invoke_props_dialog.assert_called_once_with(op)
        assert result == {"RUNNING_MODAL"}

    def test_invoke_resets_names_to_empty(self):
        op = _make_op(names="leftover")
        ctx = MagicMock()
        op.invoke(ctx, MagicMock())
        assert op.names == ""


# ---------------------------------------------------------------------------
# execute()
# ---------------------------------------------------------------------------


class TestExecute:
    def test_creates_new_tag(self, conn):
        op = _make_op(names="metal")

        with patch("melvil.ops.tag_create.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ops.tag_create.open_db", _mock_open_db(conn)):
            result = op.execute(MagicMock())

        assert result == {"FINISHED"}
        row = tags_db.get_tag_by_name(conn, "metal")
        assert row is not None

    def test_creates_multiple_tags_from_comma_separated_input(self, conn):
        op = _make_op(names="metal, plastic, wood")

        with patch("melvil.ops.tag_create.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ops.tag_create.open_db", _mock_open_db(conn)):
            result = op.execute(MagicMock())

        assert result == {"FINISHED"}
        assert tags_db.get_tag_by_name(conn, "metal") is not None
        assert tags_db.get_tag_by_name(conn, "plastic") is not None
        assert tags_db.get_tag_by_name(conn, "wood") is not None
        assert len(tags_db.list_tags(conn)) == 3

    def test_normalizes_tag_name(self, conn):
        op = _make_op(names="  Hard Surface  ")

        with patch("melvil.ops.tag_create.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ops.tag_create.open_db", _mock_open_db(conn)):
            op.execute(MagicMock())

        row = tags_db.get_tag_by_name(conn, "hard surface")
        assert row is not None

    def test_empty_name_returns_cancelled(self, conn):
        op = _make_op(names="   ")

        with patch("melvil.ops.tag_create.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ops.tag_create.open_db", _mock_open_db(conn)):
            result = op.execute(MagicMock())

        assert result == {"CANCELLED"}
        assert tags_db.list_tags(conn) == []

    def test_existing_tag_name_is_idempotent(self, conn):
        tags_db.get_or_create_tag(conn, "metal")
        conn.commit()
        op = _make_op(names="metal")

        with patch("melvil.ops.tag_create.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ops.tag_create.open_db", _mock_open_db(conn)):
            result = op.execute(MagicMock())

        assert result == {"FINISHED"}
        assert len(tags_db.list_tags(conn)) == 1

    def test_returns_cancelled_on_library_not_configured(self):
        from melvil.core.library import LibraryNotConfiguredError

        op = _make_op(names="metal")
        with patch("melvil.ops.tag_create.resolve_db_path",
                   side_effect=LibraryNotConfiguredError("not set")):
            result = op.execute(MagicMock())

        assert result == {"CANCELLED"}

    def test_returns_cancelled_on_db_error(self):
        op = _make_op(names="metal")
        with patch("melvil.ops.tag_create.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ops.tag_create.open_db", side_effect=Exception("boom")):
            result = op.execute(MagicMock())

        assert result == {"CANCELLED"}
