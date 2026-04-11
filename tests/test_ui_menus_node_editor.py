"""Tests for ui/menus_node_editor.py — MELVIL_MT_node_editor_submenu."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fresh():
    import importlib
    import melvil.ui.menus_node_editor as m
    importlib.reload(m)
    return m


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_node(select: bool = True, node_type: str = "SHADER"):
    node = MagicMock()
    node.select = select
    node.type = node_type
    return node


def _make_context(nodes=None, has_space=True):
    ctx = MagicMock()
    if has_space:
        nt = MagicMock()
        nt.nodes = nodes or []
        ctx.space_data.node_tree = nt
    else:
        ctx.space_data = None
    return ctx


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


class TestMenuMetadata:
    def test_bl_idname(self):
        from melvil.ui.menus_node_editor import MELVIL_MT_node_editor_submenu
        assert MELVIL_MT_node_editor_submenu.bl_idname == "MELVIL_MT_node_editor_submenu"

    def test_bl_label(self):
        from melvil.ui.menus_node_editor import MELVIL_MT_node_editor_submenu
        assert MELVIL_MT_node_editor_submenu.bl_label == "Melvil"

    def test_inherits_menu(self):
        import bpy
        from melvil.ui.menus_node_editor import MELVIL_MT_node_editor_submenu
        assert issubclass(MELVIL_MT_node_editor_submenu, bpy.types.Menu)


# ---------------------------------------------------------------------------
# draw()
# ---------------------------------------------------------------------------


class TestDraw:
    def test_draw_shows_save_nodes_operator(self):
        from melvil.ui.menus_node_editor import MELVIL_MT_node_editor_submenu

        menu = MELVIL_MT_node_editor_submenu()
        menu.layout = MagicMock()
        menu.draw(MagicMock())

        called_ids = [c.args[0] for c in menu.layout.operator.call_args_list]
        assert "melvil.save_nodes_as_asset" in called_ids


# ---------------------------------------------------------------------------
# _draw_node_editor_entry — guard and menu call
# ---------------------------------------------------------------------------


class TestNodeEditorEntry:
    def test_entry_shown_when_node_selected(self):
        from melvil.ui.menus_node_editor import (
            MELVIL_MT_node_editor_submenu,
            _draw_node_editor_entry,
        )

        fake_self = MagicMock()
        ctx = _make_context(nodes=[_make_node(select=True)])

        _draw_node_editor_entry(fake_self, ctx)

        fake_self.layout.menu.assert_called_once_with(MELVIL_MT_node_editor_submenu.bl_idname)

    def test_entry_hidden_when_no_nodes_selected(self):
        from melvil.ui.menus_node_editor import _draw_node_editor_entry

        fake_self = MagicMock()
        ctx = _make_context(nodes=[_make_node(select=False)])

        _draw_node_editor_entry(fake_self, ctx)

        fake_self.layout.menu.assert_not_called()

    def test_entry_hidden_when_node_tree_is_none(self):
        from melvil.ui.menus_node_editor import _draw_node_editor_entry

        fake_self = MagicMock()
        ctx = MagicMock()
        ctx.space_data.node_tree = None

        _draw_node_editor_entry(fake_self, ctx)

        fake_self.layout.menu.assert_not_called()

    def test_entry_hidden_when_space_data_is_none(self):
        from melvil.ui.menus_node_editor import _draw_node_editor_entry

        fake_self = MagicMock()
        ctx = _make_context(has_space=False)

        _draw_node_editor_entry(fake_self, ctx)

        fake_self.layout.menu.assert_not_called()

    def test_entry_hidden_when_node_list_empty(self):
        from melvil.ui.menus_node_editor import _draw_node_editor_entry

        fake_self = MagicMock()
        ctx = _make_context(nodes=[])

        _draw_node_editor_entry(fake_self, ctx)

        fake_self.layout.menu.assert_not_called()


# ---------------------------------------------------------------------------
# Host-menu registration
# ---------------------------------------------------------------------------


class TestHostMenuRegistration:
    def test_register_appends_to_node_context_menu(self):
        import bpy
        m = _fresh()
        bpy.types.NODE_MT_context_menu._handlers.clear()

        with patch.object(bpy.utils, "register_class"):
            m.register()

        assert m._draw_node_editor_entry in bpy.types.NODE_MT_context_menu._handlers

    def test_unregister_removes_from_node_context_menu(self):
        import bpy
        m = _fresh()
        bpy.types.NODE_MT_context_menu._handlers.clear()

        with patch.object(bpy.utils, "register_class"), \
             patch.object(bpy.utils, "unregister_class"):
            m.register()
            m.unregister()

        assert m._draw_node_editor_entry not in bpy.types.NODE_MT_context_menu._handlers

    def test_register_calls_register_class(self):
        import bpy
        m = _fresh()
        with patch.object(bpy.utils, "register_class") as mock_reg:
            m.register()
        mock_reg.assert_called_once_with(m.MELVIL_MT_node_editor_submenu)

    def test_unregister_calls_unregister_class(self):
        import bpy
        m = _fresh()
        with patch.object(bpy.utils, "register_class"), \
             patch.object(bpy.utils, "unregister_class") as mock_unreg:
            m.register()
            m.unregister()
        mock_unreg.assert_called_once_with(m.MELVIL_MT_node_editor_submenu)
