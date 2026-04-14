"""
Factory for asset-type submenus.

Creates a ``bpy.types.Menu`` subclass, a host-menu draw function, and
register/unregister helpers from a small set of parameters.  This eliminates
the near-identical boilerplate in ``menus_add`` and ``menus_node_add``.
"""

from __future__ import annotations

import bpy

from ..core.library import resolve_db_path
from ..db import open_db
from ..db.assets import list_assets


def create_asset_submenu(
    bl_idname: str,
    asset_type: str,
    operator_id: str,
    icon: str,
    empty_label: str,
    host_menu: str,
    op_prop: str = "asset_id",
):
    """Return ``(MenuClass, draw_entry_fn, register_fn, unregister_fn)``.

    Parameters
    ----------
    bl_idname:
        Unique Blender menu identifier, e.g. ``"MELVIL_MT_add_submenu"``.
    asset_type:
        Asset type string passed to ``list_assets`` (``"MESH"``, ``"NODE_GROUP"``, …).
    operator_id:
        Operator idname invoked per asset row (``"melvil.load_asset"``, …).
    icon:
        Blender icon name for each operator row.
    empty_label:
        Label shown when no assets match.
    host_menu:
        ``bl_idname`` of the Blender menu to append the submenu entry to.
    op_prop:
        Operator property name that receives the asset id.
    """

    class _Menu(bpy.types.Menu):
        bl_label = "Melvil"

        def draw(self, context):
            layout = self.layout

            scene = getattr(context, "scene", None)
            active_kit_id = getattr(scene, "melvil_active_kit_id", None)
            kit_id = None
            if isinstance(active_kit_id, str) and active_kit_id != "ALL_KITS":
                kit_id = active_kit_id

            try:
                with open_db(resolve_db_path()) as conn:
                    assets = list_assets(conn, type=asset_type, kit_id=kit_id)
            except Exception:
                layout.label(text="Could not open library", icon="ERROR")
                return

            if not assets:
                layout.label(text=empty_label, icon="INFO")
                return

            for asset in assets:
                op = layout.operator(operator_id, text=asset["name"], icon=icon)
                setattr(op, op_prop, asset["id"])

    _Menu.bl_idname = bl_idname
    _Menu.__name__ = bl_idname
    _Menu.__qualname__ = bl_idname

    def _draw_entry(self, context):
        self.layout.menu(bl_idname)

    def register() -> None:
        bpy.utils.register_class(_Menu)
        menu_type = getattr(bpy.types, host_menu, None)
        if menu_type is not None:
            menu_type.append(_draw_entry)

    def unregister() -> None:
        menu_type = getattr(bpy.types, host_menu, None)
        if menu_type is not None:
            menu_type.remove(_draw_entry)
        bpy.utils.unregister_class(_Menu)

    return _Menu, _draw_entry, register, unregister
