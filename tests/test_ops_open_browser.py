"""Tests for ops/open_browser.py — MELVIL_OT_open_browser popup."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


def _make_asset(id: str, name: str, type: str) -> dict:
    return {"id": id, "name": name, "type": type}


def _make_op():
    from melvil.ops.open_browser import MELVIL_OT_open_browser

    op = MELVIL_OT_open_browser()
    op.type_index = 0
    return op


def _make_wm_items(entries):
    """Build a WM mock whose melvil_type_items behaves like a real collection."""
    items_list = []
    for value, label, icon in entries:
        item = MagicMock()
        item.value = value
        item.label = label
        item.icon = icon
        items_list.append(item)

    collection = MagicMock()
    collection.__len__ = MagicMock(return_value=len(items_list))
    collection.__getitem__ = MagicMock(side_effect=lambda i: items_list[i])
    collection.__bool__ = MagicMock(return_value=bool(items_list))

    wm = MagicMock()
    wm.melvil_type_items = collection
    return wm


def _make_invoke_ctx(tools_x=35, tools_width=45, tools_y=100, tools_height=674, area_x=35, area_y=0, area_height=800, ui_scale=1.0, header_height=26):
    """Build a context mock suitable for invoke() calls."""
    tools_region = MagicMock()
    tools_region.type = "TOOLS"
    tools_region.x = tools_x
    tools_region.width = tools_width
    tools_region.y = tools_y
    tools_region.height = tools_height

    header_region = MagicMock()
    header_region.type = "HEADER"
    header_region.height = header_height

    ctx = MagicMock()
    ctx.area.regions = [tools_region, header_region]
    ctx.area.x = area_x
    ctx.area.y = area_y
    ctx.area.height = area_height
    ctx.preferences.system.ui_scale = ui_scale
    return ctx


_ENTRIES = [
    ("ALL", "All", "ASSET_MANAGER"),
    ("MATERIAL", "Materials", "MATERIAL"),
    ("MESH", "Meshes", "MESH_DATA"),
    ("NODE_GROUP", "Node Groups", "NODETREE"),
]


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


class TestMetadata:
    def test_bl_idname(self):
        from melvil.ops.open_browser import MELVIL_OT_open_browser

        assert MELVIL_OT_open_browser.bl_idname == "melvil.open_browser"

    def test_bl_label(self):
        from melvil.ops.open_browser import MELVIL_OT_open_browser

        assert MELVIL_OT_open_browser.bl_label == "Melvil Library"


# ---------------------------------------------------------------------------
# MELVIL_UL_TypeList
# ---------------------------------------------------------------------------


class TestUIList:
    def test_bl_idname(self):
        from melvil.ops.open_browser import MELVIL_UL_TypeList

        assert MELVIL_UL_TypeList.bl_idname == "MELVIL_UL_type_list"

    def test_draw_item_default_layout(self):
        from melvil.ops.open_browser import MELVIL_UL_TypeList

        ul = MELVIL_UL_TypeList()
        ul.layout_type = "DEFAULT"
        layout = MagicMock()
        item = MagicMock()
        item.label = "Materials"
        item.icon = "MATERIAL"
        ul.draw_item(None, layout, None, item, None, None, None, 1)
        layout.label.assert_called_once_with(text="Materials", icon="MATERIAL")


# ---------------------------------------------------------------------------
# poll()
# ---------------------------------------------------------------------------


class TestPoll:
    def test_returns_true_in_view3d(self):
        from melvil.ops.open_browser import MELVIL_OT_open_browser

        ctx = MagicMock()
        ctx.area.type = "VIEW_3D"
        assert MELVIL_OT_open_browser.poll(ctx) is True

    def test_returns_false_outside_view3d(self):
        from melvil.ops.open_browser import MELVIL_OT_open_browser

        ctx = MagicMock()
        ctx.area.type = "NODE_EDITOR"
        assert MELVIL_OT_open_browser.poll(ctx) is False

    def test_returns_false_when_no_area(self):
        from melvil.ops.open_browser import MELVIL_OT_open_browser

        ctx = MagicMock()
        ctx.area = None
        assert MELVIL_OT_open_browser.poll(ctx) is False


# ---------------------------------------------------------------------------
# invoke() — opens popup, populates WM collection
# ---------------------------------------------------------------------------


class TestInvoke:
    def test_invoke_calls_invoke_popup(self):
        op = _make_op()
        ctx = _make_invoke_ctx()
        op.invoke(ctx, MagicMock())
        ctx.window_manager.invoke_popup.assert_called_once_with(op, width=700)

    def test_invoke_returns_popup_result(self):
        op = _make_op()
        ctx = _make_invoke_ctx()
        ctx.window_manager.invoke_popup.return_value = {"RUNNING_MODAL"}
        result = op.invoke(ctx, MagicMock())
        assert result == {"RUNNING_MODAL"}

    def test_invoke_clears_and_populates_type_items(self):
        op = _make_op()
        ctx = _make_invoke_ctx()
        op.invoke(ctx, MagicMock())
        wm = ctx.window_manager
        wm.melvil_type_items.clear.assert_called_once()
        # One add() call per category entry
        assert wm.melvil_type_items.add.call_count == len(_ENTRIES)

    def test_invoke_resets_type_index_to_zero(self):
        op = _make_op()
        op.type_index = 2
        ctx = _make_invoke_ctx()
        op.invoke(ctx, MagicMock())
        assert op.type_index == 0

    def test_invoke_warps_cursor_to_viewport_top_left(self):
        op = _make_op()
        # tools: x=35, width=45, margin=5 → popup_x=85
        # y=100, height=674 → top=774; 774 - round(1.0*17)=17 → popup_y=757
        ctx = _make_invoke_ctx(tools_x=35, tools_width=45, tools_y=100, tools_height=674, ui_scale=1.0)
        op.invoke(ctx, MagicMock())
        ctx.window.cursor_warp.assert_called_once_with(85, 760)

    def test_invoke_cursor_warp_uses_area_fallback_without_tools_region(self):
        op = _make_op()
        ctx = _make_invoke_ctx(area_x=10, area_y=0, area_height=600, ui_scale=1.0, header_height=26)
        # Remove the TOOLS region so fallback path is exercised
        ctx.area.regions = [r for r in ctx.area.regions if r.type != "TOOLS"]
        op.invoke(ctx, MagicMock())
        # fallback: area.x + margin = 10 + 5 = 15; y = 600 - 26 = 574
        ctx.window.cursor_warp.assert_called_once_with(15, 574)

    def test_invoke_cursor_warp_respects_ui_scale(self):
        op = _make_op()
        # ui_scale=2.0 → margin=10; popup_x=90; top=774; 774 - round(2.0*17)=34 → popup_y=740
        ctx = _make_invoke_ctx(tools_x=35, tools_width=45, tools_y=100, tools_height=674, ui_scale=2.0)
        op.invoke(ctx, MagicMock())
        ctx.window.cursor_warp.assert_called_once_with(90, 746)


# ---------------------------------------------------------------------------
# check()
# ---------------------------------------------------------------------------


class TestCheck:
    def test_check_returns_true(self):
        op = _make_op()
        assert op.check(MagicMock()) is True


# ---------------------------------------------------------------------------
# execute()
# ---------------------------------------------------------------------------


class TestExecute:
    def test_execute_returns_finished(self):
        op = _make_op()
        assert op.execute(MagicMock()) == {"FINISHED"}


# ---------------------------------------------------------------------------
# draw() — popup content
# ---------------------------------------------------------------------------


class TestDraw:
    def _make_ctx(self, type_index=0):
        ctx = MagicMock()
        ctx.window_manager = _make_wm_items(_ENTRIES)
        return ctx

    def _make_op_with_layout(self):
        op = _make_op()
        layout = MagicMock()
        right_col = MagicMock()
        left_col = MagicMock()
        split_mock = MagicMock()
        split_mock.column.side_effect = [left_col, right_col]
        layout.split.return_value = split_mock
        op.layout = layout
        return op, left_col, right_col

    # --- left column uses template_list ---

    def test_draw_left_column_calls_template_list(self):
        op, left_col, right_col = self._make_op_with_layout()
        op.type_index = 0
        ctx = self._make_ctx()

        with patch("melvil.ops.open_browser.load_assets", return_value=[]), \
             patch("melvil.ops.open_browser.draw_asset_section"):
            op.draw(ctx)

        left_col.template_list.assert_called_once()
        call_args = left_col.template_list.call_args
        assert call_args[0][0] == "MELVIL_UL_type_list"

    # --- right column filtering ---

    def test_draw_all_shows_both_sections(self):
        op, left_col, right_col = self._make_op_with_layout()
        op.type_index = 0  # "ALL"
        ctx = self._make_ctx()

        materials = [_make_asset("m1", "Red", "MATERIAL")]
        meshes = [_make_asset("b1", "Rock", "MESH")]

        with patch("melvil.ops.open_browser.load_assets", side_effect=[materials, meshes]), \
             patch("melvil.ops.open_browser.draw_asset_section") as mock_draw:
            op.draw(ctx)

        assert mock_draw.call_count == 2
        titles = [c[0][1] for c in mock_draw.call_args_list]
        assert "Materials" in titles
        assert "Meshes" in titles

    def test_draw_material_filter_shows_only_materials(self):
        op, left_col, right_col = self._make_op_with_layout()
        op.type_index = 1  # "MATERIAL"
        ctx = self._make_ctx()

        with patch("melvil.ops.open_browser.load_assets", return_value=[]), \
             patch("melvil.ops.open_browser.draw_asset_section") as mock_draw:
            op.draw(ctx)

        assert mock_draw.call_count == 1
        assert mock_draw.call_args[0][1] == "Materials"

    def test_draw_mesh_filter_shows_only_meshes(self):
        op, left_col, right_col = self._make_op_with_layout()
        op.type_index = 2  # "MESH"
        ctx = self._make_ctx()

        with patch("melvil.ops.open_browser.load_assets", return_value=[]), \
             patch("melvil.ops.open_browser.draw_asset_section") as mock_draw:
            op.draw(ctx)

        assert mock_draw.call_count == 1
        assert mock_draw.call_args[0][1] == "Meshes"

    def test_db_error_shows_error_label_on_right_column(self):
        op, left_col, right_col = self._make_op_with_layout()
        op.type_index = 0
        ctx = self._make_ctx()

        with patch("melvil.ops.open_browser.load_assets", side_effect=Exception("boom")):
            op.draw(ctx)

        icon_calls = [c for c in right_col.label.call_args_list if c[1].get("icon") == "ERROR"]
        assert icon_calls

    def test_draw_out_of_range_index_defaults_to_all(self):
        op, left_col, right_col = self._make_op_with_layout()
        op.type_index = 99  # out of range → fall back to ALL
        ctx = self._make_ctx()

        with patch("melvil.ops.open_browser.load_assets", return_value=[]), \
             patch("melvil.ops.open_browser.draw_asset_section") as mock_draw:
            op.draw(ctx)

        titles = [c[0][1] for c in mock_draw.call_args_list]
        assert "Materials" in titles
        assert "Meshes" in titles

