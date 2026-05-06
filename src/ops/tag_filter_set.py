"""BLAMMO_OT_tag_filter_set — set a single exclusive tag filter in the browser.

Unlike ``tag_filter_toggle`` (which supports multiple active tags), this
operator provides single-select behaviour:

- If the given tag is not already the sole active filter → set it as the
  only active filter.
- If the given tag is already the sole active filter → clear all filters
  (acts as a toggle-off).
"""

from __future__ import annotations

import bpy
from bpy.props import StringProperty

from .tag_filter_toggle import get_active_tag_filters, set_active_tag_filters


class BLAMMO_OT_tag_filter_set(bpy.types.Operator):
    """Set a single tag as the exclusive active filter in the Blammo browser"""

    bl_idname = "blammo.tag_filter_set"
    bl_label = "Set Tag Filter"
    bl_options = {"REGISTER"}

    tag_id: StringProperty(
        name="Tag ID",
        description="UUID of the tag to set as the exclusive filter",
        default="",
        options={"HIDDEN"},
    )

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        tag_id = self.tag_id.strip()
        if not tag_id:
            self.report({"ERROR"}, "Blammo!: no tag ID provided.")
            return {"CANCELLED"}

        wm = context.window_manager
        active = get_active_tag_filters(wm)

        if active == [tag_id]:
            # Already the sole active filter — toggle off.
            set_active_tag_filters(wm, [])
        else:
            set_active_tag_filters(wm, [tag_id])

        return {"FINISHED"}


def register() -> None:
    bpy.utils.register_class(BLAMMO_OT_tag_filter_set)


def unregister() -> None:
    bpy.utils.unregister_class(BLAMMO_OT_tag_filter_set)
