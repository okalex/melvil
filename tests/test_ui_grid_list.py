"""Tests for ui/gpu/grid_list.py — GPU grid/list widget helpers."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# compute_max_offset
# ---------------------------------------------------------------------------


class TestComputeMaxOffset:
    def test_zero_items(self):
        from blammo.ui.gpu.grid_list import compute_max_offset

        assert compute_max_offset(0, 3, 4) == 0

    def test_exact_fit(self):
        from blammo.ui.gpu.grid_list import compute_max_offset

        # 12 items, 3 cols → 4 rows; 4 visible → max_offset = 0
        assert compute_max_offset(12, 3, 4) == 0

    def test_one_extra_item(self):
        from blammo.ui.gpu.grid_list import compute_max_offset

        # 13 items, 3 cols → 5 rows; 4 visible → max_offset = 1
        assert compute_max_offset(13, 3, 4) == 1

    def test_many_items(self):
        from blammo.ui.gpu.grid_list import compute_max_offset

        # 30 items, 3 cols → 10 rows; 4 visible → max_offset = 6
        assert compute_max_offset(30, 3, 4) == 6

    def test_fewer_than_one_page(self):
        from blammo.ui.gpu.grid_list import compute_max_offset

        # 5 items, 3 cols → 2 rows; 4 visible → fits, max_offset = 0
        assert compute_max_offset(5, 3, 4) == 0

    def test_single_column(self):
        from blammo.ui.gpu.grid_list import compute_max_offset

        # 10 items, 1 col → 10 rows; 4 visible → max_offset = 6
        assert compute_max_offset(10, 1, 4) == 6

    def test_zero_cols_returns_zero(self):
        from blammo.ui.gpu.grid_list import compute_max_offset

        assert compute_max_offset(10, 0, 4) == 0

    def test_zero_rows_visible_returns_zero(self):
        from blammo.ui.gpu.grid_list import compute_max_offset

        assert compute_max_offset(10, 3, 0) == 0


# ---------------------------------------------------------------------------
# get_region_offsets
# ---------------------------------------------------------------------------


class TestGetRegionOffsets:
    def test_tools_region_sets_offset_x(self):
        from blammo.ui.gpu import get_region_offsets

        tools = MagicMock()
        tools.type = "TOOLS"
        tools.width = 64
        window = MagicMock()
        window.type = "WINDOW"
        area = MagicMock()
        area.regions = [window, tools]

        ox, oy = get_region_offsets(area)
        assert ox == 64
        assert oy == 0

    def test_header_regions_set_offset_y(self):
        from blammo.ui.gpu import get_region_offsets

        header = MagicMock()
        header.type = "HEADER"
        header.height = 26
        tool_header = MagicMock()
        tool_header.type = "TOOL_HEADER"
        tool_header.height = 30
        area = MagicMock()
        area.regions = [header, tool_header]

        ox, oy = get_region_offsets(area)
        assert ox == 0
        assert oy == 56

    def test_combined_offsets(self):
        from blammo.ui.gpu import get_region_offsets

        tools = MagicMock()
        tools.type = "TOOLS"
        tools.width = 48
        header = MagicMock()
        header.type = "HEADER"
        header.height = 26
        area = MagicMock()
        area.regions = [tools, header]

        ox, oy = get_region_offsets(area)
        assert ox == 48
        assert oy == 26
