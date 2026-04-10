"""
MELVIL_OT_toggle_sidebar — open or close the Melvil N-panel tab.

Bound to ``Ctrl+Shift+A`` in the 3D View by ``ui/keymaps.py``.

Toggling ``space_data.show_region_ui`` opens or closes the sidebar.
Because the Melvil tab is in the ``"Melvil"`` category the user lands
on it naturally when the sidebar opens, provided no other tab was
previously active before it was closed.
"""

from __future__ import annotations

import bpy


class MELVIL_OT_toggle_sidebar(bpy.types.Operator):
    """Toggle the Melvil sidebar panel (Ctrl+Shift+A)"""

    bl_idname = "melvil.toggle_sidebar"
    bl_label = "Toggle Melvil Panel"
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        return (
            context.area is not None
            and context.area.type == "VIEW_3D"
        )

    def execute(self, context):
        context.space_data.show_region_ui = not context.space_data.show_region_ui
        return {"FINISHED"}
