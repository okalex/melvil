"""Tests for ops/open_browser.py — MELVIL_OT_open_browser popup."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


def _make_asset(id: str, name: str, type: str) -> dict:
    return {"id": id, "name": name, "type": type}


def _make_op():
    from melvil.ops.open_browser import MELVIL_OT_open_browser

    op = MELVIL_OT_open_browser()
    op.type_filter = "ALL"
    op.kit_filter = "ALL_KITS"
    op.search_query = ""
    return op


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


_POPUP_WIDTH = 900


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
        ctx.window_manager.invoke_popup.assert_called_once_with(op, width=_POPUP_WIDTH)

    def test_invoke_returns_popup_result(self):
        op = _make_op()
        ctx = _make_invoke_ctx()
        ctx.window_manager.invoke_popup.return_value = {"RUNNING_MODAL"}
        result = op.invoke(ctx, MagicMock())
        assert result == {"RUNNING_MODAL"}

    def test_invoke_resets_type_filter_to_all(self):
        op = _make_op()
        op.type_filter = "MESH"
        ctx = _make_invoke_ctx()
        op.invoke(ctx, MagicMock())
        assert op.type_filter == "ALL"

    def test_invoke_resets_kit_filter_to_all(self):
        op = _make_op()
        op.kit_filter = "some-uuid"
        ctx = _make_invoke_ctx()
        op.invoke(ctx, MagicMock())
        assert op.kit_filter == "ALL_KITS"

    def test_invoke_resets_search_query_to_empty(self):
        op = _make_op()
        op.search_query = "previous search"
        ctx = _make_invoke_ctx()
        op.invoke(ctx, MagicMock())
        assert op.search_query == ""

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
    def _make_ctx(self):
        ctx = MagicMock()
        ctx.window_manager.melvil_active_tag_filters = ""
        ctx.window_manager.melvil_selected_asset_id = ""
        return ctx

    def _make_op_with_layout(self):
        op = _make_op()
        layout = MagicMock()
        left_col = MagicMock()
        rest_col = MagicMock()
        middle_col = MagicMock()
        right_col = MagicMock()
        outer_split = MagicMock()
        inner_split = MagicMock()
        outer_split.column.side_effect = [left_col, rest_col]
        inner_split.column.side_effect = [middle_col, right_col]
        rest_col.split.return_value = inner_split
        layout.split.return_value = outer_split
        op.layout = layout
        return op, left_col, middle_col, right_col

    # --- left column uses prop with expand ---

    def test_draw_left_column_type_filter_prop_expand(self):
        op, left_col, middle_col, _right = self._make_op_with_layout()
        op.type_filter = "ALL"
        ctx = self._make_ctx()

        with patch("melvil.ops.open_browser.load_assets", return_value=[]), \
             patch("melvil.ops.open_browser.load_kits", return_value=[]), \
             patch("melvil.ops.open_browser.draw_asset_section"):
            op.draw(ctx)

        left_col.prop.assert_any_call(op, "type_filter", expand=True)

    def test_draw_left_column_kit_filter_prop_expand(self):
        op, left_col, middle_col, _right = self._make_op_with_layout()
        op.type_filter = "ALL"
        ctx = self._make_ctx()

        with patch("melvil.ops.open_browser.load_assets", return_value=[]), \
             patch("melvil.ops.open_browser.load_kits", return_value=[]), \
             patch("melvil.ops.open_browser.draw_asset_section"):
            op.draw(ctx)

        left_col.prop.assert_any_call(op, "kit_filter", expand=True)

    # --- right column filtering ---

    def test_draw_all_shows_all_sections(self):
        op, left_col, middle_col, _right = self._make_op_with_layout()
        op.type_filter = "ALL"
        ctx = self._make_ctx()

        materials = [_make_asset("m1", "Red", "MATERIAL")]
        meshes = [_make_asset("b1", "Rock", "MESH")]
        node_groups = [_make_asset("n1", "MyGroup", "NODE_GROUP")]

        with patch("melvil.ops.open_browser.load_assets", side_effect=[materials, meshes, node_groups]), \
             patch("melvil.ops.open_browser.load_kits", return_value=[]), \
             patch("melvil.ops.open_browser.draw_asset_section") as mock_draw:
            op.draw(ctx)

        assert mock_draw.call_count == 3
        titles = [c[0][1] for c in mock_draw.call_args_list]
        assert "Materials" in titles
        assert "Meshes" in titles
        assert "Node Groups" in titles

    def test_draw_material_filter_shows_only_materials(self):
        op, left_col, middle_col, _right = self._make_op_with_layout()
        op.type_filter = "MATERIAL"
        ctx = self._make_ctx()

        with patch("melvil.ops.open_browser.load_assets", return_value=[]), \
             patch("melvil.ops.open_browser.load_kits", return_value=[]), \
             patch("melvil.ops.open_browser.draw_asset_section") as mock_draw:
            op.draw(ctx)

        assert mock_draw.call_count == 1
        assert mock_draw.call_args[0][1] == "Materials"

    def test_draw_mesh_filter_shows_only_meshes(self):
        op, left_col, middle_col, _right = self._make_op_with_layout()
        op.type_filter = "MESH"
        ctx = self._make_ctx()

        with patch("melvil.ops.open_browser.load_assets", return_value=[]), \
             patch("melvil.ops.open_browser.load_kits", return_value=[]), \
             patch("melvil.ops.open_browser.draw_asset_section") as mock_draw:
            op.draw(ctx)

        assert mock_draw.call_count == 1
        assert mock_draw.call_args[0][1] == "Meshes"

    def test_draw_node_group_filter_shows_only_node_groups(self):
        op, left_col, middle_col, _right = self._make_op_with_layout()
        op.type_filter = "NODE_GROUP"
        ctx = self._make_ctx()

        with patch("melvil.ops.open_browser.load_assets", return_value=[]), \
             patch("melvil.ops.open_browser.load_kits", return_value=[]), \
             patch("melvil.ops.open_browser.draw_asset_section") as mock_draw:
            op.draw(ctx)

        assert mock_draw.call_count == 1
        assert mock_draw.call_args[0][1] == "Node Groups"

    def test_db_error_shows_error_label_on_right_column(self):
        op, left_col, middle_col, _right = self._make_op_with_layout()
        op.type_filter = "ALL"
        ctx = self._make_ctx()

        with patch("melvil.ops.open_browser.load_kits", side_effect=Exception("boom")):
            op.draw(ctx)

        icon_calls = [c for c in middle_col.label.call_args_list if c[1].get("icon") == "ERROR"]
        assert icon_calls

    # --- search input ---

    def test_draw_renders_search_prop_on_left_column(self):
        op, left_col, middle_col, _right = self._make_op_with_layout()
        op.type_filter = "ALL"
        op.search_query = ""
        ctx = self._make_ctx()

        with patch("melvil.ops.open_browser.load_assets", return_value=[]), \
             patch("melvil.ops.open_browser.load_kits", return_value=[]), \
             patch("melvil.ops.open_browser.draw_asset_section"):
            op.draw(ctx)

        left_col.prop.assert_any_call(op, "search_query", text="", icon="VIEWZOOM")

    def test_draw_search_filters_assets_passed_to_draw_section(self):
        op, left_col, middle_col, _right = self._make_op_with_layout()
        op.type_filter = "MATERIAL"
        op.search_query = "pla"
        ctx = self._make_ctx()

        all_materials = [
            _make_asset("m1", "Plastic", "MATERIAL"),
            _make_asset("m2", "Plaster", "MATERIAL"),
            _make_asset("m3", "Iron", "MATERIAL"),
        ]

        with patch("melvil.ops.open_browser.load_assets", return_value=all_materials), \
             patch("melvil.ops.open_browser.load_kits", return_value=[]), \
             patch("melvil.ops.open_browser.draw_asset_section") as mock_draw:
            op.draw(ctx)

        passed_assets = mock_draw.call_args[0][3]
        assert len(passed_assets) == 2
        assert {a["name"] for a in passed_assets} == {"Plastic", "Plaster"}

    def test_draw_empty_search_passes_all_assets(self):
        op, left_col, middle_col, _right = self._make_op_with_layout()
        op.type_filter = "MESH"
        op.search_query = ""
        ctx = self._make_ctx()

        meshes = [_make_asset(f"m{i}", f"Mesh {i}", "MESH") for i in range(4)]

        with patch("melvil.ops.open_browser.load_assets", return_value=meshes), \
             patch("melvil.ops.open_browser.load_kits", return_value=[]), \
             patch("melvil.ops.open_browser.draw_asset_section") as mock_draw:
            op.draw(ctx)

        passed_assets = mock_draw.call_args[0][3]
        assert len(passed_assets) == 4


# ---------------------------------------------------------------------------
# draw() — tag filter pills
# ---------------------------------------------------------------------------

_TAG_METAL = {"id": "aaaa-0001", "name": "metal"}
_TAG_PBR = {"id": "bbbb-0002", "name": "pbr"}


class TestDrawTagFilterPills:
    def _make_ctx(self, active_filters=""):
        ctx = MagicMock()
        ctx.window_manager.melvil_active_tag_filters = active_filters
        ctx.window_manager.melvil_selected_asset_id = ""
        return ctx

    def _make_op_with_layout(self):
        op = _make_op()
        layout = MagicMock()
        left_col = MagicMock()
        rest_col = MagicMock()
        middle_col = MagicMock()
        right_col = MagicMock()
        outer_split = MagicMock()
        inner_split = MagicMock()
        outer_split.column.side_effect = [left_col, rest_col]
        inner_split.column.side_effect = [middle_col, right_col]
        rest_col.split.return_value = inner_split
        layout.split.return_value = outer_split
        op.layout = layout
        return op, left_col, middle_col, right_col

    def _default_patches(self, assets=None, tags=None, memberships=None):
        """Return a dict of standard patches for draw() calls in this class."""
        return {
            "melvil.ops.open_browser.load_assets": assets if assets is not None else [],
            "melvil.ops.open_browser.load_kits": [],
            "melvil.ops.open_browser.load_asset_tag_memberships": memberships or {},
            "melvil.ops.open_browser.load_all_tags": tags if tags is not None else [],
        }

    def test_tag_list_not_rendered_when_no_visible_tags(self):
        op, left_col, _mid, _right = self._make_op_with_layout()
        ctx = self._make_ctx()

        with patch("melvil.ops.open_browser.load_assets", return_value=[]), \
             patch("melvil.ops.open_browser.load_kits", return_value=[]), \
             patch("melvil.ops.open_browser.load_asset_tag_memberships", return_value={}), \
             patch("melvil.ops.open_browser.load_all_tags", return_value=[]), \
             patch("melvil.ops.open_browser.draw_asset_section"):
            op.draw(ctx)

        left_col.template_list.assert_not_called()

    def test_tag_list_rendered_when_visible_tags_exist(self):
        op, left_col, _mid, _right = self._make_op_with_layout()
        op.type_filter = "MATERIAL"
        ctx = self._make_ctx()
        asset = _make_asset("a1", "Iron", "MATERIAL")
        asset["id"] = "a1"

        with patch("melvil.ops.open_browser.load_assets", return_value=[asset]), \
             patch("melvil.ops.open_browser.load_kits", return_value=[]), \
             patch("melvil.ops.open_browser.load_asset_tag_memberships", return_value={}), \
             patch("melvil.ops.open_browser.load_all_tags",
                   return_value=[_TAG_METAL]), \
             patch("melvil.ops.open_browser.draw_asset_section"):
            op.draw(ctx)

        left_col.row.return_value.template_list.assert_called_once()

    def test_filter_tags_collection_populated_from_wm_filters(self):
        op, left_col, _mid, _right = self._make_op_with_layout()
        op.type_filter = "MATERIAL"
        ctx = self._make_ctx(active_filters="aaaa-0001")

        with patch("melvil.ops.open_browser.load_assets", return_value=[_make_asset("a1", "Iron", "MATERIAL")]), \
             patch("melvil.ops.open_browser.load_kits", return_value=[]), \
             patch("melvil.ops.open_browser.load_asset_tag_memberships", return_value={}), \
             patch("melvil.ops.open_browser.load_all_tags", return_value=[_TAG_METAL]), \
             patch("melvil.ops.open_browser.draw_asset_section"):
            op.draw(ctx)

        ctx.window_manager.melvil_filter_tags.clear.assert_called_once()

    def test_tag_filter_applied_to_sections(self):
        """Assets without active tags should be excluded from the drawn sections."""
        op, left_col, _mid, _right = self._make_op_with_layout()
        op.type_filter = "MATERIAL"
        ctx = self._make_ctx(active_filters="aaaa-0001")

        asset_with_tag = _make_asset("a1", "Iron", "MATERIAL")
        asset_without_tag = _make_asset("a2", "Plastic", "MATERIAL")
        # Only a1 has the active tag
        memberships = {"a1": {"aaaa-0001"}}

        with patch("melvil.ops.open_browser.load_assets",
                   return_value=[asset_with_tag, asset_without_tag]), \
             patch("melvil.ops.open_browser.load_kits", return_value=[]), \
             patch("melvil.ops.open_browser.load_asset_tag_memberships",
                   return_value=memberships), \
             patch("melvil.ops.open_browser.load_all_tags", return_value=[_TAG_METAL]), \
             patch("melvil.ops.open_browser.draw_asset_section") as mock_draw:
            op.draw(ctx)

        drawn_assets = mock_draw.call_args[0][3]
        assert len(drawn_assets) == 1
        assert drawn_assets[0]["id"] == "a1"

    def test_no_tag_filter_passes_all_assets_to_sections(self):
        """With no active filters, all search-matched assets are drawn."""
        op, left_col, _mid, _right = self._make_op_with_layout()
        op.type_filter = "MATERIAL"
        ctx = self._make_ctx(active_filters="")

        assets = [_make_asset("a1", "Iron", "MATERIAL"), _make_asset("a2", "Plastic", "MATERIAL")]

        with patch("melvil.ops.open_browser.load_assets", return_value=assets), \
             patch("melvil.ops.open_browser.load_kits", return_value=[]), \
             patch("melvil.ops.open_browser.load_asset_tag_memberships", return_value={}), \
             patch("melvil.ops.open_browser.load_all_tags", return_value=[]), \
             patch("melvil.ops.open_browser.draw_asset_section") as mock_draw:
            op.draw(ctx)

        drawn_assets = mock_draw.call_args[0][3]
        assert len(drawn_assets) == 2

    def test_load_all_tags_called(self):
        """load_all_tags is called to populate the filter tag list."""
        op, left_col, _mid, _right = self._make_op_with_layout()
        op.type_filter = "MATERIAL"
        ctx = self._make_ctx()
        asset = _make_asset("unique-id-123", "Iron", "MATERIAL")

        with patch("melvil.ops.open_browser.load_assets", return_value=[asset]), \
             patch("melvil.ops.open_browser.load_kits", return_value=[]), \
             patch("melvil.ops.open_browser.load_asset_tag_memberships", return_value={}), \
             patch("melvil.ops.open_browser.load_all_tags",
                   return_value=[]) as mock_load_all_tags, \
             patch("melvil.ops.open_browser.draw_asset_section"):
            op.draw(ctx)

        mock_load_all_tags.assert_called_once()

    def test_pill_row_separator_rendered_before_pills(self):
        """A separator should appear between kit filter and pills."""
        op, left_col, _mid, _right = self._make_op_with_layout()
        op.type_filter = "MATERIAL"
        ctx = self._make_ctx()

        with patch("melvil.ops.open_browser.load_assets",
                   return_value=[_make_asset("a1", "Iron", "MATERIAL")]), \
             patch("melvil.ops.open_browser.load_kits", return_value=[]), \
             patch("melvil.ops.open_browser.load_asset_tag_memberships", return_value={}), \
             patch("melvil.ops.open_browser.load_all_tags",
                   return_value=[_TAG_METAL]), \
             patch("melvil.ops.open_browser.draw_asset_section"):
            op.draw(ctx)

        left_col.separator.assert_called()


# ---------------------------------------------------------------------------
# draw() — tag-name search integration
# ---------------------------------------------------------------------------


class TestTagNameSearch:
    """draw() should pass tag names to filter_assets for tag-based search."""

    def _make_ctx(self, query=""):
        ctx = MagicMock()
        ctx.window_manager.melvil_active_tag_filters = ""
        ctx.window_manager.melvil_selected_asset_id = ""
        return ctx

    def _make_op_with_layout(self, query=""):
        op = _make_op()
        op.search_query = query
        layout = MagicMock()
        left_col = MagicMock()
        rest_col = MagicMock()
        middle_col = MagicMock()
        right_col = MagicMock()
        outer_split = MagicMock()
        inner_split = MagicMock()
        outer_split.column.side_effect = [left_col, rest_col]
        inner_split.column.side_effect = [middle_col, right_col]
        rest_col.split.return_value = inner_split
        layout.split.return_value = outer_split
        op.layout = layout
        return op, left_col, middle_col, right_col

    def test_load_asset_tag_names_called_when_query_non_empty(self):
        op, _left, _mid, _right = self._make_op_with_layout(query="metal")
        op.type_filter = "MATERIAL"
        ctx = self._make_ctx()
        asset = _make_asset("a1", "Iron", "MATERIAL")

        with patch("melvil.ops.open_browser.load_assets", return_value=[asset]), \
             patch("melvil.ops.open_browser.load_kits", return_value=[]), \
             patch("melvil.ops.open_browser.load_asset_tag_names",
                   return_value={}) as mock_names, \
             patch("melvil.ops.open_browser.load_asset_tag_memberships", return_value={}), \
             patch("melvil.ops.open_browser.load_all_tags", return_value=[]), \
             patch("melvil.ops.open_browser.draw_asset_section"):
            op.draw(ctx)

        mock_names.assert_called_once_with(["a1"])

    def test_load_asset_tag_names_not_called_when_query_empty(self):
        op, _left, _mid, _right = self._make_op_with_layout(query="")
        op.type_filter = "MATERIAL"
        ctx = self._make_ctx()

        with patch("melvil.ops.open_browser.load_assets", return_value=[]), \
             patch("melvil.ops.open_browser.load_kits", return_value=[]), \
             patch("melvil.ops.open_browser.load_asset_tag_names") as mock_names, \
             patch("melvil.ops.open_browser.draw_asset_section"):
            op.draw(ctx)

        mock_names.assert_not_called()

    def test_asset_included_when_tag_matches_query_but_name_does_not(self):
        """An asset whose name doesn't match the query but has a matching tag is shown."""
        op, _left, _mid, _right = self._make_op_with_layout(query="metal")
        op.type_filter = "MATERIAL"
        ctx = self._make_ctx()
        # "Glass" does not contain "metal", but the asset is tagged "metal"
        asset = _make_asset("a1", "Glass", "MATERIAL")

        with patch("melvil.ops.open_browser.load_assets", return_value=[asset]), \
             patch("melvil.ops.open_browser.load_kits", return_value=[]), \
             patch("melvil.ops.open_browser.load_asset_tag_names",
                   return_value={"a1": ["metal"]}), \
             patch("melvil.ops.open_browser.load_asset_tag_memberships", return_value={}), \
             patch("melvil.ops.open_browser.load_all_tags", return_value=[]), \
             patch("melvil.ops.open_browser.draw_asset_section") as mock_draw:
            op.draw(ctx)

        drawn_assets = mock_draw.call_args[0][3]
        assert len(drawn_assets) == 1
        assert drawn_assets[0]["id"] == "a1"

    def test_asset_excluded_when_neither_name_nor_tag_matches(self):
        op, _left, _mid, _right = self._make_op_with_layout(query="metal")
        op.type_filter = "MATERIAL"
        ctx = self._make_ctx()
        asset = _make_asset("a1", "Glass", "MATERIAL")

        with patch("melvil.ops.open_browser.load_assets", return_value=[asset]), \
             patch("melvil.ops.open_browser.load_kits", return_value=[]), \
             patch("melvil.ops.open_browser.load_asset_tag_names",
                   return_value={"a1": ["transparent"]}), \
             patch("melvil.ops.open_browser.load_asset_tag_memberships", return_value={}), \
             patch("melvil.ops.open_browser.load_all_tags", return_value=[]), \
             patch("melvil.ops.open_browser.draw_asset_section") as mock_draw:
            op.draw(ctx)

        drawn_assets = mock_draw.call_args[0][3]
        assert len(drawn_assets) == 0



