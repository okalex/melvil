"""Tests for ops/tag_rename.py — BLAMMO_OT_tag_rename."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest

from blammo.db.connection import migrate
from blammo.db import tags as tags_db

TAG_ID = "cccccccc-0000-4000-8000-000000000001"


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


def _mock_open_db(conn):
    @contextmanager
    def _cm(_path):
        yield conn
    return _cm


def _make_op(tag_id="", name=""):
    from blammo.ops.tag_rename import BLAMMO_OT_tag_rename
    op = BLAMMO_OT_tag_rename()
    op.tag_id = tag_id
    op.name = name
    return op


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


def test_bl_idname():
    from blammo.ops.tag_rename import BLAMMO_OT_tag_rename
    assert BLAMMO_OT_tag_rename.bl_idname == "blammo.tag_rename"


def test_poll_always_true():
    from blammo.ops.tag_rename import BLAMMO_OT_tag_rename
    assert BLAMMO_OT_tag_rename.poll(MagicMock()) is True


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
        with patch("blammo.ops.tag_rename.resolve_db_path", return_value=":memory:"), \
             patch("blammo.ops.tag_rename.open_db", _mock_open_db(conn)):
            result = op.invoke(MagicMock(), MagicMock())
        assert result == {"CANCELLED"}

    def test_populates_name_and_shows_dialog(self, conn):
        op = _make_op(tag_id=TAG_ID)
        ctx = MagicMock()
        with patch("blammo.ops.tag_rename.resolve_db_path", return_value=":memory:"), \
             patch("blammo.ops.tag_rename.open_db", _mock_open_db(conn)):
            op.invoke(ctx, MagicMock())
        assert op.name == "metal"


# ---------------------------------------------------------------------------
# execute()
# ---------------------------------------------------------------------------


class TestExecute:
    def test_no_tag_id_returns_cancelled(self):
        op = _make_op(tag_id="", name="steel")
        with patch("blammo.ops.tag_rename.resolve_db_path", return_value=":memory:"):
            result = op.execute(MagicMock())
        assert result == {"CANCELLED"}

    def test_renames_tag(self, conn):
        op = _make_op(tag_id=TAG_ID, name="steel")
        with patch("blammo.ops.tag_rename.resolve_db_path", return_value=":memory:"), \
             patch("blammo.ops.tag_rename.open_db", _mock_open_db(conn)):
            result = op.execute(MagicMock())
        assert result == {"FINISHED"}
        assert tags_db.get_tag_by_id(conn, TAG_ID)["name"] == "steel"

    def test_normalizes_new_name(self, conn):
        op = _make_op(tag_id=TAG_ID, name="  STEEL  ")
        with patch("blammo.ops.tag_rename.resolve_db_path", return_value=":memory:"), \
             patch("blammo.ops.tag_rename.open_db", _mock_open_db(conn)):
            op.execute(MagicMock())
        assert tags_db.get_tag_by_id(conn, TAG_ID)["name"] == "steel"

    def test_empty_name_returns_cancelled(self, conn):
        op = _make_op(tag_id=TAG_ID, name="   ")
        with patch("blammo.ops.tag_rename.resolve_db_path", return_value=":memory:"), \
             patch("blammo.ops.tag_rename.open_db", _mock_open_db(conn)):
            result = op.execute(MagicMock())
        assert result == {"CANCELLED"}

    def test_conflict_returns_cancelled(self, conn):
        other_id = "dddddddd-0000-4000-8000-000000000001"
        conn.execute("INSERT INTO tags (id, name) VALUES (?, ?)", (other_id, "shiny"))
        conn.commit()
        op = _make_op(tag_id=TAG_ID, name="shiny")
        with patch("blammo.ops.tag_rename.resolve_db_path", return_value=":memory:"), \
             patch("blammo.ops.tag_rename.open_db", _mock_open_db(conn)):
            result = op.execute(MagicMock())
        assert result == {"CANCELLED"}

    def test_library_not_configured_returns_cancelled(self):
        from blammo.core.library import LibraryNotConfiguredError
        op = _make_op(tag_id=TAG_ID, name="steel")
        with patch("blammo.ops.tag_rename.resolve_db_path", side_effect=LibraryNotConfiguredError("x")):
            result = op.execute(MagicMock())
        assert result == {"CANCELLED"}
