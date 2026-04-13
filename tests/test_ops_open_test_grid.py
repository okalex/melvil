"""Tests for ops/open_test_grid.py — MELVIL_OT_open_test_grid viewport overlay."""

from __future__ import annotations

from unittest.mock import MagicMock

import bpy
import pytest


class TestMetadata:
    def test_bl_idname(self):
        from melvil.ops.open_test_grid import MELVIL_OT_open_test_grid

        assert MELVIL_OT_open_test_grid.bl_idname == "melvil.open_test_grid"

    def test_bl_label(self):
        from melvil.ops.open_test_grid import MELVIL_OT_open_test_grid

        assert MELVIL_OT_open_test_grid.bl_label == "Melvil Grid Test"

    def test_bl_options_contains_register(self):
        from melvil.ops.open_test_grid import MELVIL_OT_open_test_grid

        assert "REGISTER" in MELVIL_OT_open_test_grid.bl_options


class TestPoll:
    def test_returns_true_in_view3d(self):
        from melvil.ops.open_test_grid import MELVIL_OT_open_test_grid

        ctx = MagicMock()
        ctx.area.type = "VIEW_3D"
        assert MELVIL_OT_open_test_grid.poll(ctx) is True

    def test_returns_false_outside_view3d(self):
        from melvil.ops.open_test_grid import MELVIL_OT_open_test_grid

        ctx = MagicMock()
        ctx.area.type = "NODE_EDITOR"
        assert MELVIL_OT_open_test_grid.poll(ctx) is False

    def test_returns_false_when_no_area(self):
        from melvil.ops.open_test_grid import MELVIL_OT_open_test_grid

        ctx = MagicMock()
        ctx.area = None
        assert MELVIL_OT_open_test_grid.poll(ctx) is False


class TestInvoke:
    def setup_method(self):
        # Reset module-level draw state before each test.
        import melvil.ops.open_test_grid as mod
        mod._draw_handle = None
        mod._draw_state["active"] = False
        mod._draw_state["items"] = []
        bpy.types.SpaceView3D.draw_handler_add.reset_mock()

    def test_invoke_registers_draw_handler(self):
        from melvil.ops.open_test_grid import MELVIL_OT_open_test_grid

        op = MELVIL_OT_open_test_grid()
        ctx = MagicMock()
        ctx.area.type = "VIEW_3D"
        event = MagicMock()

        result = op.invoke(ctx, event)

        bpy.types.SpaceView3D.draw_handler_add.assert_called_once()
        assert result == {"RUNNING_MODAL"}

    def test_invoke_adds_modal_handler(self):
        from melvil.ops.open_test_grid import MELVIL_OT_open_test_grid

        op = MELVIL_OT_open_test_grid()
        ctx = MagicMock()
        event = MagicMock()

        op.invoke(ctx, event)

        ctx.window_manager.modal_handler_add.assert_called_once_with(op)

    def test_invoke_populates_draw_state(self):
        from melvil.ops.open_test_grid import (
            MELVIL_OT_open_test_grid,
            _draw_state,
        )

        op = MELVIL_OT_open_test_grid()
        ctx = MagicMock()
        event = MagicMock()

        op.invoke(ctx, event)

        assert _draw_state["active"] is True
        assert len(_draw_state["items"]) == 30

    def test_fake_items_have_required_keys(self):
        from melvil.ops.open_test_grid import (
            MELVIL_OT_open_test_grid,
            _draw_state,
        )

        op = MELVIL_OT_open_test_grid()
        ctx = MagicMock()
        event = MagicMock()

        op.invoke(ctx, event)

        for item in _draw_state["items"]:
            assert "id" in item
            assert "name" in item
            assert "type" in item
            assert item["type"] in ("MATERIAL", "MESH", "NODE_GROUP")


class TestModal:
    def setup_method(self):
        import melvil.ops.open_test_grid as mod
        mod._draw_handle = "FAKE_HANDLE"
        mod._draw_state["active"] = True
        mod._draw_state["items"] = [
            {"id": f"id-{i}", "name": f"Item {i}", "type": "MESH"}
            for i in range(30)
        ]
        bpy.types.SpaceView3D.draw_handler_remove.reset_mock()

    def _make_ctx(self, scroll_offset=0):
        """Build a mock context with a melvil_grid_scroll PropertyGroup stub."""
        ctx = MagicMock()
        scroll_props = MagicMock()
        scroll_props.scroll_offset = scroll_offset
        scroll_props.selected_id = ""
        scroll_props.hovered_index = -1
        ctx.window_manager.melvil_grid_scroll = scroll_props
        ctx.region.x = 0
        ctx.region.y = 0
        return ctx

    def test_esc_cancels_and_cleans_up(self):
        from melvil.ops.open_test_grid import (
            MELVIL_OT_open_test_grid,
            _draw_state,
        )

        op = MELVIL_OT_open_test_grid()
        ctx = self._make_ctx()
        event = MagicMock()
        event.type = "ESC"

        result = op.modal(ctx, event)

        assert result == {"CANCELLED"}
        bpy.types.SpaceView3D.draw_handler_remove.assert_called_once()
        assert _draw_state["active"] is False

    def test_rightmouse_cancels(self):
        from melvil.ops.open_test_grid import MELVIL_OT_open_test_grid

        op = MELVIL_OT_open_test_grid()
        ctx = self._make_ctx()
        event = MagicMock()
        event.type = "RIGHTMOUSE"

        result = op.modal(ctx, event)

        assert result == {"CANCELLED"}

    def test_other_events_pass_through(self):
        from melvil.ops.open_test_grid import MELVIL_OT_open_test_grid

        op = MELVIL_OT_open_test_grid()
        ctx = self._make_ctx()
        event = MagicMock()
        event.type = "MOUSEMOVE"
        event.mouse_x = 0
        event.mouse_y = 0

        result = op.modal(ctx, event)

        assert result == {"PASS_THROUGH"}

    def test_wheelup_over_grid_decrements_scroll(self):
        from melvil.ops.open_test_grid import MELVIL_OT_open_test_grid
        import melvil.ui.grid_list as grid_list

        # Seed _card_rects so is_over_grid returns True at (50, 50).
        grid_list._card_rects = [(0, 0, 200, 200, "id-0")]

        ctx = self._make_ctx(scroll_offset=2)
        op = MELVIL_OT_open_test_grid()
        event = MagicMock()
        event.type = "WHEELUPMOUSE"
        event.mouse_x = 50
        event.mouse_y = 50

        result = op.modal(ctx, event)

        assert result == {"RUNNING_MODAL"}
        assert ctx.window_manager.melvil_grid_scroll.scroll_offset == 1

    def test_wheelup_clamps_at_zero(self):
        from melvil.ops.open_test_grid import MELVIL_OT_open_test_grid
        import melvil.ui.grid_list as grid_list

        grid_list._card_rects = [(0, 0, 200, 200, "id-0")]

        ctx = self._make_ctx(scroll_offset=0)
        op = MELVIL_OT_open_test_grid()
        event = MagicMock()
        event.type = "WHEELUPMOUSE"
        event.mouse_x = 50
        event.mouse_y = 50

        op.modal(ctx, event)

        assert ctx.window_manager.melvil_grid_scroll.scroll_offset == 0

    def test_wheeldown_over_grid_increments_scroll(self):
        from melvil.ops.open_test_grid import MELVIL_OT_open_test_grid
        import melvil.ui.grid_list as grid_list

        grid_list._card_rects = [(0, 0, 200, 200, "id-0")]

        ctx = self._make_ctx(scroll_offset=0)
        op = MELVIL_OT_open_test_grid()
        event = MagicMock()
        event.type = "WHEELDOWNMOUSE"
        event.mouse_x = 50
        event.mouse_y = 50

        result = op.modal(ctx, event)

        assert result == {"RUNNING_MODAL"}
        assert ctx.window_manager.melvil_grid_scroll.scroll_offset == 1

    def test_wheeldown_clamps_at_max_offset(self):
        from melvil.ops.open_test_grid import MELVIL_OT_open_test_grid
        import melvil.ui.grid_list as grid_list

        grid_list._card_rects = [(0, 0, 200, 200, "id-0")]

        # 30 items, 3 cols, 4 visible rows → max_offset = ceil(30/3) - 4 = 6
        ctx = self._make_ctx(scroll_offset=6)
        op = MELVIL_OT_open_test_grid()
        event = MagicMock()
        event.type = "WHEELDOWNMOUSE"
        event.mouse_x = 50
        event.mouse_y = 50

        op.modal(ctx, event)

        assert ctx.window_manager.melvil_grid_scroll.scroll_offset == 6

    def test_wheel_outside_grid_passes_through(self):
        from melvil.ops.open_test_grid import MELVIL_OT_open_test_grid
        import melvil.ui.grid_list as grid_list

        # No card rects → cursor can't be over grid.
        grid_list._card_rects = []

        ctx = self._make_ctx(scroll_offset=0)
        op = MELVIL_OT_open_test_grid()
        event = MagicMock()
        event.type = "WHEELDOWNMOUSE"
        event.mouse_x = 50
        event.mouse_y = 50

        result = op.modal(ctx, event)

        assert result == {"PASS_THROUGH"}


class TestGenerateFakeItems:
    def test_default_count(self):
        from melvil.ops.open_test_grid import _generate_fake_items

        items = _generate_fake_items()
        assert len(items) == 30

    def test_custom_count(self):
        from melvil.ops.open_test_grid import _generate_fake_items

        items = _generate_fake_items(5)
        assert len(items) == 5

    def test_ids_are_unique(self):
        from melvil.ops.open_test_grid import _generate_fake_items

        items = _generate_fake_items(30)
        ids = [item["id"] for item in items]
        assert len(set(ids)) == 30

    def test_types_cycle(self):
        from melvil.ops.open_test_grid import _generate_fake_items

        items = _generate_fake_items(6)
        types = [item["type"] for item in items]
        assert types == [
            "MATERIAL", "MESH", "NODE_GROUP",
            "MATERIAL", "MESH", "NODE_GROUP",
        ]
