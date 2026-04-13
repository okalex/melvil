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

        # 2 blf.draw calls per item: name + type label
        assert blf.draw.call_count == 6

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
