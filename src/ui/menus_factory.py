"""
Factory and helpers for asset-type submenus.

``create_asset_submenu`` generates a ``bpy.types.Menu`` subclass, a
host-menu draw function, and register/unregister helpers from a small set
of parameters — eliminating the near-identical boilerplate in
``menus_add`` and ``menus_node_add``.

``register_submenu`` / ``unregister_submenu`` handle the three-step
register/unregister dance shared by all menu modules.
"""

from __future__ import annotations

import bpy

from .draw_helpers import load_assets


# ---------------------------------------------------------------------------
# Generic register / unregister helpers (item 2)
# ---------------------------------------------------------------------------


def register_submenu(cls, host_menu_id: str, draw_fn) -> None:
    """Register *cls* and append *draw_fn* to the host menu."""
    bpy.utils.register_class(cls)
    menu_type = getattr(bpy.types, host_menu_id, None)
    if menu_type is not None:
        menu_type.append(draw_fn)


def unregister_submenu(cls, host_menu_id: str, draw_fn) -> None:
    """Remove *draw_fn* from the host menu and unregister *cls*."""
    menu_type = getattr(bpy.types, host_menu_id, None)
    if menu_type is not None:
        menu_type.remove(draw_fn)
    bpy.utils.unregister_class(cls)


# ---------------------------------------------------------------------------
# Asset submenu factory (items 1 + 4)
# ---------------------------------------------------------------------------


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
        Asset type string passed to ``load_assets`` (``"MESH"``, ``"NODE_GROUP"``, …).
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
                assets = load_assets(asset_type, kit_id=kit_id)
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
        register_submenu(_Menu, host_menu, _draw_entry)

    def unregister() -> None:
        unregister_submenu(_Menu, host_menu, _draw_entry)

    return _Menu, _draw_entry, register, unregister
