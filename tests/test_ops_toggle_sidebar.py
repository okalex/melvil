"""Tests for ops/toggle_sidebar.py — BLAMMO_OT_toggle_sidebar."""

from __future__ import annotations

from unittest.mock import MagicMock, PropertyMock

import pytest


# ---------------------------------------------------------------------------
# poll()
# ---------------------------------------------------------------------------


class TestPoll:
    def test_returns_true_in_view3d(self):
        from blammo.ops.toggle_sidebar import BLAMMO_OT_toggle_sidebar

        ctx = MagicMock()
        ctx.area.type = "VIEW_3D"
        assert BLAMMO_OT_toggle_sidebar.poll(ctx) is True

    def test_returns_false_outside_view3d(self):
        from blammo.ops.toggle_sidebar import BLAMMO_OT_toggle_sidebar

        for area_type in ("NODE_EDITOR", "IMAGE_EDITOR", "SEQUENCE_EDITOR"):
            ctx = MagicMock()
            ctx.area.type = area_type
            assert BLAMMO_OT_toggle_sidebar.poll(ctx) is False

    def test_returns_false_when_no_area(self):
        from blammo.ops.toggle_sidebar import BLAMMO_OT_toggle_sidebar

        ctx = MagicMock()
        ctx.area = None
        assert BLAMMO_OT_toggle_sidebar.poll(ctx) is False


# ---------------------------------------------------------------------------
# execute()
# ---------------------------------------------------------------------------


class TestExecute:
    def test_returns_finished(self):
        from blammo.ops.toggle_sidebar import BLAMMO_OT_toggle_sidebar

        op = BLAMMO_OT_toggle_sidebar()
        ctx = MagicMock()
        ctx.space_data.show_region_ui = False

        result = op.execute(ctx)
        assert result == {"FINISHED"}

    def test_toggles_show_region_ui_from_false_to_true(self):
        from blammo.ops.toggle_sidebar import BLAMMO_OT_toggle_sidebar

        op = BLAMMO_OT_toggle_sidebar()
        ctx = MagicMock()
        ctx.space_data.show_region_ui = False

        op.execute(ctx)

        assert ctx.space_data.show_region_ui is True

    def test_toggles_show_region_ui_from_true_to_false(self):
        from blammo.ops.toggle_sidebar import BLAMMO_OT_toggle_sidebar

        op = BLAMMO_OT_toggle_sidebar()
        ctx = MagicMock()
        ctx.space_data.show_region_ui = True

        op.execute(ctx)

        assert ctx.space_data.show_region_ui is False


# ---------------------------------------------------------------------------
# bl_idname / metadata
# ---------------------------------------------------------------------------


class TestMetadata:
    def test_bl_idname(self):
        from blammo.ops.toggle_sidebar import BLAMMO_OT_toggle_sidebar

        assert BLAMMO_OT_toggle_sidebar.bl_idname == "blammo.toggle_sidebar"
