"""MELVIL_OT_tag_sort_toggle — set the tag management sort order."""

from __future__ import annotations

import bpy
from bpy.props import StringProperty


class MELVIL_OT_tag_sort_toggle(bpy.types.Operator):
    """Set the sort order for the tag management list"""

    bl_idname = "melvil.tag_sort_toggle"
    bl_label = ""
    bl_options = {"REGISTER", "INTERNAL"}

    sort_by: StringProperty(
        name="Sort By",
        description="Sort order: 'NAME' or 'USAGE'",
        default="NAME",
        options={"HIDDEN"},
    )

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        sort_by = self.sort_by.strip().upper()
        if sort_by not in ("NAME", "USAGE"):
            self.report({"WARNING"}, f"Melvil: unknown sort order '{sort_by}'")
            return {"CANCELLED"}
        context.window_manager.melvil_tag_sort = sort_by
        return {"FINISHED"}
