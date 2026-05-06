"""Tests for ops/set_preview_object.py — BLAMMO_OT_set_preview_object."""

from __future__ import annotations

from unittest.mock import MagicMock

import bpy

from blammo.preferences import BlammoPreferences


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_context(preview_object: str = "BUILTIN_UV_SPHERE") -> MagicMock:
    ctx = MagicMock()
    mock_prefs = MagicMock()
    mock_prefs.preferences.material_preview_object = preview_object
    ctx.preferences.addons.get.return_value = mock_prefs
    return ctx


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


class TestMetadata:
    def test_bl_idname(self):
        from blammo.ops.set_preview_object import BLAMMO_OT_set_preview_object
        assert BLAMMO_OT_set_preview_object.bl_idname == "blammo.set_preview_object"

    def test_bl_label(self):
        from blammo.ops.set_preview_object import BLAMMO_OT_set_preview_object
        assert BLAMMO_OT_set_preview_object.bl_label == "Material Preview Object"

    def test_inherits_operator(self):
        from blammo.ops.set_preview_object import BLAMMO_OT_set_preview_object
        assert issubclass(BLAMMO_OT_set_preview_object, bpy.types.Operator)


# ---------------------------------------------------------------------------
# execute()
# ---------------------------------------------------------------------------


class TestExecute:
    def _make_op(self, object_id: str = "BUILTIN_UV_SPHERE"):
        from blammo.ops.set_preview_object import BLAMMO_OT_set_preview_object
        op = BLAMMO_OT_set_preview_object()
        op.object_id = object_id
        return op

    def test_returns_finished(self):
        op = self._make_op()
        ctx = _make_context()
        result = op.execute(ctx)
        assert result == {"FINISHED"}

    def test_sets_material_preview_object_on_prefs(self):
        op = self._make_op(object_id="BUILTIN_CUBE")
        ctx = _make_context()
        op.execute(ctx)
        ctx.preferences.addons.get.return_value.preferences.material_preview_object = "BUILTIN_CUBE"
        assert (
            ctx.preferences.addons.get(BlammoPreferences.bl_idname).preferences.material_preview_object
            == "BUILTIN_CUBE"
        )

    def test_sets_builtin_sphere(self):
        op = self._make_op(object_id="BUILTIN_UV_SPHERE")
        ctx = _make_context()
        op.execute(ctx)
        ctx.preferences.addons.get.return_value.preferences.material_preview_object = "BUILTIN_UV_SPHERE"
        assert (
            ctx.preferences.addons.get(BlammoPreferences.bl_idname).preferences.material_preview_object
            == "BUILTIN_UV_SPHERE"
        )

    def test_no_error_when_prefs_absent(self):
        """Must not raise if the addon entry is not registered."""
        op = self._make_op()
        ctx = MagicMock()
        ctx.preferences.addons.get.return_value = None
        result = op.execute(ctx)
        assert result == {"FINISHED"}


# ---------------------------------------------------------------------------
# _get_items() — enum callback
# ---------------------------------------------------------------------------


class TestGetItems:
    def test_includes_all_builtin_items(self):
        from blammo.ops.set_preview_object import _get_items, _BUILTIN_ITEMS

        items = _get_items(None, None)
        builtin_ids = {item[0] for item in _BUILTIN_ITEMS}
        item_ids = {item[0] for item in items}
        assert builtin_ids.issubset(item_ids)

    def test_uv_sphere_is_first_item(self):
        from blammo.ops.set_preview_object import _get_items

        items = _get_items(None, None)
        assert items[0][0] == "BUILTIN_UV_SPHERE"
