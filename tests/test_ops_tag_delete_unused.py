"""Tests for ops/tag_delete_unused.py — MELVIL_OT_tag_delete_unused."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest

from melvil.db.connection import migrate
from melvil.db import assets as assets_db
from melvil.db import tags as tags_db
from melvil.db.kits import DEFAULT_KIT_ID


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


def _make_op():
    from melvil.ops.tag_delete_unused import MELVIL_OT_tag_delete_unused

    return MELVIL_OT_tag_delete_unused()


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


def test_bl_idname():
    from melvil.ops.tag_delete_unused import MELVIL_OT_tag_delete_unused

    assert MELVIL_OT_tag_delete_unused.bl_idname == "melvil.tag_delete_unused"


def test_bl_label():
    from melvil.ops.tag_delete_unused import MELVIL_OT_tag_delete_unused

    assert "Delete" in MELVIL_OT_tag_delete_unused.bl_label


# ---------------------------------------------------------------------------
# poll()
# ---------------------------------------------------------------------------


def test_poll_always_returns_true():
    from melvil.ops.tag_delete_unused import MELVIL_OT_tag_delete_unused

    assert MELVIL_OT_tag_delete_unused.poll(MagicMock()) is True


# ---------------------------------------------------------------------------
# invoke()
# ---------------------------------------------------------------------------


class TestInvoke:
    def test_returns_cancelled_when_no_unused_tags(self, conn):
        asset_id = "aaaaaaaa-0000-4000-8000-000000000001"
        assets_db.insert_asset(
            conn, id=asset_id, name="Iron", type="MATERIAL", blend_path="iron.blend"
        )
        tags_db.add_asset_tag(conn, asset_id, "metal")
        conn.commit()

        op = _make_op()

        with patch("melvil.ops.tag_delete_unused.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ops.tag_delete_unused.open_db", _mock_open_db(conn)):
            result = op.invoke(MagicMock(), MagicMock())

        assert result == {"CANCELLED"}

    def test_returns_props_dialog_when_unused_tags_exist(self, conn):
        tags_db.get_or_create_tag(conn, "orphan")
        conn.commit()

        op = _make_op()
        ctx = MagicMock()

        with patch("melvil.ops.tag_delete_unused.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ops.tag_delete_unused.open_db", _mock_open_db(conn)):
            ctx.window_manager.invoke_props_dialog.return_value = {"RUNNING_MODAL"}
            result = op.invoke(ctx, MagicMock())

        assert result == {"RUNNING_MODAL"}

    def test_stores_unused_count(self, conn):
        tags_db.get_or_create_tag(conn, "orphan1")
        tags_db.get_or_create_tag(conn, "orphan2")
        conn.commit()

        op = _make_op()
        ctx = MagicMock()

        with patch("melvil.ops.tag_delete_unused.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ops.tag_delete_unused.open_db", _mock_open_db(conn)):
            op.invoke(ctx, MagicMock())

        assert op._unused_count == 2

    def test_returns_cancelled_on_db_error(self):
        from melvil.core.library import LibraryNotConfiguredError

        op = _make_op()
        with patch("melvil.ops.tag_delete_unused.resolve_db_path",
                   side_effect=LibraryNotConfiguredError("not set")):
            result = op.invoke(MagicMock(), MagicMock())

        assert result == {"CANCELLED"}


# ---------------------------------------------------------------------------
# draw()
# ---------------------------------------------------------------------------


class TestDraw:
    def test_draw_shows_count_in_label(self, conn):
        tags_db.get_or_create_tag(conn, "orphan1")
        tags_db.get_or_create_tag(conn, "orphan2")
        conn.commit()

        op = _make_op()
        ctx = MagicMock()

        with patch("melvil.ops.tag_delete_unused.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ops.tag_delete_unused.open_db", _mock_open_db(conn)):
            op.invoke(ctx, MagicMock())

        layout = MagicMock()
        op.layout = layout
        op.draw(ctx)

        all_label_texts = [c[1].get("text", "") or (c[0][0] if c[0] else "")
                           for c in layout.label.call_args_list]
        assert any("2" in t for t in all_label_texts)


# ---------------------------------------------------------------------------
# execute()
# ---------------------------------------------------------------------------


class TestExecute:
    def test_deletes_unused_tags(self, conn):
        asset_id = "aaaaaaaa-0000-4000-8000-000000000001"
        assets_db.insert_asset(
            conn, id=asset_id, name="Iron", type="MATERIAL", blend_path="iron.blend"
        )
        tags_db.add_asset_tag(conn, asset_id, "used")
        tags_db.get_or_create_tag(conn, "orphan1")
        tags_db.get_or_create_tag(conn, "orphan2")
        conn.commit()

        op = _make_op()

        with patch("melvil.ops.tag_delete_unused.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ops.tag_delete_unused.open_db", _mock_open_db(conn)):
            result = op.execute(MagicMock())

        assert result == {"FINISHED"}
        remaining = tags_db.list_tags(conn)
        assert len(remaining) == 1
        assert remaining[0]["name"] == "used"

    def test_preserves_used_tags(self, conn):
        asset_id = "aaaaaaaa-0000-4000-8000-000000000001"
        assets_db.insert_asset(
            conn, id=asset_id, name="Iron", type="MATERIAL", blend_path="iron.blend"
        )
        tags_db.add_asset_tag(conn, asset_id, "metal")
        tags_db.add_asset_tag(conn, asset_id, "hard")
        conn.commit()

        op = _make_op()

        with patch("melvil.ops.tag_delete_unused.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ops.tag_delete_unused.open_db", _mock_open_db(conn)):
            result = op.execute(MagicMock())

        assert result == {"FINISHED"}
        remaining = tags_db.list_tags(conn)
        assert len(remaining) == 2

    def test_no_unused_still_returns_finished(self, conn):
        asset_id = "aaaaaaaa-0000-4000-8000-000000000001"
        assets_db.insert_asset(
            conn, id=asset_id, name="Iron", type="MATERIAL", blend_path="iron.blend"
        )
        tags_db.add_asset_tag(conn, asset_id, "metal")
        conn.commit()

        op = _make_op()

        with patch("melvil.ops.tag_delete_unused.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ops.tag_delete_unused.open_db", _mock_open_db(conn)):
            result = op.execute(MagicMock())

        assert result == {"FINISHED"}

    def test_returns_cancelled_on_db_error(self):
        from melvil.core.library import LibraryNotConfiguredError

        op = _make_op()
        with patch("melvil.ops.tag_delete_unused.resolve_db_path",
                   side_effect=LibraryNotConfiguredError("not set")):
            result = op.execute(MagicMock())

        assert result == {"CANCELLED"}
