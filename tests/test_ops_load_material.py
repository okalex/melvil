"""Tests for ops/load_material.py — MELVIL_OT_load_material_to_slot."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest

from melvil.db.connection import migrate
from melvil.db import assets as assets_db


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


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


SAMPLE_MATERIAL_A = dict(
    id="aaaaaaaa-0000-4000-8000-000000000001",
    name="Red Metal",
    type="MATERIAL",
    blend_path="red_metal_aaaaaaaa.blend",
)

SAMPLE_MATERIAL_B = dict(
    id="bbbbbbbb-0000-4000-8000-000000000002",
    name="Blue Gloss",
    type="MATERIAL",
    blend_path="blue_gloss_bbbbbbbb.blend",
)


def _make_op(slot_mode="NEW", asset_id="", material_index=-1):
    from melvil.ops.load_material import MELVIL_OT_load_material_to_slot

    op = MELVIL_OT_load_material_to_slot()
    op.slot_mode = slot_mode
    op.asset_id = asset_id
    op.material_index = material_index
    return op


def _make_context(obj=None):
    ctx = MagicMock()
    ctx.active_object = obj
    ctx.window_manager.melvil_picker_active = False
    ctx.window_manager.melvil_selection_valid = False
    return ctx


def _make_wm_items(materials):
    """Build a WM-like mock whose melvil_material_items behave like a real collection."""
    items_list = []
    for m in materials:
        item = MagicMock()
        item.name = m["name"]
        item.asset_id = m["id"]
        items_list.append(item)

    collection = MagicMock()
    collection.__len__ = MagicMock(return_value=len(items_list))
    collection.__getitem__ = MagicMock(side_effect=lambda i: items_list[i])

    wm = MagicMock()
    wm.melvil_material_items = collection
    return wm


def _make_object():
    obj = MagicMock()
    obj.data = MagicMock()
    obj.data.materials = MagicMock()
    return obj


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


class TestMetadata:
    def test_bl_idname(self):
        from melvil.ops.load_material import MELVIL_OT_load_material_to_slot
        assert MELVIL_OT_load_material_to_slot.bl_idname == "melvil.load_material_to_slot"

    def test_bl_label(self):
        from melvil.ops.load_material import MELVIL_OT_load_material_to_slot
        assert MELVIL_OT_load_material_to_slot.bl_label == "Load Material"

    def test_has_undo_in_bl_options(self):
        from melvil.ops.load_material import MELVIL_OT_load_material_to_slot
        assert "UNDO" in MELVIL_OT_load_material_to_slot.bl_options

    def test_inherits_operator(self):
        import bpy
        from melvil.ops.load_material import MELVIL_OT_load_material_to_slot
        assert issubclass(MELVIL_OT_load_material_to_slot, bpy.types.Operator)

    def test_draw_shows_material_label(self):
        op = _make_op()
        op.layout = MagicMock()

        op.draw(MagicMock())

        label_calls = [c for c in op.layout.label.call_args_list if c[1].get("icon") == "MATERIAL"]
        assert label_calls

    def test_draw_calls_template_list_when_materials_exist(self):
        op = _make_op()
        op.layout = MagicMock()

        ctx = MagicMock()
        ctx.window_manager.melvil_material_items.__len__ = MagicMock(return_value=2)

        op.draw(ctx)

        op.layout.template_list.assert_called_once()
        call_args = op.layout.template_list.call_args
        assert call_args[0][0] == "MELVIL_UL_material_list"

    def test_draw_template_list_uses_op_for_active_index(self):
        op = _make_op()
        op.layout = MagicMock()

        ctx = MagicMock()
        wm = ctx.window_manager
        wm.melvil_material_items.__len__ = MagicMock(return_value=1)

        op.draw(ctx)

        call_args = op.layout.template_list.call_args[0]
        assert call_args[2] is wm                      # dataptr = wm
        assert call_args[3] == "melvil_material_items"
        assert call_args[4] is op                      # active_dataptr = operator
        assert call_args[5] == "material_index"

    def test_draw_shows_placeholder_when_no_materials(self):
        op = _make_op()
        op.layout = MagicMock()

        # Default MagicMock __len__ returns 0 — simulates empty list
        op.draw(MagicMock())

        text_calls = [c[1].get("text", "") for c in op.layout.label.call_args_list]
        assert any("No materials" in t for t in text_calls)

    def test_draw_db_error_shows_error_label(self):
        op = _make_op()
        op._load_error = "db_error"
        op.layout = MagicMock()

        op.draw(MagicMock())

        error_calls = [c for c in op.layout.label.call_args_list if c[1].get("icon") == "ERROR"]
        assert error_calls


# ---------------------------------------------------------------------------
# poll()
# ---------------------------------------------------------------------------


class TestPoll:
    def test_returns_true_when_active_object_exists(self):
        from melvil.ops.load_material import MELVIL_OT_load_material_to_slot

        ctx = _make_context(obj=_make_object())
        assert MELVIL_OT_load_material_to_slot.poll(ctx) is True

    def test_returns_false_when_no_active_object(self):
        from melvil.ops.load_material import MELVIL_OT_load_material_to_slot

        ctx = _make_context(obj=None)
        assert MELVIL_OT_load_material_to_slot.poll(ctx) is False

    def test_returns_false_in_dialog_when_nothing_selected(self):
        from melvil.ops.load_material import MELVIL_OT_load_material_to_slot

        ctx = _make_context(obj=_make_object())
        ctx.window_manager.melvil_picker_active = True
        ctx.window_manager.melvil_selection_valid = False
        assert MELVIL_OT_load_material_to_slot.poll(ctx) is False

    def test_returns_true_in_dialog_when_item_selected(self):
        from melvil.ops.load_material import MELVIL_OT_load_material_to_slot

        ctx = _make_context(obj=_make_object())
        ctx.window_manager.melvil_picker_active = True
        ctx.window_manager.melvil_selection_valid = True
        assert MELVIL_OT_load_material_to_slot.poll(ctx) is True


# ---------------------------------------------------------------------------
# check()
# ---------------------------------------------------------------------------


class TestCheck:
    def test_check_returns_true(self):
        op = _make_op(material_index=-1)
        ctx = MagicMock()
        ctx.window_manager.melvil_material_items.__len__ = MagicMock(return_value=0)
        assert op.check(ctx) is True

    def test_check_sets_selection_valid_false_when_no_selection(self):
        op = _make_op(material_index=-1)
        ctx = MagicMock()
        ctx.window_manager.melvil_material_items.__len__ = MagicMock(return_value=2)
        op.check(ctx)
        assert ctx.window_manager.melvil_selection_valid is False

    def test_check_sets_selection_valid_true_when_item_selected(self):
        op = _make_op(material_index=0)
        item = MagicMock()
        item.asset_id = SAMPLE_MATERIAL_A["id"]
        ctx = MagicMock()
        ctx.window_manager.melvil_material_items.__len__ = MagicMock(return_value=1)
        ctx.window_manager.melvil_material_items.__getitem__ = MagicMock(return_value=item)
        op.check(ctx)
        assert ctx.window_manager.melvil_selection_valid is True

    def test_check_syncs_asset_id_when_item_selected(self):
        op = _make_op(material_index=0)
        item = MagicMock()
        item.asset_id = SAMPLE_MATERIAL_A["id"]
        ctx = MagicMock()
        ctx.window_manager.melvil_material_items.__len__ = MagicMock(return_value=1)
        ctx.window_manager.melvil_material_items.__getitem__ = MagicMock(return_value=item)
        op.check(ctx)
        assert op.asset_id == SAMPLE_MATERIAL_A["id"]

    def test_check_clears_asset_id_when_no_selection(self):
        op = _make_op(material_index=-1, asset_id=SAMPLE_MATERIAL_A["id"])
        ctx = MagicMock()
        ctx.window_manager.melvil_material_items.__len__ = MagicMock(return_value=0)
        op.check(ctx)
        assert op.asset_id == ""


# ---------------------------------------------------------------------------
# invoke()
# ---------------------------------------------------------------------------


class TestInvoke:
    def test_invoke_opens_props_dialog(self):
        op = _make_op()
        ctx = _make_context(obj=_make_object())

        with patch("melvil.ops.load_material.load_assets", return_value=[]):
            op.invoke(ctx, MagicMock())

        ctx.window_manager.invoke_props_dialog.assert_called_once_with(
            op, width=400, confirm_text="Load Material"
        )

    def test_invoke_return_value_comes_from_dialog(self):
        op = _make_op()
        ctx = _make_context(obj=_make_object())
        ctx.window_manager.invoke_props_dialog.return_value = {"RUNNING_MODAL"}

        with patch("melvil.ops.load_material.load_assets", return_value=[]):
            result = op.invoke(ctx, MagicMock())

        assert result == {"RUNNING_MODAL"}

    def test_invoke_sets_picker_active(self):
        op = _make_op()
        ctx = _make_context(obj=_make_object())

        with patch("melvil.ops.load_material.load_assets", return_value=[]):
            op.invoke(ctx, MagicMock())

        assert ctx.window_manager.melvil_picker_active is True

    def test_invoke_sets_selection_valid_false(self):
        op = _make_op()
        ctx = _make_context(obj=_make_object())

        with patch("melvil.ops.load_material.load_assets", return_value=[]):
            op.invoke(ctx, MagicMock())

        assert ctx.window_manager.melvil_selection_valid is False

    def test_invoke_resets_operator_material_index(self):
        op = _make_op(material_index=3)
        ctx = _make_context(obj=_make_object())

        with patch("melvil.ops.load_material.load_assets", return_value=[]):
            op.invoke(ctx, MagicMock())

        assert op.material_index == -1

    def test_invoke_populates_wm_items(self):
        op = _make_op()
        ctx = _make_context(obj=_make_object())
        rows = [
            {"id": SAMPLE_MATERIAL_A["id"], "name": "Red Metal"},
            {"id": SAMPLE_MATERIAL_B["id"], "name": "Blue Gloss"},
        ]
        with patch("melvil.ops.load_material.load_assets", return_value=rows):
            op.invoke(ctx, MagicMock())

        assert ctx.window_manager.melvil_material_items.add.call_count == 2

    def test_invoke_wm_item_names_match_db_rows(self):
        op = _make_op()
        ctx = _make_context(obj=_make_object())
        rows = [{"id": SAMPLE_MATERIAL_A["id"], "name": "Red Metal"}]

        with patch("melvil.ops.load_material.load_assets", return_value=rows):
            op.invoke(ctx, MagicMock())

        item_mock = ctx.window_manager.melvil_material_items.add.return_value
        assert item_mock.name == "Red Metal"
        assert item_mock.asset_id == SAMPLE_MATERIAL_A["id"]

    def test_invoke_sets_load_error_flag_on_db_failure(self):
        op = _make_op()
        ctx = _make_context(obj=_make_object())

        with patch("melvil.ops.load_material.load_assets", side_effect=Exception("boom")):
            op.invoke(ctx, MagicMock())

        assert op._load_error is not None

    def _context_with_kit(self, active_kit_id: str = "ALL_KITS") -> MagicMock:
        ctx = _make_context(obj=_make_object())
        scene = MagicMock()
        scene.melvil_active_kit_id = active_kit_id
        ctx.scene = scene
        return ctx

    def test_invoke_passes_kit_id_when_specific_kit_active(self):
        op = _make_op()
        kit_id = "00000000-0000-4000-8000-000000000001"
        ctx = self._context_with_kit(active_kit_id=kit_id)

        with patch("melvil.ops.load_material.load_assets", return_value=[]) as mock_load:
            op.invoke(ctx, MagicMock())

        _, kwargs = mock_load.call_args
        assert kwargs.get("kit_id") == kit_id

    def test_invoke_passes_no_kit_filter_when_all_kits(self):
        op = _make_op()
        ctx = self._context_with_kit(active_kit_id="ALL_KITS")

        with patch("melvil.ops.load_material.load_assets", return_value=[]) as mock_load:
            op.invoke(ctx, MagicMock())

        _, kwargs = mock_load.call_args
        assert kwargs.get("kit_id") is None

    def test_invoke_passes_no_kit_filter_when_no_scene(self):
        op = _make_op()
        ctx = _make_context(obj=_make_object())
        ctx.scene = None

        with patch("melvil.ops.load_material.load_assets", return_value=[]) as mock_load:
            op.invoke(ctx, MagicMock())

        _, kwargs = mock_load.call_args
        assert kwargs.get("kit_id") is None


# ---------------------------------------------------------------------------
# execute() — guard checks
# ---------------------------------------------------------------------------


class TestExecuteGuards:
    def test_empty_asset_id_returns_cancelled(self):
        op = _make_op(asset_id="")
        ctx = _make_context(obj=_make_object())

        result = op.execute(ctx)

        assert result == {"CANCELLED"}

    def test_no_active_object_returns_cancelled(self):
        op = _make_op(asset_id=SAMPLE_MATERIAL_A["id"])
        ctx = _make_context(obj=None)

        with patch("melvil.ops.load_material.resolve_library_root", return_value="/lib"):
            result = op.execute(ctx)

        assert result == {"CANCELLED"}

    def test_library_not_configured_returns_cancelled(self):
        from melvil.core.library import LibraryNotConfiguredError

        op = _make_op(asset_id=SAMPLE_MATERIAL_A["id"])
        ctx = _make_context(obj=_make_object())

        with patch(
            "melvil.ops.load_material.resolve_library_root",
            side_effect=LibraryNotConfiguredError("not set"),
        ):
            result = op.execute(ctx)

        assert result == {"CANCELLED"}

    def test_asset_not_found_returns_cancelled(self, conn):
        from melvil.core.asset_reader import AssetNotFoundError

        op = _make_op(asset_id="does-not-exist")
        ctx = _make_context(obj=_make_object())

        with patch("melvil.ops.load_material.resolve_library_root", return_value="/lib"), \
             patch("melvil.ops.load_material.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ops.load_material.open_db", _mock_open_db(conn)), \
             patch("melvil.ops.load_material.AssetReader") as MockReader:
            MockReader.return_value.read.side_effect = AssetNotFoundError("not found")
            result = op.execute(ctx)

        assert result == {"CANCELLED"}

    def test_none_datablock_returns_cancelled(self, conn):
        op = _make_op(asset_id=SAMPLE_MATERIAL_A["id"])
        ctx = _make_context(obj=_make_object())

        with patch("melvil.ops.load_material.resolve_library_root", return_value="/lib"), \
             patch("melvil.ops.load_material.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ops.load_material.open_db", _mock_open_db(conn)), \
             patch("melvil.ops.load_material.AssetReader") as MockReader:
            MockReader.return_value.read.return_value = None
            result = op.execute(ctx)

        assert result == {"CANCELLED"}

    def test_execute_clears_picker_active(self, conn):
        assets_db.insert_asset(conn, **SAMPLE_MATERIAL_A)
        op = _make_op(asset_id=SAMPLE_MATERIAL_A["id"], slot_mode="NEW")
        ctx = _make_context(obj=_make_object())
        ctx.window_manager.melvil_picker_active = True

        with patch("melvil.ops.load_material.resolve_library_root", return_value="/lib"), \
             patch("melvil.ops.load_material.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ops.load_material.open_db", _mock_open_db(conn)), \
             patch("melvil.ops.load_material.AssetReader") as MockReader:
            MockReader.return_value.read.return_value = MagicMock(name="Red Metal")
            op.execute(ctx)

        assert ctx.window_manager.melvil_picker_active is False
        assert ctx.window_manager.melvil_selection_valid is False


# ---------------------------------------------------------------------------
# execute() — slot assignment
# ---------------------------------------------------------------------------


class TestSlotAssignment:
    def _execute(self, conn, slot_mode, obj=None):
        mock_mat = MagicMock()
        mock_mat.name = "Red Metal"

        if obj is None:
            obj = _make_object()

        op = _make_op(asset_id=SAMPLE_MATERIAL_A["id"], slot_mode=slot_mode)
        ctx = _make_context(obj=obj)

        with patch("melvil.ops.load_material.resolve_library_root", return_value="/lib"), \
             patch("melvil.ops.load_material.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ops.load_material.open_db", _mock_open_db(conn)), \
             patch("melvil.ops.load_material.AssetReader") as MockReader:
            MockReader.return_value.read.return_value = mock_mat
            result = op.execute(ctx)

        return result, obj, mock_mat

    def test_new_slot_appends_material(self, conn):
        assets_db.insert_asset(conn, **SAMPLE_MATERIAL_A)
        result, obj, mat = self._execute(conn, slot_mode="NEW")

        assert result == {"FINISHED"}
        obj.data.materials.append.assert_called_once_with(mat)

    def test_replace_slot_sets_active_material(self, conn):
        assets_db.insert_asset(conn, **SAMPLE_MATERIAL_A)
        result, obj, mat = self._execute(conn, slot_mode="REPLACE")

        assert result == {"FINISHED"}
        assert obj.active_material == mat

    def test_new_slot_does_not_set_active_material(self, conn):
        assets_db.insert_asset(conn, **SAMPLE_MATERIAL_A)
        obj = _make_object()
        self._execute(conn, slot_mode="NEW", obj=obj)

        assert obj.active_material != MagicMock()

    def test_replace_slot_does_not_append(self, conn):
        assets_db.insert_asset(conn, **SAMPLE_MATERIAL_A)
        result, obj, mat = self._execute(conn, slot_mode="REPLACE")

        obj.data.materials.append.assert_not_called()


# ---------------------------------------------------------------------------
# cancel()
# ---------------------------------------------------------------------------


class TestCancel:
    def test_cancel_clears_wm_items(self):
        from melvil.ops.load_material import MELVIL_OT_load_material_to_slot

        op = MELVIL_OT_load_material_to_slot()
        ctx = MagicMock()

        op.cancel(ctx)

        ctx.window_manager.melvil_material_items.clear.assert_called_once()

    def test_cancel_clears_picker_active(self):
        from melvil.ops.load_material import MELVIL_OT_load_material_to_slot

        op = MELVIL_OT_load_material_to_slot()
        ctx = MagicMock()
        ctx.window_manager.melvil_picker_active = True

        op.cancel(ctx)

        assert ctx.window_manager.melvil_picker_active is False
        assert ctx.window_manager.melvil_selection_valid is False


# ---------------------------------------------------------------------------
# PropertyGroup / UIList / dismiss operator metadata
# ---------------------------------------------------------------------------


class TestSupportingClasses:
    def test_pg_material_item_inherits_property_group(self):
        import bpy
        from melvil.ops.load_material import MELVIL_PG_MaterialItem

        assert issubclass(MELVIL_PG_MaterialItem, bpy.types.PropertyGroup)

    def test_uilist_bl_idname(self):
        from melvil.ops.load_material import MELVIL_UL_MaterialList

        assert MELVIL_UL_MaterialList.bl_idname == "MELVIL_UL_material_list"

    def test_uilist_inherits_uilist(self):
        import bpy
        from melvil.ops.load_material import MELVIL_UL_MaterialList

        assert issubclass(MELVIL_UL_MaterialList, bpy.types.UIList)
