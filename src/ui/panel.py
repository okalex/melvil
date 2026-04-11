"""
Melvil N-panel — 3D Viewport sidebar (N key → Melvil tab).

Layout
------
- "Save as Asset" button (calls ``melvil.save_asset`` with dialog)
- "Browse Library" button (calls ``melvil.open_browser`` popup)
"""

from __future__ import annotations

import bpy


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
