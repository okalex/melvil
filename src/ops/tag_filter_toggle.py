"""BLAMMO_OT_tag_filter_toggle — toggle a tag's active state in the browser filter.

Active tag filters are stored as a comma-separated list of tag UUIDs on
``bpy.types.WindowManager.blammo_active_tag_filters``.  This property is
non-persistent (registered dynamically, not saved in the .blend file).

When one or more tags are active the browser shows only assets that have
**all** of those tags (AND semantics).
"""

from __future__ import annotations

import bpy
from bpy.props import StringProperty


def get_active_tag_filters(wm) -> list[str]:
    """Return the list of currently active tag filter UUIDs."""
    raw = getattr(wm, "blammo_active_tag_filters", "")
    return [t for t in raw.split(",") if t]


def set_active_tag_filters(wm, filters: list[str]) -> None:
    """Persist *filters* (list of UUIDs) back onto the window manager."""
    wm.blammo_active_tag_filters = ",".join(filters)


class BLAMMO_OT_tag_filter_toggle(bpy.types.Operator):
    """Toggle a tag as an active filter in the Blammo browser"""

    bl_idname = "blammo.tag_filter_toggle"
    bl_label = "Toggle Tag Filter"
    bl_options = {"REGISTER"}

    tag_id: StringProperty(
        name="Tag ID",
        description="UUID of the tag to toggle as a filter",
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

        if tag_id in active:
            active.remove(tag_id)
        else:
            active.append(tag_id)

        set_active_tag_filters(wm, active)
        return {"FINISHED"}
