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

        layout.operator.assert_any_call(
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
             patch("melvil.ui.panel.draw_asset_section") as mock_section:
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
