"""
Melvil submenu for the Add menu (Shift-A / Object ▸ Add).

``MELVIL_MT_add_submenu`` appears as a "Melvil ▶" entry in
``VIEW3D_MT_add``.  Its ``draw()`` method queries the database at draw-time
and renders one ``melvil.load_asset`` operator button per saved mesh asset.

Blender indexes operator *display text* for menu search, so assets are
individually searchable by name inside the Add menu search box without any
extra work.
"""

from __future__ import annotations

import bpy

from ..core.library import resolve_db_path
from ..db import open_db
from ..db.assets import list_assets


class MELVIL_MT_add_submenu(bpy.types.Menu):
    """Melvil mesh assets — shown as a sub-menu inside the Add menu."""

    bl_idname = "MELVIL_MT_add_submenu"
    bl_label = "Melvil"

    def draw(self, context):
        layout = self.layout

        try:
            with open_db(resolve_db_path()) as conn:
                assets = list_assets(conn, type="MESH")
        except Exception:
            layout.label(text="Could not open library", icon="ERROR")
            return

        if not assets:
            layout.label(text="No mesh assets saved yet", icon="INFO")
            return

        for asset in assets:
            op = layout.operator("melvil.load_asset", text=asset["name"], icon="MESH_DATA")
            op.asset_id = asset["id"]


# ---------------------------------------------------------------------------
# Draw function appended to VIEW3D_MT_add
# ---------------------------------------------------------------------------


def _draw_add_entry(self, context):
    """Appended to VIEW3D_MT_add to insert the Melvil sub-menu."""
    self.layout.menu(MELVIL_MT_add_submenu.bl_idname)


# ---------------------------------------------------------------------------
# Register / unregister
# ---------------------------------------------------------------------------


def register() -> None:
    bpy.utils.register_class(MELVIL_MT_add_submenu)
    add_menu = getattr(bpy.types, "VIEW3D_MT_add", None)
    if add_menu is not None:
        add_menu.append(_draw_add_entry)


def unregister() -> None:
    add_menu = getattr(bpy.types, "VIEW3D_MT_add", None)
    if add_menu is not None:
        add_menu.remove(_draw_add_entry)
    bpy.utils.unregister_class(MELVIL_MT_add_submenu)
