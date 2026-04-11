"""MELVIL_OT_asset_select — select an asset for the detail panel.

Sets ``wm.melvil_selected_asset_id`` to the given asset UUID.  Clicking the
same asset's details button again clears the selection (toggle behaviour).
The browser popup's ``check()`` returning ``True`` ensures a redraw after
each execution.
"""

from __future__ import annotations

import bpy
from bpy.props import StringProperty


class MELVIL_OT_asset_select(bpy.types.Operator):
    """Select a Melvil asset to view its details"""

    bl_idname = "melvil.asset_select"
    bl_label = "Asset Details"
    bl_options = {"REGISTER"}

    asset_id: StringProperty(
        name="Asset ID",
        description="UUID of the asset to select",
        default="",
        options={"HIDDEN"},
    )

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        asset_id = self.asset_id.strip()
        if not asset_id:
            self.report({"ERROR"}, "Melvil: no asset ID provided.")
            return {"CANCELLED"}

        wm = context.window_manager
        current = getattr(wm, "melvil_selected_asset_id", "")
        wm.melvil_selected_asset_id = "" if current == asset_id else asset_id
        return {"FINISHED"}


def register() -> None:
    bpy.utils.register_class(MELVIL_OT_asset_select)


def unregister() -> None:
    bpy.utils.unregister_class(MELVIL_OT_asset_select)
