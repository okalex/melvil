"""Tests for ui/menus.py — BLAMMO_MT_context_submenu and item registry."""

from __future__ import annotations

from unittest.mock import MagicMock, call, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fresh_menus():
    """Re-import menus with a clean _items list each time."""
    import importlib
    import blammo.ui.menus as m

    importlib.reload(m)
    return m


# ---------------------------------------------------------------------------
# BLAMMO_MT_context_submenu metadata
# ---------------------------------------------------------------------------


class TestMenuMetadata:
    def test_bl_idname(self):
        from blammo.ui.menus import BLAMMO_MT_context_submenu

        assert BLAMMO_MT_context_submenu.bl_idname == "BLAMMO_MT_context_submenu"

    def test_bl_label(self):
        from blammo.ui.menus import BLAMMO_MT_context_submenu

        assert BLAMMO_MT_context_submenu.bl_label == "Blammo!"

    def test_inherits_menu(self):
        import bpy
        from blammo.ui.menus import BLAMMO_MT_context_submenu

        assert issubclass(BLAMMO_MT_context_submenu, bpy.types.Menu)


# ---------------------------------------------------------------------------
# Item registry — register_item / unregister_item
# ---------------------------------------------------------------------------


class TestItemRegistry:
    def test_register_item_adds_to_list(self):
        m = _fresh_menus()
        fn = MagicMock()
        m.register_item(fn)
        assert fn in m._items

    def test_register_item_is_idempotent(self):
        m = _fresh_menus()
        fn = MagicMock()
        m.register_item(fn)
        m.register_item(fn)
        assert m._items.count(fn) == 1

    def test_unregister_item_removes_fn(self):
        m = _fresh_menus()
        fn = MagicMock()
        m.register_item(fn)
        m.unregister_item(fn)
        assert fn not in m._items

    def test_unregister_item_is_safe_when_not_registered(self):
        m = _fresh_menus()
        fn = MagicMock()
        # should not raise
        m.unregister_item(fn)


# ---------------------------------------------------------------------------
# Submenu draw — calls registered items
# ---------------------------------------------------------------------------


class TestSubmenuDraw:
    def test_draw_calls_each_registered_item(self):
        m = _fresh_menus()
        fn1, fn2 = MagicMock(), MagicMock()
        m.register_item(fn1)
        m.register_item(fn2)

        menu_instance = m.BLAMMO_MT_context_submenu()
        menu_instance.layout = MagicMock()
        ctx = MagicMock()

        menu_instance.draw(ctx)

        fn1.assert_called_once_with(menu_instance, ctx)
        fn2.assert_called_once_with(menu_instance, ctx)

    def test_draw_is_empty_when_no_items_registered(self):
        m = _fresh_menus()
        menu_instance = m.BLAMMO_MT_context_submenu()
        menu_instance.layout = MagicMock()
        # Should not raise and layout should not be touched.
        menu_instance.draw(MagicMock())
        menu_instance.layout.assert_not_called()


# ---------------------------------------------------------------------------
# Host-menu patching — register() / unregister()
# ---------------------------------------------------------------------------


class TestHostMenuIntegration:
    def test_register_appends_entry_to_object_context_menu(self):
        import bpy

        m = _fresh_menus()
        bpy.types.VIEW3D_MT_object_context_menu._handlers.clear()

        with patch.object(bpy.utils, "register_class"):
            m.register()

        assert m._draw_blammo_submenu_entry in bpy.types.VIEW3D_MT_object_context_menu._handlers

    def test_unregister_removes_entry_from_object_context_menu(self):
        import bpy

        m = _fresh_menus()
        bpy.types.VIEW3D_MT_object_context_menu._handlers.clear()

        with patch.object(bpy.utils, "register_class"), patch.object(bpy.utils, "unregister_class"):
            m.register()
            m.unregister()

        assert m._draw_blammo_submenu_entry not in bpy.types.VIEW3D_MT_object_context_menu._handlers

    def test_register_calls_register_class_for_submenu(self):
        import bpy

        m = _fresh_menus()
        with patch.object(bpy.utils, "register_class") as mock_reg:
            m.register()

        mock_reg.assert_called_once_with(m.BLAMMO_MT_context_submenu)

    def test_unregister_calls_unregister_class_for_submenu(self):
        import bpy

        m = _fresh_menus()
        with patch.object(bpy.utils, "register_class"), patch.object(bpy.utils, "unregister_class") as mock_unreg:
            m.register()
            m.unregister()

        mock_unreg.assert_called_once_with(m.BLAMMO_MT_context_submenu)


# ---------------------------------------------------------------------------
# _draw_blammo_submenu_entry — calls layout.menu with correct bl_idname
# ---------------------------------------------------------------------------


class TestSubmenuEntry:
    def test_entry_calls_layout_menu_with_correct_idname(self):
        from blammo.ui.menus import BLAMMO_MT_context_submenu, _draw_blammo_submenu_entry

        fake_self = MagicMock()
        ctx = MagicMock()
        ctx.selected_objects = [MagicMock()]
        _draw_blammo_submenu_entry(fake_self, ctx)

        fake_self.layout.menu.assert_called_once_with(BLAMMO_MT_context_submenu.bl_idname)

    def test_entry_hidden_when_nothing_selected(self):
        from blammo.ui.menus import _draw_blammo_submenu_entry

        fake_self = MagicMock()
        ctx = MagicMock()
        ctx.selected_objects = []
        _draw_blammo_submenu_entry(fake_self, ctx)

        fake_self.layout.menu.assert_not_called()


# ---------------------------------------------------------------------------
# menu_items — default save-asset item
# ---------------------------------------------------------------------------


class TestMenuItems:
    def test_save_asset_item_registered_after_register(self):
        import importlib

        import blammo.ui.menu_items as mi
        import blammo.ui.menus as m

        importlib.reload(m)
        importlib.reload(mi)

        mi.register()
        assert mi._draw_save_asset in m._items

    def test_save_asset_item_unregistered_after_unregister(self):
        import importlib

        import blammo.ui.menu_items as mi
        import blammo.ui.menus as m

        importlib.reload(m)
        importlib.reload(mi)

        mi.register()
        mi.unregister()
        assert mi._draw_save_asset not in m._items

    def test_draw_save_asset_calls_operator(self):
        from blammo.ui.menu_items import _draw_save_asset

        fake_self = MagicMock()
        _draw_save_asset(fake_self, MagicMock())

        fake_self.layout.operator.assert_called_once_with("blammo.save_asset", icon="EXPORT")
