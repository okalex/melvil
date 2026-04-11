"""Tests for ui/panel.py — MELVIL_PT_main."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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

        panel.draw(MagicMock())

        layout.operator.assert_any_call(
            "melvil.save_asset", text="Save as Asset", icon="ADD"
        )

    def test_browse_button_always_drawn(self):
        panel = self._panel()
        layout = _make_layout()
        panel.layout = layout

        panel.draw(MagicMock())

        layout.operator.assert_any_call(
            "melvil.open_browser", text="Browse Library", icon="ASSET_MANAGER"
        )
