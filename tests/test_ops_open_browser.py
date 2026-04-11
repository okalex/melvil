"""Tests for ops/open_browser.py — MELVIL_OT_open_browser popup."""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest


def _make_asset(id: str, name: str, type: str) -> dict:
    return {"id": id, "name": name, "type": type}


def _make_op():
    from melvil.ops.open_browser import MELVIL_OT_open_browser

    return MELVIL_OT_open_browser()


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
# invoke() — opens popup
# ---------------------------------------------------------------------------


class TestInvoke:
    def test_invoke_calls_invoke_popup(self):
        op = _make_op()
        ctx = MagicMock()
        result = op.invoke(ctx, MagicMock())
        ctx.window_manager.invoke_popup.assert_called_once_with(op, width=400)

    def test_invoke_returns_popup_result(self):
        op = _make_op()
        ctx = MagicMock()
        ctx.window_manager.invoke_popup.return_value = {"RUNNING_MODAL"}
        result = op.invoke(ctx, MagicMock())
        assert result == {"RUNNING_MODAL"}


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
    def test_db_error_shows_error_label(self):
        op = _make_op()
        op.layout = MagicMock()

        with patch("melvil.ops.open_browser.resolve_db_path", side_effect=Exception("boom")):
            op.draw(MagicMock())

        op.layout.label.assert_called()
        icon_calls = [c for c in op.layout.label.call_args_list if c[1].get("icon") == "ERROR"]
        assert icon_calls

    def test_draw_delegates_to_draw_asset_section(self):
        op = _make_op()
        op.layout = MagicMock()

        materials = [_make_asset("m1", "Red", "MATERIAL")]
        meshes = [_make_asset("b1", "Rock", "MESH")]

        with patch("melvil.ops.open_browser.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ops.open_browser.open_db") as mock_open, \
             patch("melvil.ops.open_browser.list_assets", side_effect=[materials, meshes]), \
             patch("melvil.ops.open_browser.draw_asset_section") as mock_draw:
            mock_open.return_value.__enter__ = lambda s: MagicMock()
            mock_open.return_value.__exit__ = MagicMock(return_value=False)
            op.draw(MagicMock())

        assert mock_draw.call_count == 2
        titles = [c[0][1] for c in mock_draw.call_args_list]
        assert "Materials" in titles
        assert "Meshes" in titles
