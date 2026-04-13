"""Tests for ui/grid_list.py — GPU-drawn card grid component."""

from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock, call

import pytest


def _make_item(id: str, name: str, type: str) -> dict:
    return {"id": id, "name": name, "type": type}


def _make_region(height: int = 600) -> MagicMock:
    region = MagicMock()
    region.height = height
    return region


# ---------------------------------------------------------------------------
# draw_rect / draw_rect_outline
# ---------------------------------------------------------------------------


class TestDrawRect:
    def test_calls_shader_and_batch(self):
        from melvil.ui.grid_list import draw_rect

        # Should not raise — exercises the shader/batch pipeline.
        draw_rect(10, 20, 100, 50, (1.0, 0.0, 0.0, 1.0))

    def test_draws_with_given_color(self):
        import gpu
        from melvil.ui.grid_list import draw_rect

        shader_mock = gpu.shader.from_builtin.return_value
        shader_mock.uniform_float.reset_mock()

        color = (0.5, 0.5, 0.5, 1.0)
        draw_rect(0, 0, 10, 10, color)

        shader_mock.uniform_float.assert_called_with("color", color)


class TestDrawRectOutline:
    def test_calls_shader_and_batch(self):
        from melvil.ui.grid_list import draw_rect_outline

        draw_rect_outline(10, 20, 100, 50, (1.0, 1.0, 1.0, 1.0))

    def test_thickness_parameter_accepted(self):
        from melvil.ui.grid_list import draw_rect_outline

        # Should not raise with custom thickness.
        draw_rect_outline(0, 0, 50, 50, (1.0, 1.0, 1.0, 1.0), thickness=2)


# ---------------------------------------------------------------------------
# draw_grid
# ---------------------------------------------------------------------------


class TestDrawGrid:
    def test_empty_items_returns_zero_height(self):
        from melvil.ui import grid_list
        from melvil.ui.grid_list import draw_grid

        region = _make_region()
        height = draw_grid(region, [], cols=3, rows_visible=4)

        assert height == 0
        assert grid_list._card_rects == []

    def test_empty_items_clears_card_rects(self):
        from melvil.ui import grid_list
        from melvil.ui.grid_list import draw_grid

        # Seed with stale data.
        grid_list._card_rects = [("stale",)]
        draw_grid(_make_region(), [], cols=3, rows_visible=4)

        assert grid_list._card_rects == []

    def test_card_rects_populated_for_6_items_3_cols(self):
        from melvil.ui import grid_list
        from melvil.ui.grid_list import draw_grid

        items = [_make_item(f"id-{i}", f"Item {i}", "MESH") for i in range(6)]
        draw_grid(_make_region(), items, cols=3, rows_visible=4)

        assert len(grid_list._card_rects) == 6
        # Each rect is (x, y, w, h, item_id)
        ids = [r[4] for r in grid_list._card_rects]
        assert ids == [f"id-{i}" for i in range(6)]

    def test_card_rects_columns_layout(self):
        from melvil.ui import grid_list
        from melvil.ui.grid_list import draw_grid, CARD_W, CARD_GAP, GRID_ORIGIN_X

        items = [_make_item(f"id-{i}", f"Item {i}", "MESH") for i in range(6)]
        draw_grid(_make_region(), items, cols=3, rows_visible=4)

        # First row: 3 items across columns.
        xs = [r[0] for r in grid_list._card_rects[:3]]
        expected = [
            GRID_ORIGIN_X + c * (CARD_W + CARD_GAP) for c in range(3)
        ]
        assert xs == expected

    def test_returns_correct_height_for_2_rows(self):
        from melvil.ui.grid_list import draw_grid, CARD_H, CARD_GAP, GRID_ORIGIN_Y

        items = [_make_item(f"id-{i}", f"Item {i}", "MESH") for i in range(6)]
        height = draw_grid(_make_region(), items, cols=3, rows_visible=4)

        # 6 items / 3 cols = 2 rows
        expected = 2 * (CARD_H + CARD_GAP) + GRID_ORIGIN_Y * 2
        assert height == expected

    def test_returns_correct_height_for_partial_row(self):
        from melvil.ui.grid_list import draw_grid, CARD_H, CARD_GAP, GRID_ORIGIN_Y

        items = [_make_item(f"id-{i}", f"Item {i}", "MESH") for i in range(4)]
        height = draw_grid(_make_region(), items, cols=3, rows_visible=4)

        # 4 items / 3 cols = ceil(4/3) = 2 rows
        expected = 2 * (CARD_H + CARD_GAP) + GRID_ORIGIN_Y * 2
        assert height == expected

    def test_scroll_offset_slices_items(self):
        from melvil.ui import grid_list
        from melvil.ui.grid_list import draw_grid

        items = [_make_item(f"id-{i}", f"Item {i}", "MESH") for i in range(12)]
        draw_grid(_make_region(), items, cols=3, rows_visible=2, scroll_offset=1)

        # offset=1 means skip first row (3 items), show next 6.
        ids = [r[4] for r in grid_list._card_rects]
        assert ids == [f"id-{i}" for i in range(3, 9)]

    def test_scroll_offset_beyond_items_returns_zero(self):
        from melvil.ui import grid_list
        from melvil.ui.grid_list import draw_grid

        items = [_make_item(f"id-{i}", f"Item {i}", "MESH") for i in range(3)]
        height = draw_grid(_make_region(), items, cols=3, rows_visible=2, scroll_offset=5)

        assert height == 0
        assert grid_list._card_rects == []

    def test_single_column_list_mode(self):
        from melvil.ui import grid_list
        from melvil.ui.grid_list import draw_grid

        items = [_make_item(f"id-{i}", f"Item {i}", "MESH") for i in range(4)]
        draw_grid(_make_region(), items, cols=1, rows_visible=4)

        # All items in column 0 — same x value.
        xs = [r[0] for r in grid_list._card_rects]
        assert len(set(xs)) == 1

    def test_blf_draw_called_for_each_visible_item(self):
        import blf
        from melvil.ui.grid_list import draw_grid

        blf.draw.reset_mock()
        items = [_make_item(f"id-{i}", f"Item {i}", "MESH") for i in range(3)]
        draw_grid(_make_region(), items, cols=3, rows_visible=4)

        # 3 blf.draw calls per item: name + type label + button label
        assert blf.draw.call_count == 9

    def test_card_rects_store_item_id_not_index(self):
        from melvil.ui import grid_list
        from melvil.ui.grid_list import draw_grid

        items = [_make_item("uuid-abc", "My Asset", "MATERIAL")]
        draw_grid(_make_region(), items, cols=1, rows_visible=4)

        assert grid_list._card_rects[0][4] == "uuid-abc"

    def test_offset_x_shifts_cards_right(self):
        from melvil.ui import grid_list
        from melvil.ui.grid_list import draw_grid, GRID_ORIGIN_X

        items = [_make_item("id-0", "Item", "MESH")]
        draw_grid(_make_region(), items, cols=1, rows_visible=4, offset_x=50)

        x = grid_list._card_rects[0][0]
        assert x == 50 + GRID_ORIGIN_X

    def test_offset_y_shifts_cards_down(self):
        from melvil.ui import grid_list
        from melvil.ui.grid_list import (
            draw_grid, GRID_ORIGIN_Y, CARD_H, CARD_GAP,
        )

        region = _make_region(height=600)
        items = [_make_item("id-0", "Item", "MESH")]

        draw_grid(region, items, cols=1, rows_visible=4, offset_y=40)
        y_with_offset = grid_list._card_rects[0][1]

        draw_grid(region, items, cols=1, rows_visible=4, offset_y=0)
        y_no_offset = grid_list._card_rects[0][1]

        assert y_with_offset == y_no_offset - 40


class TestGetRegionOffsets:
    def test_tools_region_sets_offset_x(self):
        from melvil.ops.open_test_grid import _get_region_offsets

        tools = MagicMock()
        tools.type = "TOOLS"
        tools.width = 64
        window = MagicMock()
        window.type = "WINDOW"
        area = MagicMock()
        area.regions = [window, tools]

        ox, oy = _get_region_offsets(area)
        assert ox == 64
        assert oy == 0

    def test_header_regions_set_offset_y(self):
        from melvil.ops.open_test_grid import _get_region_offsets

        header = MagicMock()
        header.type = "HEADER"
        header.height = 26
        tool_header = MagicMock()
        tool_header.type = "TOOL_HEADER"
        tool_header.height = 30
        area = MagicMock()
        area.regions = [header, tool_header]

        ox, oy = _get_region_offsets(area)
        assert ox == 0
        assert oy == 56

    def test_combined_offsets(self):
        from melvil.ops.open_test_grid import _get_region_offsets

        tools = MagicMock()
        tools.type = "TOOLS"
        tools.width = 48
        header = MagicMock()
        header.type = "HEADER"
        header.height = 26
        area = MagicMock()
        area.regions = [tools, header]

        ox, oy = _get_region_offsets(area)
        assert ox == 48
        assert oy == 26


# ---------------------------------------------------------------------------
# compute_max_offset
# ---------------------------------------------------------------------------


class TestComputeMaxOffset:
    def test_zero_items(self):
        from melvil.ui.grid_list import compute_max_offset

        assert compute_max_offset(0, 3, 4) == 0

    def test_exact_fit(self):
        from melvil.ui.grid_list import compute_max_offset

        # 12 items, 3 cols → 4 rows; 4 visible → max_offset = 0
        assert compute_max_offset(12, 3, 4) == 0

    def test_one_extra_item(self):
        from melvil.ui.grid_list import compute_max_offset

        # 13 items, 3 cols → 5 rows; 4 visible → max_offset = 1
        assert compute_max_offset(13, 3, 4) == 1

    def test_many_items(self):
        from melvil.ui.grid_list import compute_max_offset

        # 30 items, 3 cols → 10 rows; 4 visible → max_offset = 6
        assert compute_max_offset(30, 3, 4) == 6

    def test_fewer_than_one_page(self):
        from melvil.ui.grid_list import compute_max_offset

        # 5 items, 3 cols → 2 rows; 4 visible → fits, max_offset = 0
        assert compute_max_offset(5, 3, 4) == 0

    def test_single_column(self):
        from melvil.ui.grid_list import compute_max_offset

        # 10 items, 1 col → 10 rows; 4 visible → max_offset = 6
        assert compute_max_offset(10, 1, 4) == 6

    def test_zero_cols_returns_zero(self):
        from melvil.ui.grid_list import compute_max_offset

        assert compute_max_offset(10, 0, 4) == 0

    def test_zero_rows_visible_returns_zero(self):
        from melvil.ui.grid_list import compute_max_offset

        assert compute_max_offset(10, 3, 0) == 0


# ---------------------------------------------------------------------------
# hit_test
# ---------------------------------------------------------------------------


class TestHitTest:
    def test_hit_inside_card(self):
        from melvil.ui import grid_list
        from melvil.ui.grid_list import hit_test

        grid_list._card_rects = [
            (10, 100, 120, 80, "id-abc"),
            (136, 100, 120, 80, "id-def"),
        ]

        result = hit_test(50, 120)
        assert result == ("id-abc", 0)

    def test_hit_second_card(self):
        from melvil.ui import grid_list
        from melvil.ui.grid_list import hit_test

        grid_list._card_rects = [
            (10, 100, 120, 80, "id-abc"),
            (136, 100, 120, 80, "id-def"),
        ]

        result = hit_test(200, 120)
        assert result == ("id-def", 1)

    def test_miss_in_gap(self):
        from melvil.ui import grid_list
        from melvil.ui.grid_list import hit_test

        grid_list._card_rects = [
            (10, 100, 120, 80, "id-abc"),
            (136, 100, 120, 80, "id-def"),
        ]

        # X=132 is in the gap between cards.
        result = hit_test(132, 120)
        assert result is None

    def test_miss_outside_grid(self):
        from melvil.ui import grid_list
        from melvil.ui.grid_list import hit_test

        grid_list._card_rects = [
            (10, 100, 120, 80, "id-abc"),
        ]

        result = hit_test(500, 500)
        assert result is None

    def test_empty_card_rects(self):
        from melvil.ui import grid_list
        from melvil.ui.grid_list import hit_test

        grid_list._card_rects = []

        result = hit_test(50, 50)
        assert result is None

    def test_returns_slot_index_not_real_index(self):
        from melvil.ui import grid_list
        from melvil.ui.grid_list import hit_test

        grid_list._card_rects = [
            (10, 100, 120, 80, "id-third"),
        ]

        # Even though this is the "third" item, it's the first card rect
        # so slot_index should be 0.
        result = hit_test(50, 120)
        assert result == ("id-third", 0)


# ---------------------------------------------------------------------------
# is_over_grid
# ---------------------------------------------------------------------------


class TestIsOverGrid:
    def test_inside_grid(self):
        from melvil.ui import grid_list
        from melvil.ui.grid_list import is_over_grid

        grid_list._card_rects = [
            (10, 100, 120, 80, "id-0"),
            (136, 100, 120, 80, "id-1"),
        ]

        assert is_over_grid(50, 140) is True

    def test_outside_grid(self):
        from melvil.ui import grid_list
        from melvil.ui.grid_list import is_over_grid

        grid_list._card_rects = [
            (10, 100, 120, 80, "id-0"),
        ]

        assert is_over_grid(500, 500) is False

    def test_empty_card_rects(self):
        from melvil.ui import grid_list
        from melvil.ui.grid_list import is_over_grid

        grid_list._card_rects = []

        assert is_over_grid(50, 50) is False

    def test_on_edge(self):
        from melvil.ui import grid_list
        from melvil.ui.grid_list import is_over_grid

        grid_list._card_rects = [
            (10, 100, 120, 80, "id-0"),
        ]

        # Exactly on the boundary should be considered "over".
        assert is_over_grid(10, 100) is True
        assert is_over_grid(130, 180) is True


# ---------------------------------------------------------------------------
# draw_grid selection / hover color switching
# ---------------------------------------------------------------------------


class TestDrawGridSelectionAndHover:
    def _get_draw_rect_colors(self):
        """Return the list of *color* args passed to draw_rect calls."""
        import gpu
        shader_mock = gpu.shader.from_builtin.return_value
        calls = shader_mock.uniform_float.call_args_list
        return [c.args[1] for c in calls if c.args[0] == "color"]

    def test_selected_card_uses_selected_color(self):
        import gpu
        from melvil.ui.grid_list import (
            draw_grid, COLOR_CARD_SELECTED, COLOR_CARD_BG,
        )

        gpu.shader.from_builtin.return_value.uniform_float.reset_mock()

        items = [
            _make_item("id-sel", "Selected", "MESH"),
            _make_item("id-other", "Other", "MESH"),
        ]
        draw_grid(_make_region(), items, cols=2, rows_visible=4, selected_id="id-sel")

        colors = self._get_draw_rect_colors()
        # First draw_rect call is the background panel; cards start from index 1.
        # Per card: bg, border, preview placeholder, button bg = 4 color calls.
        # Card 0 (selected) should use COLOR_CARD_SELECTED.
        assert colors[1] == COLOR_CARD_SELECTED
        # Card 1 (not selected) should use COLOR_CARD_BG.
        assert colors[5] == COLOR_CARD_BG

    def test_hovered_card_uses_hover_color(self):
        import gpu
        from melvil.ui.grid_list import (
            draw_grid, COLOR_CARD_HOVER, COLOR_CARD_BG,
        )

        gpu.shader.from_builtin.return_value.uniform_float.reset_mock()

        items = [
            _make_item("id-0", "First", "MESH"),
            _make_item("id-1", "Second", "MESH"),
        ]
        draw_grid(_make_region(), items, cols=2, rows_visible=4, hovered_index=1)

        colors = self._get_draw_rect_colors()
        # Per card: bg, border, preview placeholder, button bg = 4 color calls.
        # Card 0 (not hovered) → COLOR_CARD_BG
        assert colors[1] == COLOR_CARD_BG
        # Card 1 (hovered) → COLOR_CARD_HOVER
        assert colors[5] == COLOR_CARD_HOVER

    def test_selected_takes_priority_over_hovered(self):
        import gpu
        from melvil.ui.grid_list import draw_grid, COLOR_CARD_SELECTED

        gpu.shader.from_builtin.return_value.uniform_float.reset_mock()

        items = [_make_item("id-both", "Both", "MESH")]
        draw_grid(
            _make_region(), items, cols=1, rows_visible=4,
            selected_id="id-both", hovered_index=0,
        )

        colors = self._get_draw_rect_colors()
        # The card is both selected and hovered — selected wins.
        assert colors[1] == COLOR_CARD_SELECTED

    def test_no_selection_or_hover_uses_default(self):
        import gpu
        from melvil.ui.grid_list import draw_grid, COLOR_CARD_BG

        gpu.shader.from_builtin.return_value.uniform_float.reset_mock()

        items = [_make_item("id-0", "Plain", "MESH")]
        draw_grid(_make_region(), items, cols=1, rows_visible=4)

        colors = self._get_draw_rect_colors()
        assert colors[1] == COLOR_CARD_BG


# ---------------------------------------------------------------------------
# draw_texture
# ---------------------------------------------------------------------------


class TestDrawTexture:
    def test_calls_image_shader(self):
        import gpu
        from melvil.ui.grid_list import draw_texture

        gpu.shader.from_builtin.reset_mock()
        texture = MagicMock()
        draw_texture(texture, 10, 20, 100, 80)

        gpu.shader.from_builtin.assert_called_with('IMAGE')

    def test_binds_texture_uniform(self):
        import gpu
        from melvil.ui.grid_list import draw_texture

        shader_mock = gpu.shader.from_builtin.return_value
        shader_mock.uniform_sampler.reset_mock()

        texture = MagicMock()
        draw_texture(texture, 10, 20, 100, 80)

        shader_mock.uniform_sampler.assert_called_with("image", texture)


# ---------------------------------------------------------------------------
# draw_grid preview support
# ---------------------------------------------------------------------------


class TestDrawGridPreviews:
    def test_callback_called_for_each_visible_item(self):
        from melvil.ui.grid_list import draw_grid

        items = [_make_item(f"id-{i}", f"Item {i}", "MESH") for i in range(3)]
        callback = MagicMock(return_value=None)
        draw_grid(
            _make_region(), items, cols=3, rows_visible=4,
            get_preview_texture=callback,
        )

        assert callback.call_count == 3
        for i, call_args in enumerate(callback.call_args_list):
            assert call_args.args[0] == items[i]

    def test_preview_texture_drawn_when_callback_returns_texture(self):
        import gpu
        from melvil.ui.grid_list import draw_grid

        gpu.shader.from_builtin.reset_mock()
        texture = MagicMock()
        callback = MagicMock(return_value=texture)
        items = [_make_item("id-0", "Item", "MESH")]
        draw_grid(
            _make_region(), items, cols=1, rows_visible=4,
            get_preview_texture=callback,
        )

        # IMAGE shader should have been used for the preview.
        builtin_calls = [c.args[0] for c in gpu.shader.from_builtin.call_args_list]
        assert 'IMAGE' in builtin_calls

    def test_placeholder_drawn_when_callback_returns_none(self):
        import gpu
        from melvil.ui.grid_list import draw_grid, COLOR_PREVIEW_BG

        gpu.shader.from_builtin.return_value.uniform_float.reset_mock()
        callback = MagicMock(return_value=None)
        items = [_make_item("id-0", "Item", "MESH")]
        draw_grid(
            _make_region(), items, cols=1, rows_visible=4,
            get_preview_texture=callback,
        )

        colors = [
            c.args[1]
            for c in gpu.shader.from_builtin.return_value.uniform_float.call_args_list
            if c.args[0] == "color"
        ]
        assert COLOR_PREVIEW_BG in colors

    def test_placeholder_drawn_when_no_callback(self):
        import gpu
        from melvil.ui.grid_list import draw_grid, COLOR_PREVIEW_BG

        gpu.shader.from_builtin.return_value.uniform_float.reset_mock()
        items = [_make_item("id-0", "Item", "MESH")]
        draw_grid(_make_region(), items, cols=1, rows_visible=4)

        colors = [
            c.args[1]
            for c in gpu.shader.from_builtin.return_value.uniform_float.call_args_list
            if c.args[0] == "color"
        ]
        assert COLOR_PREVIEW_BG in colors

    def test_callback_not_called_for_offscreen_items(self):
        from melvil.ui.grid_list import draw_grid

        items = [_make_item(f"id-{i}", f"Item {i}", "MESH") for i in range(12)]
        callback = MagicMock(return_value=None)
        # cols=3, rows_visible=2 → 6 visible items, scroll_offset=0
        draw_grid(
            _make_region(), items, cols=3, rows_visible=2,
            get_preview_texture=callback,
        )

        assert callback.call_count == 6


# ---------------------------------------------------------------------------
# List mode (cols=1)
# ---------------------------------------------------------------------------


class TestDrawGridListMode:
    def test_list_card_height_uses_list_card_h(self):
        from melvil.ui import grid_list
        from melvil.ui.grid_list import draw_grid, LIST_CARD_H, CARD_GAP, GRID_ORIGIN_Y

        items = [_make_item(f"id-{i}", f"Item {i}", "MESH") for i in range(4)]
        height = draw_grid(_make_region(), items, cols=1, rows_visible=10)

        expected = 4 * (LIST_CARD_H + CARD_GAP) + GRID_ORIGIN_Y * 2
        assert height == expected

    def test_list_card_width_matches_grid_panel(self):
        from melvil.ui import grid_list
        from melvil.ui.grid_list import draw_grid, CARD_W, CARD_GAP

        items = [_make_item("id-0", "Item", "MESH")]
        draw_grid(_make_region(), items, cols=1, rows_visible=4)

        # Default grid_cols_for_width = 3 in list mode
        expected_w = 3 * (CARD_W + CARD_GAP) - CARD_GAP
        assert grid_list._card_rects[0][2] == expected_w

    def test_list_all_cards_same_column(self):
        from melvil.ui import grid_list
        from melvil.ui.grid_list import draw_grid

        items = [_make_item(f"id-{i}", f"Item {i}", "MESH") for i in range(5)]
        draw_grid(_make_region(), items, cols=1, rows_visible=10)

        xs = [r[0] for r in grid_list._card_rects]
        assert len(set(xs)) == 1

    def test_list_blf_draws_two_calls_per_item(self):
        import blf
        from melvil.ui.grid_list import draw_grid

        blf.draw.reset_mock()
        items = [_make_item(f"id-{i}", f"Item {i}", "MESH") for i in range(3)]
        draw_grid(_make_region(), items, cols=1, rows_visible=10)

        # 3 blf.draw calls per item: name + type label + button label
        assert blf.draw.call_count == 9

    def test_list_preview_callback_called(self):
        from melvil.ui.grid_list import draw_grid

        items = [_make_item("id-0", "Item", "MESH")]
        callback = MagicMock(return_value=None)
        draw_grid(
            _make_region(), items, cols=1, rows_visible=4,
            get_preview_texture=callback,
        )

        callback.assert_called_once_with(items[0])

    def test_list_placeholder_when_no_texture(self):
        import gpu
        from melvil.ui.grid_list import draw_grid, COLOR_PREVIEW_BG

        gpu.shader.from_builtin.return_value.uniform_float.reset_mock()
        items = [_make_item("id-0", "Item", "MESH")]
        draw_grid(_make_region(), items, cols=1, rows_visible=4)

        colors = [
            c.args[1]
            for c in gpu.shader.from_builtin.return_value.uniform_float.call_args_list
            if c.args[0] == "color"
        ]
        assert COLOR_PREVIEW_BG in colors

    def test_grid_mode_uses_full_card_h(self):
        from melvil.ui.grid_list import draw_grid, CARD_H, CARD_GAP, GRID_ORIGIN_Y

        items = [_make_item(f"id-{i}", f"Item {i}", "MESH") for i in range(4)]
        height = draw_grid(_make_region(), items, cols=2, rows_visible=10)

        # 4 items / 2 cols = 2 rows
        expected = 2 * (CARD_H + CARD_GAP) + GRID_ORIGIN_Y * 2
        assert height == expected

    def test_grid_card_width_is_card_w(self):
        from melvil.ui import grid_list
        from melvil.ui.grid_list import draw_grid, CARD_W

        items = [_make_item("id-0", "Item", "MESH")]
        draw_grid(_make_region(), items, cols=3, rows_visible=4)

        assert grid_list._card_rects[0][2] == CARD_W


# ---------------------------------------------------------------------------
# Button rects & button_hit_test
# ---------------------------------------------------------------------------


class TestDrawGridButtons:
    def test_button_rects_populated_per_visible_item(self):
        from melvil.ui import grid_list
        from melvil.ui.grid_list import draw_grid

        items = [_make_item(f"id-{i}", f"Item {i}", "MESH") for i in range(6)]
        draw_grid(_make_region(), items, cols=3, rows_visible=4)

        assert len(grid_list._button_rects) == 6
        ids = [r[4] for r in grid_list._button_rects]
        assert ids == [f"id-{i}" for i in range(6)]

    def test_button_rects_cleared_on_empty(self):
        from melvil.ui import grid_list
        from melvil.ui.grid_list import draw_grid

        grid_list._button_rects = [("stale",)]
        draw_grid(_make_region(), [], cols=3, rows_visible=4)

        assert grid_list._button_rects == []

    def test_button_inside_card_bounds(self):
        from melvil.ui import grid_list
        from melvil.ui.grid_list import draw_grid

        items = [_make_item("id-0", "Item", "MESH")]
        draw_grid(_make_region(), items, cols=1, rows_visible=4)

        card = grid_list._card_rects[0]
        btn = grid_list._button_rects[0]
        cx, cy, cw, ch = card[0], card[1], card[2], card[3]
        bx, by, bw, bh = btn[0], btn[1], btn[2], btn[3]

        assert bx >= cx
        assert by >= cy
        assert bx + bw <= cx + cw
        assert by + bh <= cy + ch

    def test_button_drawn_with_button_bg_color(self):
        import gpu
        from melvil.ui.grid_list import draw_grid, COLOR_BUTTON_BG

        gpu.shader.from_builtin.return_value.uniform_float.reset_mock()
        items = [_make_item("id-0", "Item", "MESH")]
        draw_grid(_make_region(), items, cols=1, rows_visible=4)

        colors = [
            c.args[1]
            for c in gpu.shader.from_builtin.return_value.uniform_float.call_args_list
            if c.args[0] == "color"
        ]
        assert COLOR_BUTTON_BG in colors

    def test_hovered_button_uses_hover_color(self):
        import gpu
        from melvil.ui.grid_list import draw_grid, COLOR_BUTTON_HOVER

        gpu.shader.from_builtin.return_value.uniform_float.reset_mock()
        items = [_make_item("id-0", "Item", "MESH")]
        draw_grid(
            _make_region(), items, cols=1, rows_visible=4,
            hovered_button_index=0,
        )

        colors = [
            c.args[1]
            for c in gpu.shader.from_builtin.return_value.uniform_float.call_args_list
            if c.args[0] == "color"
        ]
        assert COLOR_BUTTON_HOVER in colors

    def test_button_label_drawn(self):
        import blf
        from melvil.ui.grid_list import draw_grid

        blf.draw.reset_mock()
        items = [_make_item("id-0", "Item", "MESH")]
        draw_grid(_make_region(), items, cols=1, rows_visible=4)

        labels = [c.args[1] for c in blf.draw.call_args_list]
        assert "Load" in labels

    def test_button_rects_in_list_mode(self):
        from melvil.ui import grid_list
        from melvil.ui.grid_list import draw_grid

        items = [_make_item(f"id-{i}", f"Item {i}", "MESH") for i in range(3)]
        draw_grid(_make_region(), items, cols=1, rows_visible=10)

        assert len(grid_list._button_rects) == 3


class TestButtonHitTest:
    def test_hit_inside_button(self):
        from melvil.ui import grid_list
        from melvil.ui.grid_list import button_hit_test

        grid_list._button_rects = [
            (20, 100, 100, 20, "id-abc"),
        ]

        result = button_hit_test(50, 110)
        assert result == ("id-abc", 0)

    def test_miss_outside_button(self):
        from melvil.ui import grid_list
        from melvil.ui.grid_list import button_hit_test

        grid_list._button_rects = [
            (20, 100, 100, 20, "id-abc"),
        ]

        result = button_hit_test(5, 5)
        assert result is None

    def test_empty_button_rects(self):
        from melvil.ui import grid_list
        from melvil.ui.grid_list import button_hit_test

        grid_list._button_rects = []

        result = button_hit_test(50, 50)
        assert result is None

    def test_hit_correct_button_among_many(self):
        from melvil.ui import grid_list
        from melvil.ui.grid_list import button_hit_test

        grid_list._button_rects = [
            (20, 100, 100, 20, "id-first"),
            (20, 200, 100, 20, "id-second"),
        ]

        result = button_hit_test(50, 210)
        assert result == ("id-second", 1)
