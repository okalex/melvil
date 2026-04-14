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
from ..db.assets import get_asset
from ..db.kits import get_kit
from ..preferences import MelvilPreferences

_BUILTIN_PREVIEW_LABELS: dict[str, str] = {
    "BUILTIN_CUBE": "Cube",
    "BUILTIN_UV_SPHERE": "UV Sphere",
    "BUILTIN_TORUS": "Torus",
    "BUILTIN_MONKEY": "Monkey",
}


def _resolve_preview_object_label(mat_prev_id: str) -> str:
    """Return the human-readable label for the current material_preview_object value."""
    if mat_prev_id in _BUILTIN_PREVIEW_LABELS:
        return _BUILTIN_PREVIEW_LABELS[mat_prev_id]
    try:
        with open_db(resolve_db_path()) as conn:
            row = get_asset(conn, mat_prev_id)
        return str(row["name"]) if row else "Unknown Asset"
    except Exception:  # noqa: BLE001
        return "Unknown Asset"


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

        layout.operator("melvil.open_browser", text="Browse Library", icon="ASSET_MANAGER")

        layout.separator()

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

        layout.separator()

        # Auto-generate previews toggle — reads from addon preferences.
        prefs = context.preferences.addons.get(MelvilPreferences.bl_idname)
        if prefs is not None:
            layout.label(text="Preview Generation")
            layout.prop(prefs.preferences, "auto_generate_previews")

            layout.label(text="Material Preview Object")
            preview_obj_id = prefs.preferences.material_preview_object
            preview_obj_label = _resolve_preview_object_label(preview_obj_id)
            layout.operator_menu_enum(
                "melvil.set_preview_object",
                "object_id",
                text=preview_obj_label,
            )
