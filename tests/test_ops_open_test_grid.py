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
        mod._draw_state["items"] = [{"id": "x", "name": "x", "type": "MESH"}]
        bpy.types.SpaceView3D.draw_handler_remove.reset_mock()

    def test_esc_cancels_and_cleans_up(self):
        from melvil.ops.open_test_grid import (
            MELVIL_OT_open_test_grid,
            _draw_state,
        )

        op = MELVIL_OT_open_test_grid()
        ctx = MagicMock()
        event = MagicMock()
        event.type = "ESC"

        result = op.modal(ctx, event)

        assert result == {"CANCELLED"}
        bpy.types.SpaceView3D.draw_handler_remove.assert_called_once()
        assert _draw_state["active"] is False

    def test_rightmouse_cancels(self):
        from melvil.ops.open_test_grid import MELVIL_OT_open_test_grid

        op = MELVIL_OT_open_test_grid()
        ctx = MagicMock()
        event = MagicMock()
        event.type = "RIGHTMOUSE"

        result = op.modal(ctx, event)

        assert result == {"CANCELLED"}

    def test_other_events_pass_through(self):
        from melvil.ops.open_test_grid import MELVIL_OT_open_test_grid

        op = MELVIL_OT_open_test_grid()
        ctx = MagicMock()
        event = MagicMock()
        event.type = "MOUSEMOVE"

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
