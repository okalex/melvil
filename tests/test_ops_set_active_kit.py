"""Tests for ops/set_active_kit.py — MELVIL_OT_set_active_kit."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import bpy


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_context(active_kit_id: str = "ALL_KITS") -> MagicMock:
    ctx = MagicMock()
    scene = MagicMock()
    scene.melvil_active_kit_id = active_kit_id
    ctx.scene = scene
    return ctx


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


class TestMetadata:
    def test_bl_idname(self):
        from melvil.ops.set_active_kit import MELVIL_OT_set_active_kit
        assert MELVIL_OT_set_active_kit.bl_idname == "melvil.set_active_kit"

    def test_bl_label(self):
        from melvil.ops.set_active_kit import MELVIL_OT_set_active_kit
        assert MELVIL_OT_set_active_kit.bl_label == "Active Kit"

    def test_inherits_operator(self):
        from melvil.ops.set_active_kit import MELVIL_OT_set_active_kit
        assert issubclass(MELVIL_OT_set_active_kit, bpy.types.Operator)


# ---------------------------------------------------------------------------
# execute()
# ---------------------------------------------------------------------------


class TestExecute:
    def _make_op(self, kit_id: str = "ALL_KITS"):
        from melvil.ops.set_active_kit import MELVIL_OT_set_active_kit
        op = MELVIL_OT_set_active_kit()
        op.kit_id = kit_id
        return op

    def test_returns_finished(self):
        op = self._make_op()
        ctx = _make_context()
        result = op.execute(ctx)
        assert result == {"FINISHED"}

    def test_sets_scene_active_kit_id(self):
        kit_uuid = "00000000-0000-4000-8000-000000000001"
        op = self._make_op(kit_id=kit_uuid)
        ctx = _make_context()
        op.execute(ctx)
        assert ctx.scene.melvil_active_kit_id == kit_uuid

    def test_sets_all_kits_sentinel(self):
        op = self._make_op(kit_id="ALL_KITS")
        ctx = _make_context(active_kit_id="some_kit_id")
        op.execute(ctx)
        assert ctx.scene.melvil_active_kit_id == "ALL_KITS"

    def test_no_error_when_scene_is_none(self):
        op = self._make_op(kit_id="ALL_KITS")
        ctx = MagicMock()
        ctx.scene = None
        # Should not raise
        result = op.execute(ctx)
        assert result == {"FINISHED"}


# ---------------------------------------------------------------------------
# _get_kit_items
# ---------------------------------------------------------------------------


class TestGetKitItems:
    def test_always_includes_all_kits_first(self):
        from melvil.ops.set_active_kit import _get_kit_items
        with patch("melvil.ops.set_active_kit.resolve_db_path", side_effect=Exception("no db")):
            items = _get_kit_items(None, None)
        assert items[0][0] == "ALL_KITS"
        assert items[0][1] == "All Kits"

    def test_includes_kits_from_db(self):
        from melvil.ops.set_active_kit import _get_kit_items

        fake_kits = [
            {"id": "kit-uuid-1", "name": "Materials", "description": ""},
            {"id": "kit-uuid-2", "name": "Environments", "description": None},
        ]
        with patch("melvil.ops.set_active_kit.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ops.set_active_kit.open_db") as mock_open, \
             patch("melvil.ops.set_active_kit.list_kits", return_value=fake_kits):
            mock_open.return_value.__enter__ = lambda s: MagicMock()
            mock_open.return_value.__exit__ = MagicMock(return_value=False)
            items = _get_kit_items(None, None)

        ids = [item[0] for item in items]
        assert "kit-uuid-1" in ids
        assert "kit-uuid-2" in ids

    def test_falls_back_gracefully_on_db_error(self):
        from melvil.ops.set_active_kit import _get_kit_items
        with patch("melvil.ops.set_active_kit.resolve_db_path", side_effect=Exception("fail")):
            items = _get_kit_items(None, None)
        # At minimum the ALL_KITS item should survive
        assert len(items) >= 1
        assert items[0][0] == "ALL_KITS"

    def test_strings_are_interned(self):
        from melvil.ops.set_active_kit import _get_kit_items
        with patch("melvil.ops.set_active_kit.resolve_db_path", side_effect=Exception("no db")):
            items = _get_kit_items(None, None)
        # sys.intern returns the canonical interned string
        assert items[0][0] is "ALL_KITS"  # noqa: F632 — intentional identity check
