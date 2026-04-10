"""Tests for ui/panel.py — MELVIL_PT_main and _draw_asset_section."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from unittest.mock import MagicMock, call, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_asset(id: str, name: str, type: str) -> dict:
    """Return a dict that behaves like a sqlite3.Row for panel purposes."""
    return {"id": id, "name": name, "type": type}


def _make_layout():
    return MagicMock()


# ---------------------------------------------------------------------------
# MELVIL_PT_main.poll()
# ---------------------------------------------------------------------------


class TestPoll:
    def test_always_true(self):
        from melvil.ui.panel import MELVIL_PT_main

        assert MELVIL_PT_main.poll(MagicMock()) is True


# ---------------------------------------------------------------------------
# MELVIL_PT_main.draw() — top-level behaviour
# ---------------------------------------------------------------------------


class TestDraw:
    def _panel(self):
        from melvil.ui.panel import MELVIL_PT_main

        return MELVIL_PT_main()

    def test_save_button_always_drawn(self):
        panel = self._panel()
        layout = _make_layout()
        panel.layout = layout
        ctx = MagicMock()

        @contextmanager
        def _cm(_):
            yield MagicMock()

        with patch("melvil.ui.panel.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ui.panel.open_db", side_effect=_cm), \
             patch("melvil.ui.panel.list_assets", return_value=[]):
            panel.draw(ctx)

        layout.operator.assert_called_with(
            "melvil.save_asset", text="Save as Asset", icon="ADD"
        )

    def test_db_error_shows_error_label(self):
        from melvil.ui.panel import MELVIL_PT_main

        panel = MELVIL_PT_main()
        layout = _make_layout()
        panel.layout = layout

        with patch("melvil.ui.panel.resolve_db_path", side_effect=Exception("boom")):
            panel.draw(MagicMock())

        layout.label.assert_called_with(
            text="Could not open library database", icon="ERROR"
        )

    def test_draw_calls_section_for_materials_and_meshes(self):
        from melvil.ui.panel import MELVIL_PT_main

        panel = MELVIL_PT_main()
        layout = _make_layout()
        panel.layout = layout

        mat = _make_asset("aaa", "Red Metal", "MATERIAL")
        mesh = _make_asset("bbb", "Suzanne", "MESH")

        @contextmanager
        def _cm(_):
            yield MagicMock()

        with patch("melvil.ui.panel.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ui.panel.open_db", side_effect=_cm), \
             patch("melvil.ui.panel.list_assets", side_effect=[[mat], [mesh]]), \
             patch("melvil.ui.panel._draw_asset_section") as mock_section:
            panel.draw(MagicMock())

        assert mock_section.call_count == 2
        # First call: Materials
        first_call = mock_section.call_args_list[0]
        assert first_call.args[1] == "Materials"
        assert first_call.args[3] == [mat]
        # Second call: Meshes
        second_call = mock_section.call_args_list[1]
        assert second_call.args[1] == "Meshes"
        assert second_call.args[3] == [mesh]


# ---------------------------------------------------------------------------
# _draw_asset_section()
# ---------------------------------------------------------------------------


class TestDrawAssetSection:
    def test_empty_assets_shows_placeholder(self):
        from melvil.ui.panel import _draw_asset_section

        layout = _make_layout()
        _draw_asset_section(layout, "Materials", "MATERIAL", [])

        box = layout.box.return_value
        box.label.assert_any_call(text="No materials saved yet")

    def test_header_label_uses_title_and_icon(self):
        from melvil.ui.panel import _draw_asset_section

        layout = _make_layout()
        _draw_asset_section(layout, "Meshes", "MESH_DATA", [])

        box = layout.box.return_value
        box.label.assert_any_call(text="Meshes", icon="MESH_DATA")

    def test_each_asset_row_has_load_and_delete_buttons(self):
        from melvil.ui.panel import _draw_asset_section

        layout = _make_layout()
        asset = _make_asset("aaaaaaaa-0000-4000-8000-000000000001", "Red Metal", "MATERIAL")

        _draw_asset_section(layout, "Materials", "MATERIAL", [asset])

        box = layout.box.return_value
        row = box.row.return_value

        operator_calls = [c.args[0] for c in row.operator.call_args_list]
        assert "melvil.load_asset" in operator_calls
        assert "melvil.delete_asset" in operator_calls

    def test_load_and_delete_buttons_get_correct_asset_id(self):
        from melvil.ui.panel import _draw_asset_section

        layout = _make_layout()
        asset_id = "aaaaaaaa-0000-4000-8000-000000000001"
        asset = _make_asset(asset_id, "Red Metal", "MATERIAL")

        _draw_asset_section(layout, "Materials", "MATERIAL", [asset])

        row = layout.box.return_value.row.return_value
        # The operator() mock returns the same MagicMock for every call,
        # so we check that asset_id was assigned to the return value.
        op_mock = row.operator.return_value
        assert op_mock.asset_id == asset_id

    def test_asset_name_is_shown_as_label(self):
        from melvil.ui.panel import _draw_asset_section

        layout = _make_layout()
        asset = _make_asset("bbb", "Suzanne", "MESH")

        _draw_asset_section(layout, "Meshes", "MESH_DATA", [asset])

        row = layout.box.return_value.row.return_value
        row.label.assert_called_with(text="Suzanne")

    def test_multiple_assets_each_get_a_row(self):
        from melvil.ui.panel import _draw_asset_section

        layout = _make_layout()
        assets = [
            _make_asset("aaa", "Iron", "MATERIAL"),
            _make_asset("bbb", "Bronze", "MATERIAL"),
            _make_asset("ccc", "Gold", "MATERIAL"),
        ]

        _draw_asset_section(layout, "Materials", "MATERIAL", assets)

        box = layout.box.return_value
        # row(align=True) should be called once per asset
        assert box.row.call_count == len(assets)
