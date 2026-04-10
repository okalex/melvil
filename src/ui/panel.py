"""
Melvil N-panel — 3D Viewport sidebar (N key → Melvil tab).

Layout
------
- "Save as Asset" button (calls ``melvil.save_asset`` with dialog)
- **Materials** section (box) — one row per saved material asset
- **Meshes** section (box) — one row per saved mesh asset

Each asset row displays the name and two icon buttons:
- IMPORT  → ``melvil.load_asset``
- TRASH   → ``melvil.delete_asset``

Both sections show a placeholder label when empty.

Architecture note
-----------------
The list is read directly from the database on every draw call.  This is
intentionally simple for M1.  M2 will introduce a WindowManager-level
``CollectionProperty`` cache so the list can be filtered and searched
without touching the DB on every redraw.
"""

from __future__ import annotations

import bpy

from ..core.library import resolve_db_path
from ..db import open_db
from ..db.assets import list_assets


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
        layout.separator()

        try:
            with open_db(resolve_db_path()) as conn:
                materials = list_assets(conn, type="MATERIAL")
                meshes = list_assets(conn, type="MESH")
        except Exception:
            layout.label(text="Could not open library database", icon="ERROR")
            return

        _draw_asset_section(layout, "Materials", "MATERIAL", materials)
        _draw_asset_section(layout, "Meshes", "MESH_DATA", meshes)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _draw_asset_section(layout, title: str, icon: str, assets) -> None:
    """
    Draw a titled box containing one row per asset in *assets*.

    Each row has:
    - the asset name (label)
    - a Load button  (IMPORT icon → ``melvil.load_asset``)
    - a Delete button (TRASH icon → ``melvil.delete_asset``)

    When *assets* is empty a placeholder label is shown instead.
    """
    box = layout.box()
    box.label(text=title, icon=icon)

    if not assets:
        box.label(text=f"No {title.lower()} saved yet")
        return

    for asset in assets:
        row = box.row(align=True)
        row.label(text=asset["name"])

        load_op = row.operator("melvil.load_asset", text="", icon="IMPORT")
        load_op.asset_id = asset["id"]

        del_op = row.operator("melvil.delete_asset", text="", icon="TRASH")
        del_op.asset_id = asset["id"]
