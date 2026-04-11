"""Tests for ui/menus_node_add.py — MELVIL_MT_node_add_submenu."""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_asset(id: str, name: str) -> dict:
    return {"id": id, "name": name, "type": "NODE_GROUP"}


def _fresh():
    import importlib
    import melvil.ui.menus_node_add as m
    importlib.reload(m)
    return m


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


class TestMenuMetadata:
    def test_bl_idname(self):
        from melvil.ui.menus_node_add import MELVIL_MT_node_add_submenu
        assert MELVIL_MT_node_add_submenu.bl_idname == "MELVIL_MT_node_add_submenu"

    def test_bl_label(self):
        from melvil.ui.menus_node_add import MELVIL_MT_node_add_submenu
        assert MELVIL_MT_node_add_submenu.bl_label == "Melvil"

    def test_inherits_menu(self):
        import bpy
        from melvil.ui.menus_node_add import MELVIL_MT_node_add_submenu
        assert issubclass(MELVIL_MT_node_add_submenu, bpy.types.Menu)


# ---------------------------------------------------------------------------
# draw()
# ---------------------------------------------------------------------------


class TestDraw:
    def _menu(self):
        from melvil.ui.menus_node_add import MELVIL_MT_node_add_submenu
        m = MELVIL_MT_node_add_submenu()
        m.layout = MagicMock()
        m.layout.operator.return_value = MagicMock()
        return m

    def test_draws_one_row_per_asset(self):
        assets = [_make_asset("id1", "Noise FX"), _make_asset("id2", "Marble PBR")]
        menu = self._menu()

        with patch("melvil.ui.menus_node_add.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ui.menus_node_add.open_db") as mock_open, \
             patch("melvil.ui.menus_node_add.list_assets", return_value=assets):
            mock_open.return_value.__enter__ = lambda s: MagicMock()
            mock_open.return_value.__exit__ = MagicMock(return_value=False)
            menu.draw(MagicMock())

        assert menu.layout.operator.call_count == 2

    def test_operator_uses_add_node_group(self):
        assets = [_make_asset("id1", "Noise FX")]
        menu = self._menu()

        with patch("melvil.ui.menus_node_add.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ui.menus_node_add.open_db") as mock_open, \
             patch("melvil.ui.menus_node_add.list_assets", return_value=assets):
            mock_open.return_value.__enter__ = lambda s: MagicMock()
            mock_open.return_value.__exit__ = MagicMock(return_value=False)
            menu.draw(MagicMock())

        first_arg = menu.layout.operator.call_args[0][0]
        assert first_arg == "melvil.add_node_group"

    def test_operator_text_is_asset_name(self):
        assets = [_make_asset("id1", "Noise FX")]
        menu = self._menu()

        with patch("melvil.ui.menus_node_add.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ui.menus_node_add.open_db") as mock_open, \
             patch("melvil.ui.menus_node_add.list_assets", return_value=assets):
            mock_open.return_value.__enter__ = lambda s: MagicMock()
            mock_open.return_value.__exit__ = MagicMock(return_value=False)
            menu.draw(MagicMock())

        call_kwargs = menu.layout.operator.call_args
        text = call_kwargs.kwargs.get("text") or call_kwargs[1].get("text")
        assert text == "Noise FX"

    def test_asset_id_set_on_operator_return(self):
        assets = [_make_asset("abc-123", "Noise FX")]
        menu = self._menu()
        op_retval = MagicMock()
        menu.layout.operator.return_value = op_retval

        with patch("melvil.ui.menus_node_add.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ui.menus_node_add.open_db") as mock_open, \
             patch("melvil.ui.menus_node_add.list_assets", return_value=assets):
            mock_open.return_value.__enter__ = lambda s: MagicMock()
            mock_open.return_value.__exit__ = MagicMock(return_value=False)
            menu.draw(MagicMock())

        assert op_retval.asset_id == "abc-123"

    def test_empty_assets_shows_info_label(self):
        menu = self._menu()

        with patch("melvil.ui.menus_node_add.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ui.menus_node_add.open_db") as mock_open, \
             patch("melvil.ui.menus_node_add.list_assets", return_value=[]):
            mock_open.return_value.__enter__ = lambda s: MagicMock()
            mock_open.return_value.__exit__ = MagicMock(return_value=False)
            menu.draw(MagicMock())

        menu.layout.label.assert_called_once()
        label_kwargs = menu.layout.label.call_args
        assert "No node group assets" in (
            label_kwargs.kwargs.get("text") or label_kwargs[1].get("text") or ""
        )

    def test_db_error_shows_error_label(self):
        menu = self._menu()

        with patch("melvil.ui.menus_node_add.resolve_db_path", side_effect=Exception("boom")):
            menu.draw(MagicMock())

        menu.layout.label.assert_called_once()
        call_kwargs = menu.layout.label.call_args
        assert (call_kwargs.kwargs.get("icon") or call_kwargs[1].get("icon")) == "ERROR"


# ---------------------------------------------------------------------------
# _draw_node_add_entry
# ---------------------------------------------------------------------------


class TestNodeAddEntry:
    def test_entry_calls_layout_menu(self):
        from melvil.ui.menus_node_add import MELVIL_MT_node_add_submenu, _draw_node_add_entry

        fake_self = MagicMock()
        _draw_node_add_entry(fake_self, MagicMock())
        fake_self.layout.menu.assert_called_once_with(MELVIL_MT_node_add_submenu.bl_idname)


# ---------------------------------------------------------------------------
# Host-menu registration
# ---------------------------------------------------------------------------


class TestHostMenuRegistration:
    def test_register_appends_to_node_mt_add(self):
        import bpy
        m = _fresh()
        bpy.types.NODE_MT_add._handlers.clear()

        with patch.object(bpy.utils, "register_class"):
            m.register()

        assert m._draw_node_add_entry in bpy.types.NODE_MT_add._handlers

    def test_unregister_removes_from_node_mt_add(self):
        import bpy
        m = _fresh()
        bpy.types.NODE_MT_add._handlers.clear()

        with patch.object(bpy.utils, "register_class"), \
             patch.object(bpy.utils, "unregister_class"):
            m.register()
            m.unregister()

        assert m._draw_node_add_entry not in bpy.types.NODE_MT_add._handlers

    def test_register_calls_register_class(self):
        import bpy
        m = _fresh()
        with patch.object(bpy.utils, "register_class") as mock_reg:
            m.register()
        mock_reg.assert_called_once_with(m.MELVIL_MT_node_add_submenu)

    def test_unregister_calls_unregister_class(self):
        import bpy
        m = _fresh()
        with patch.object(bpy.utils, "register_class"), \
             patch.object(bpy.utils, "unregister_class") as mock_unreg:
            m.register()
            m.unregister()
        mock_unreg.assert_called_once_with(m.MELVIL_MT_node_add_submenu)
