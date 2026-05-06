"""Tests for ui/menus_material.py — BLAMMO_MT_material_submenu."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


def _fresh():
    import importlib
    import blammo.ui.menus_material as m
    importlib.reload(m)
    return m


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


class TestMenuMetadata:
    def test_bl_idname(self):
        from blammo.ui.menus_material import BLAMMO_MT_material_submenu
        assert BLAMMO_MT_material_submenu.bl_idname == "BLAMMO_MT_material_submenu"

    def test_bl_label(self):
        from blammo.ui.menus_material import BLAMMO_MT_material_submenu
        assert BLAMMO_MT_material_submenu.bl_label == "Blammo!"

    def test_inherits_menu(self):
        import bpy
        from blammo.ui.menus_material import BLAMMO_MT_material_submenu
        assert issubclass(BLAMMO_MT_material_submenu, bpy.types.Menu)


# ---------------------------------------------------------------------------
# draw() — conditional entries
# ---------------------------------------------------------------------------


def _make_layout():
    """Return a MagicMock layout where operator() returns a settable object."""
    layout = MagicMock()
    layout.operator.return_value = MagicMock()
    return layout


class TestDraw:
    def test_draw_always_shows_load_new_slot(self):
        from blammo.ui.menus_material import BLAMMO_MT_material_submenu

        menu = BLAMMO_MT_material_submenu()
        menu.layout = _make_layout()
        ctx = MagicMock()
        ctx.active_object = None  # no object — still shows load option

        menu.draw(ctx)

        calls = [c.args[0] for c in menu.layout.operator.call_args_list]
        assert "blammo.load_material_to_slot" in calls

    def test_draw_with_material_shows_replace_and_save(self):
        from blammo.ui.menus_material import BLAMMO_MT_material_submenu

        menu = BLAMMO_MT_material_submenu()
        menu.layout = _make_layout()
        ctx = MagicMock()
        ctx.active_object.active_material = MagicMock()

        menu.draw(ctx)

        all_calls = [c.args[0] for c in menu.layout.operator.call_args_list]
        # Both load_material_to_slot entries and save_asset should appear
        assert all_calls.count("blammo.load_material_to_slot") == 2
        assert "blammo.save_asset" in all_calls

    def test_draw_without_material_hides_replace_and_save(self):
        from blammo.ui.menus_material import BLAMMO_MT_material_submenu

        menu = BLAMMO_MT_material_submenu()
        menu.layout = _make_layout()
        ctx = MagicMock()
        ctx.active_object.active_material = None

        menu.draw(ctx)

        all_calls = [c.args[0] for c in menu.layout.operator.call_args_list]
        assert all_calls.count("blammo.load_material_to_slot") == 1
        assert "blammo.save_asset" not in all_calls

    def test_draw_new_slot_sets_slot_mode(self):
        from blammo.ui.menus_material import BLAMMO_MT_material_submenu

        menu = BLAMMO_MT_material_submenu()
        menu.layout = _make_layout()
        ctx = MagicMock()
        ctx.active_object.active_material = None

        menu.draw(ctx)

        op_return = menu.layout.operator.return_value
        assert op_return.slot_mode == "NEW"


# ---------------------------------------------------------------------------
# _draw_material_entry — guard and menu call
# ---------------------------------------------------------------------------


class TestMaterialEntry:
    def test_entry_calls_layout_menu_when_material_present(self):
        from blammo.ui.menus_material import BLAMMO_MT_material_submenu, _draw_material_entry

        fake_self = MagicMock()
        ctx = MagicMock()
        ctx.active_object.active_material = MagicMock()

        _draw_material_entry(fake_self, ctx)

        fake_self.layout.menu.assert_called_once_with(BLAMMO_MT_material_submenu.bl_idname)

    def test_entry_shown_when_object_has_no_material(self):
        from blammo.ui.menus_material import BLAMMO_MT_material_submenu, _draw_material_entry

        fake_self = MagicMock()
        ctx = MagicMock()
        ctx.active_object.active_material = None  # object exists, no material

        _draw_material_entry(fake_self, ctx)

        fake_self.layout.menu.assert_called_once_with(BLAMMO_MT_material_submenu.bl_idname)

    def test_entry_hidden_when_no_active_object(self):
        from blammo.ui.menus_material import _draw_material_entry

        fake_self = MagicMock()
        ctx = MagicMock()
        ctx.active_object = None

        _draw_material_entry(fake_self, ctx)

        fake_self.layout.menu.assert_not_called()


# ---------------------------------------------------------------------------
# Host-menu registration
# ---------------------------------------------------------------------------


class TestHostMenuRegistration:
    def test_register_appends_to_material_context_menu(self):
        import bpy
        m = _fresh()
        bpy.types.MATERIAL_MT_context_menu._handlers.clear()

        with patch.object(bpy.utils, "register_class"):
            m.register()

        assert m._draw_material_entry in bpy.types.MATERIAL_MT_context_menu._handlers

    def test_unregister_removes_from_material_context_menu(self):
        import bpy
        m = _fresh()
        bpy.types.MATERIAL_MT_context_menu._handlers.clear()

        with patch.object(bpy.utils, "register_class"), \
             patch.object(bpy.utils, "unregister_class"):
            m.register()
            m.unregister()

        assert m._draw_material_entry not in bpy.types.MATERIAL_MT_context_menu._handlers

    def test_register_calls_register_class(self):
        import bpy
        m = _fresh()
        with patch.object(bpy.utils, "register_class") as mock_reg:
            m.register()
        mock_reg.assert_called_once_with(m.BLAMMO_MT_material_submenu)

    def test_unregister_calls_unregister_class(self):
        import bpy
        m = _fresh()
        with patch.object(bpy.utils, "register_class"), \
             patch.object(bpy.utils, "unregister_class") as mock_unreg:
            m.register()
            m.unregister()
        mock_unreg.assert_called_once_with(m.BLAMMO_MT_material_submenu)
