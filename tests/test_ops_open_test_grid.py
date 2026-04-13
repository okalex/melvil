"""Tests for ops/open_test_grid.py — MELVIL_OT_open_test_grid test popup."""

from __future__ import annotations

from unittest.mock import MagicMock

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
    def test_invoke_calls_invoke_popup(self):
        from melvil.ops.open_test_grid import MELVIL_OT_open_test_grid

        op = MELVIL_OT_open_test_grid()
        ctx = MagicMock()
        event = MagicMock()
        ctx.window_manager.invoke_popup.return_value = {"RUNNING_MODAL"}

        result = op.invoke(ctx, event)

        ctx.window_manager.invoke_popup.assert_called_once_with(op, width=500)
        assert result == {"RUNNING_MODAL"}

    def test_invoke_populates_items(self):
        from melvil.ops.open_test_grid import MELVIL_OT_open_test_grid

        op = MELVIL_OT_open_test_grid()
        ctx = MagicMock()
        event = MagicMock()
        ctx.window_manager.invoke_popup.return_value = {"RUNNING_MODAL"}

        op.invoke(ctx, event)

        assert len(op._items) == 30

    def test_fake_items_have_required_keys(self):
        from melvil.ops.open_test_grid import MELVIL_OT_open_test_grid

        op = MELVIL_OT_open_test_grid()
        ctx = MagicMock()
        event = MagicMock()
        ctx.window_manager.invoke_popup.return_value = {"RUNNING_MODAL"}

        op.invoke(ctx, event)

        for item in op._items:
            assert "id" in item
            assert "name" in item
            assert "type" in item
            assert item["type"] in ("MATERIAL", "MESH", "NODE_GROUP")


class TestModal:
    def test_modal_returns_pass_through(self):
        from melvil.ops.open_test_grid import MELVIL_OT_open_test_grid

        op = MELVIL_OT_open_test_grid()
        ctx = MagicMock()
        event = MagicMock()

        assert op.modal(ctx, event) == {"PASS_THROUGH"}


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
