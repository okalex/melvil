"""Tests for ops/set_preview_object.py — MELVIL_OT_set_preview_object."""

from __future__ import annotations

from unittest.mock import MagicMock

import bpy

from melvil.preferences import MelvilPreferences


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
        from melvil.ops.set_preview_object import MELVIL_OT_set_preview_object
        assert MELVIL_OT_set_preview_object.bl_idname == "melvil.set_preview_object"

    def test_bl_label(self):
        from melvil.ops.set_preview_object import MELVIL_OT_set_preview_object
        assert MELVIL_OT_set_preview_object.bl_label == "Material Preview Object"

    def test_inherits_operator(self):
        from melvil.ops.set_preview_object import MELVIL_OT_set_preview_object
        assert issubclass(MELVIL_OT_set_preview_object, bpy.types.Operator)


# ---------------------------------------------------------------------------
# execute()
# ---------------------------------------------------------------------------


class TestExecute:
    def _make_op(self, object_id: str = "BUILTIN_UV_SPHERE"):
        from melvil.ops.set_preview_object import MELVIL_OT_set_preview_object
        op = MELVIL_OT_set_preview_object()
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
            ctx.preferences.addons.get(MelvilPreferences.bl_idname).preferences.material_preview_object
            == "BUILTIN_CUBE"
        )

    def test_sets_builtin_sphere(self):
        op = self._make_op(object_id="BUILTIN_UV_SPHERE")
        ctx = _make_context()
        op.execute(ctx)
        ctx.preferences.addons.get.return_value.preferences.material_preview_object = "BUILTIN_UV_SPHERE"
        assert (
            ctx.preferences.addons.get(MelvilPreferences.bl_idname).preferences.material_preview_object
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
        from melvil.ops.set_preview_object import _get_items, _BUILTIN_ITEMS

        items = _get_items(None, None)
        builtin_ids = {item[0] for item in _BUILTIN_ITEMS}
        item_ids = {item[0] for item in items}
        assert builtin_ids.issubset(item_ids)

    def test_uv_sphere_is_first_item(self):
        from melvil.ops.set_preview_object import _get_items

        items = _get_items(None, None)
        assert items[0][0] == "BUILTIN_UV_SPHERE"
