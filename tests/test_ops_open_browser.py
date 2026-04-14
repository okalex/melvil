"""Tests for ops/open_browser.py — MELVIL_OT_open_browser viewport browser."""

from __future__ import annotations

from unittest.mock import MagicMock

import bpy
import pytest


class TestMetadata:
    def test_bl_idname(self):
        from melvil.ops.open_browser import MELVIL_OT_open_browser

        assert MELVIL_OT_open_browser.bl_idname == "melvil.open_browser"

    def test_bl_label(self):
        from melvil.ops.open_browser import MELVIL_OT_open_browser

        assert MELVIL_OT_open_browser.bl_label == "Melvil Browser (GPU)"

    def test_bl_options_contains_internal(self):
        from melvil.ops.open_browser import MELVIL_OT_open_browser

        assert "INTERNAL" in MELVIL_OT_open_browser.bl_options


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


class TestInvoke:
    def setup_method(self):
        bpy.types.SpaceView3D.draw_handler_add.reset_mock()
        bpy.types.SpaceView3D.draw_handler_remove.reset_mock()

    def test_invoke_creates_panel_and_attaches(self):
        from melvil.ops.open_browser import MELVIL_OT_open_browser

        op = MELVIL_OT_open_browser()
        ctx = MagicMock()
        ctx.area.type = "VIEW_3D"
        event = MagicMock()

        result = op.invoke(ctx, event)

        assert result == {"RUNNING_MODAL"}
        assert op._panel is not None
        bpy.types.SpaceView3D.draw_handler_add.assert_called_once()
        ctx.window_manager.modal_handler_add.assert_called_once_with(op)

    def test_invoke_tags_redraw(self):
        from melvil.ops.open_browser import MELVIL_OT_open_browser

        op = MELVIL_OT_open_browser()
        ctx = MagicMock()
        event = MagicMock()

        op.invoke(ctx, event)
        ctx.area.tag_redraw.assert_called()


class TestModal:
    def _make_op(self):
        from melvil.ops.open_browser import MELVIL_OT_open_browser

        op = MELVIL_OT_open_browser()
        ctx = MagicMock()
        ctx.area.type = "VIEW_3D"
        op.invoke(ctx, MagicMock())
        return op, ctx

    def test_esc_cancels(self):
        op, ctx = self._make_op()
        event = MagicMock()
        event.type = "ESC"
        event.value = "PRESS"

        result = op.modal(ctx, event)
        assert result == {"CANCELLED"}
        assert op._panel is None

    def test_rightmouse_cancels(self):
        op, ctx = self._make_op()
        event = MagicMock()
        event.type = "RIGHTMOUSE"
        event.value = "PRESS"

        result = op.modal(ctx, event)
        assert result == {"CANCELLED"}

    def test_click_outside_cancels(self):
        op, ctx = self._make_op()
        # Panel has no rect yet (empty build), so is_inside returns False.
        event = MagicMock()
        event.type = "LEFTMOUSE"
        event.value = "PRESS"
        event.mouse_region_x = 9999
        event.mouse_region_y = 9999

        result = op.modal(ctx, event)
        assert result == {"CANCELLED"}

    def test_other_events_pass_through(self):
        op, ctx = self._make_op()
        event = MagicMock()
        event.type = "MOUSEMOVE"
        event.value = "NOTHING"

        result = op.modal(ctx, event)
        assert result == {"RUNNING_MODAL"}


class TestCancel:
    def setup_method(self):
        bpy.types.SpaceView3D.draw_handler_add.reset_mock()
        bpy.types.SpaceView3D.draw_handler_remove.reset_mock()

    def test_cancel_detaches_panel(self):
        from melvil.ops.open_browser import MELVIL_OT_open_browser

        op = MELVIL_OT_open_browser()
        ctx = MagicMock()
        op.invoke(ctx, MagicMock())

        op.cancel(ctx)
        assert op._panel is None
        bpy.types.SpaceView3D.draw_handler_remove.assert_called_once()

    def test_cancel_without_invoke_is_safe(self):
        from melvil.ops.open_browser import MELVIL_OT_open_browser

        op = MELVIL_OT_open_browser()
        ctx = MagicMock()
        op.cancel(ctx)  # should not raise
