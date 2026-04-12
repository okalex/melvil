"""Tests for ui/panel.py — MELVIL_PT_main."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_layout():
    return MagicMock()


def _make_context(active_kit_id: str = "ALL_KITS") -> MagicMock:
    ctx = MagicMock()
    scene = MagicMock()
    scene.melvil_active_kit_id = active_kit_id
    ctx.scene = scene
    return ctx


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

    def test_browse_button_always_drawn(self):
        panel = self._panel()
        layout = _make_layout()
        panel.layout = layout

        panel.draw(_make_context())

        layout.operator.assert_any_call(
            "melvil.open_browser", text="Browse Library", icon="ASSET_MANAGER"
        )

    def test_active_kit_label_drawn(self):
        panel = self._panel()
        layout = _make_layout()
        panel.layout = layout

        panel.draw(_make_context())

        layout.label.assert_any_call(text="Active Kit")

    def test_active_kit_operator_menu_enum_drawn(self):
        panel = self._panel()
        layout = _make_layout()
        panel.layout = layout

        panel.draw(_make_context())

        layout.operator_menu_enum.assert_called_once_with(
            "melvil.set_active_kit",
            "kit_id",
            text="All Kits",
            icon="BOOKMARKS",
        )

    def test_active_kit_shows_all_kits_when_sentinel(self):
        panel = self._panel()
        layout = _make_layout()
        panel.layout = layout

        panel.draw(_make_context(active_kit_id="ALL_KITS"))

        call_kwargs = layout.operator_menu_enum.call_args
        text = call_kwargs.kwargs.get("text") or call_kwargs[1].get("text")
        assert text == "All Kits"

    def test_active_kit_shows_kit_name_when_specific_kit(self):
        panel = self._panel()
        layout = _make_layout()
        panel.layout = layout

        kit_id = "00000000-0000-4000-8000-000000000001"
        ctx = _make_context(active_kit_id=kit_id)

        fake_row = {"name": "General"}
        with patch("melvil.ui.panel.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ui.panel.open_db") as mock_open, \
             patch("melvil.ui.panel.get_kit", return_value=fake_row):
            mock_open.return_value.__enter__ = lambda s: MagicMock()
            mock_open.return_value.__exit__ = MagicMock(return_value=False)
            panel.draw(ctx)

        call_kwargs = layout.operator_menu_enum.call_args
        text = call_kwargs.kwargs.get("text") or call_kwargs[1].get("text")
        assert text == "General"

    def test_active_kit_falls_back_to_all_kits_on_db_error(self):
        panel = self._panel()
        layout = _make_layout()
        panel.layout = layout

        kit_id = "some-kit-uuid"
        ctx = _make_context(active_kit_id=kit_id)

        with patch("melvil.ui.panel.resolve_db_path", side_effect=Exception("no db")):
            panel.draw(ctx)

        call_kwargs = layout.operator_menu_enum.call_args
        text = call_kwargs.kwargs.get("text") or call_kwargs[1].get("text")
        assert text == "All Kits"

    def test_auto_generate_previews_checkbox_drawn_when_prefs_available(self):
        panel = self._panel()
        layout = _make_layout()
        panel.layout = layout

        ctx = _make_context()
        mock_prefs = MagicMock()
        ctx.preferences.addons.get.return_value = mock_prefs

        panel.draw(ctx)

        layout.prop.assert_any_call(mock_prefs.preferences, "auto_generate_previews")

    def test_auto_generate_previews_checkbox_not_drawn_when_prefs_absent(self):
        panel = self._panel()
        layout = _make_layout()
        panel.layout = layout

        ctx = _make_context()
        ctx.preferences.addons.get.return_value = None

        panel.draw(ctx)

        prop_calls = [c for c in layout.prop.call_args_list if "auto_generate_previews" in c[0]]
        assert len(prop_calls) == 0
