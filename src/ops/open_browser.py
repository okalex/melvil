"""
MELVIL_OT_open_browser — floating popup library browser.

Invoked by ``Ctrl+Shift+A`` or the "Browse Library" button in the N-panel.
Uses ``window_manager.invoke_popup()`` to open a clean floating window
containing the full Melvil asset list — no Blender editor chrome.

The popup draws Materials and Meshes sections using the shared
``draw_asset_section`` helper.  Clicking a Load button inside the popup
immediately appends the asset and closes the window.
"""

from __future__ import annotations

import bpy

from ..ui.draw_helpers import draw_asset_section, load_assets

_POPUP_WIDTH = 400


class MELVIL_OT_open_browser(bpy.types.Operator):
    """Open the Melvil library browser (Ctrl+Shift+A)"""

    bl_idname = "melvil.open_browser"
    bl_label = "Melvil Library"
    bl_options = {"REGISTER"}

    # ------------------------------------------------------------------
    # Blender operator interface
    # ------------------------------------------------------------------

    @classmethod
    def poll(cls, context):
        return context.area is not None and context.area.type == "VIEW_3D"

    def invoke(self, context, event):
        return context.window_manager.invoke_popup(self, width=_POPUP_WIDTH)

    def execute(self, context):
        # Called when the user presses Enter / confirms; nothing to do here
        # as individual asset operators (load/delete) handle their own logic.
        return {"FINISHED"}

    def draw(self, context):
        layout = self.layout
        layout.label(text="Melvil Library", icon="ASSET_MANAGER")
        layout.separator()

        try:
            materials = load_assets("MATERIAL")
            meshes = load_assets("MESH")
        except Exception:
            layout.label(text="Could not open library database", icon="ERROR")
            return

        draw_asset_section(layout, "Materials", "MATERIAL", materials)
        draw_asset_section(layout, "Meshes", "MESH_DATA", meshes)
