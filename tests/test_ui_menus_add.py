"""Tests for ui/menus_add.py — BLAMMO_MT_add_submenu."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_asset(id: str, name: str) -> dict:
    return {"id": id, "name": name, "type": "MESH"}


def _fresh():
    import importlib
    import blammo.ui.menus_add as m
    importlib.reload(m)
    return m


_PATCH_LOAD = "blammo.ui.menus_factory.load_assets"


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


class TestMenuMetadata:
    def test_bl_idname(self):
        from blammo.ui.menus_add import BLAMMO_MT_add_submenu
        assert BLAMMO_MT_add_submenu.bl_idname == "BLAMMO_MT_add_submenu"

    def test_bl_label(self):
        from blammo.ui.menus_add import BLAMMO_MT_add_submenu
        assert BLAMMO_MT_add_submenu.bl_label == "Blammo!"

    def test_inherits_menu(self):
        import bpy
        from blammo.ui.menus_add import BLAMMO_MT_add_submenu
        assert issubclass(BLAMMO_MT_add_submenu, bpy.types.Menu)


# ---------------------------------------------------------------------------
# draw() — happy path: assets present
# ---------------------------------------------------------------------------


class TestDraw:
    def _menu(self):
        from blammo.ui.menus_add import BLAMMO_MT_add_submenu
        m = BLAMMO_MT_add_submenu()
        m.layout = MagicMock()
        return m

    def _context(self, active_kit_id: str = "ALL_KITS") -> MagicMock:
        ctx = MagicMock()
        scene = MagicMock()
        scene.blammo_active_kit_id = active_kit_id
        ctx.scene = scene
        return ctx

    def test_draws_one_row_per_asset(self):
        assets = [_make_asset("id1", "Rock"), _make_asset("id2", "Barrel")]
        menu = self._menu()

        with patch(_PATCH_LOAD, return_value=assets):
            menu.draw(MagicMock())

        assert menu.layout.operator.call_count == 2

    def test_operator_text_is_asset_name(self):
        assets = [_make_asset("id1", "Rock")]
        menu = self._menu()

        with patch(_PATCH_LOAD, return_value=assets):
            menu.draw(MagicMock())

        call_kwargs = menu.layout.operator.call_args
        assert call_kwargs.kwargs.get("text") == "Rock" or call_kwargs.args[1] == "Rock" \
            or call_kwargs[1].get("text") == "Rock"

    def test_operator_uses_load_asset(self):
        assets = [_make_asset("id1", "Rock")]
        menu = self._menu()

        with patch(_PATCH_LOAD, return_value=assets):
            menu.draw(MagicMock())

        first_arg = menu.layout.operator.call_args[0][0]
        assert first_arg == "blammo.load_asset"

    def test_asset_id_set_on_operator_return(self):
        assets = [_make_asset("abc-123", "Rock")]
        menu = self._menu()

        op_retval = MagicMock()
        menu.layout.operator.return_value = op_retval

        with patch(_PATCH_LOAD, return_value=assets):
            menu.draw(MagicMock())

        assert op_retval.asset_id == "abc-123"

    def test_empty_assets_shows_info_label(self):
        menu = self._menu()

        with patch(_PATCH_LOAD, return_value=[]):
            menu.draw(MagicMock())

        menu.layout.label.assert_called_once()
        label_kwargs = menu.layout.label.call_args
        assert "No mesh assets" in (label_kwargs[1].get("text") or label_kwargs[0][0])

    def test_db_error_shows_error_label(self):
        menu = self._menu()

        with patch(_PATCH_LOAD, side_effect=Exception("boom")):
            menu.draw(MagicMock())

        menu.layout.label.assert_called_once()
        label_kwargs = menu.layout.label.call_args
        assert label_kwargs[1].get("icon") == "ERROR"

    def test_filters_by_active_kit_when_set(self):
        menu = self._menu()
        kit_id = "some-kit-uuid"

        with patch(_PATCH_LOAD, return_value=[]) as mock_load:
            menu.draw(self._context(active_kit_id=kit_id))

        mock_load.assert_called_once_with("MESH", kit_id=kit_id)

    def test_no_kit_filter_when_all_kits(self):
        menu = self._menu()

        with patch(_PATCH_LOAD, return_value=[]) as mock_load:
            menu.draw(self._context(active_kit_id="ALL_KITS"))

        mock_load.assert_called_once_with("MESH", kit_id=None)


# ---------------------------------------------------------------------------
# Host-menu registration
# ---------------------------------------------------------------------------


class TestHostMenuRegistration:
    def test_register_appends_to_view3d_mt_add(self):
        import bpy
        m = _fresh()
        bpy.types.VIEW3D_MT_add._handlers.clear()

        with patch.object(bpy.utils, "register_class"):
            m.register()

        assert m._draw_add_entry in bpy.types.VIEW3D_MT_add._handlers

    def test_unregister_removes_from_view3d_mt_add(self):
        import bpy
        m = _fresh()
        bpy.types.VIEW3D_MT_add._handlers.clear()

        with patch.object(bpy.utils, "register_class"), \
             patch.object(bpy.utils, "unregister_class"):
            m.register()
            m.unregister()

        assert m._draw_add_entry not in bpy.types.VIEW3D_MT_add._handlers

    def test_register_calls_register_class(self):
        import bpy
        m = _fresh()
        with patch.object(bpy.utils, "register_class") as mock_reg:
            m.register()
        mock_reg.assert_called_once_with(m.BLAMMO_MT_add_submenu)

    def test_unregister_calls_unregister_class(self):
        import bpy
        m = _fresh()
        with patch.object(bpy.utils, "register_class"), \
             patch.object(bpy.utils, "unregister_class") as mock_unreg:
            m.register()
            m.unregister()
        mock_unreg.assert_called_once_with(m.BLAMMO_MT_add_submenu)


# ---------------------------------------------------------------------------
# _draw_add_entry — calls layout.menu with correct bl_idname
# ---------------------------------------------------------------------------


class TestAddEntry:
    def test_entry_calls_layout_menu(self):
        from blammo.ui.menus_add import BLAMMO_MT_add_submenu, _draw_add_entry

        fake_self = MagicMock()
        _draw_add_entry(fake_self, MagicMock())

        fake_self.layout.menu.assert_called_once_with(BLAMMO_MT_add_submenu.bl_idname)
