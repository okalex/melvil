"""Tests for ui/keymaps.py — keymap registration and unregistration."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestRegister:
    def test_register_adds_keymap_entry(self):
        from melvil.ui import keymaps

        mock_kmi = MagicMock()
        mock_km = MagicMock()
        mock_km.keymap_items.new.return_value = mock_kmi
        mock_kc = MagicMock()
        mock_kc.keymaps.new.return_value = mock_km
        mock_wm = MagicMock()
        mock_wm.keyconfigs.addon = mock_kc

        with patch("melvil.ui.keymaps.bpy") as mock_bpy:
            mock_bpy.context.window_manager = mock_wm
            keymaps.register()

        mock_kc.keymaps.new.assert_called_once_with(
            name="3D View", space_type="VIEW_3D"
        )
        mock_km.keymap_items.new.assert_called_once_with(
            "melvil.open_browser",
            type="A",
            value="PRESS",
            ctrl=True,
            shift=True,
        )
        # Clean up to avoid state bleed between tests
        keymaps._keymaps.clear()

    def test_register_skips_when_addon_keyconfig_is_none(self):
        from melvil.ui import keymaps

        mock_wm = MagicMock()
        mock_wm.keyconfigs.addon = None

        with patch("melvil.ui.keymaps.bpy") as mock_bpy:
            mock_bpy.context.window_manager = mock_wm
            keymaps.register()  # should not raise

        assert len(keymaps._keymaps) == 0


class TestUnregister:
    def test_unregister_removes_items_and_clears_list(self):
        from melvil.ui import keymaps

        mock_km = MagicMock()
        mock_kmi = MagicMock()
        keymaps._keymaps.append((mock_km, mock_kmi))

        keymaps.unregister()

        mock_km.keymap_items.remove.assert_called_once_with(mock_kmi)
        assert len(keymaps._keymaps) == 0

    def test_unregister_is_safe_when_empty(self):
        from melvil.ui import keymaps

        keymaps._keymaps.clear()
        keymaps.unregister()  # should not raise
