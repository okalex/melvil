"""MELVIL_OT_tag_filter_clear — clear all active tag filters in the browser."""

from __future__ import annotations

import bpy

from .tag_filter_toggle import set_active_tag_filters


class MELVIL_OT_tag_filter_clear(bpy.types.Operator):
    """Clear all active tag filters in the Melvil browser"""

    bl_idname = "melvil.tag_filter_clear"
    bl_label = "Clear Tag Filters"
    bl_options = {"REGISTER", "INTERNAL"}

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        set_active_tag_filters(context.window_manager, [])
        return {"FINISHED"}
