"""
Melvil N-panel — 3D Viewport sidebar (N key → Melvil tab).

Layout
------
- "Save as Asset" button (calls ``melvil.save_asset`` with dialog)
- "Browse Library" button (calls ``melvil.open_browser`` popup)
- Active Kit section — dropdown to filter add-menu items by kit
"""

from __future__ import annotations

import bpy

from ..core.library import resolve_db_path
from ..db import open_db
from ..db.kits import get_kit


class MELVIL_PT_main(bpy.types.Panel):
    """Melvil asset library panel"""

    bl_idname = "MELVIL_PT_main"
    bl_label = "Melvil Assets"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Melvil"

    @classmethod
    def poll(cls, context):
        return True

    def draw(self, context):
        layout = self.layout

        # "Save as Asset" is always shown; Blender greys it out when the
        # operator's poll() fails (no active object).
        layout.operator("melvil.save_asset", text="Save as Asset", icon="ADD")
        layout.operator("melvil.open_browser", text="Browse Library", icon="ASSET_MANAGER")

        layout.separator()

        # Active Kit — dropdown backed by melvil.set_active_kit.  The button
        # label reflects the current selection stored on the scene.
        scene = getattr(context, "scene", None)
        active_kit_id = getattr(scene, "melvil_active_kit_id", None)
        if not isinstance(active_kit_id, str) or active_kit_id == "ALL_KITS":
            kit_label = "All Kits"
        else:
            try:
                with open_db(resolve_db_path()) as conn:
                    row = get_kit(conn, active_kit_id)
                kit_label = str(row["name"]) if row else "All Kits"
            except Exception:  # noqa: BLE001
                kit_label = "All Kits"

        layout.label(text="Active Kit")
        layout.operator_menu_enum(
            "melvil.set_active_kit",
            "kit_id",
            text=kit_label,
            icon="BOOKMARKS",
        )
