"""
Scene-level properties for Melvil.

Registered on ``bpy.types.Scene`` so values persist with the .blend file.
WindowManager properties are registered for transient (non-persistent) state.

Properties on Scene
-------------------
melvil_active_kit_id : str
    The kit currently active for filtering add-menu items.  ``"ALL_KITS"``
    means no kit filter is applied.

melvil_mru_kit_id : str
    The kit most recently used when saving an asset.  Empty string means no
    MRU kit has been recorded yet.  Used as a fallback default in the save
    dialog when the active kit is "All Kits".

Properties on WindowManager
---------------------------
melvil_active_tag_filters : str
    Comma-separated list of tag UUIDs currently active as browser filters.
    Non-persistent — reset each Blender session.
"""

from __future__ import annotations

import bpy
from bpy.props import BoolProperty, CollectionProperty, IntProperty, StringProperty
from bpy.types import PropertyGroup


# Guard flag: set True while draw() rebuilds melvil_filter_tags so that the
# is_active update callback does not fire during that reconstruction.
_rebuilding_filter_tags: bool = False


def _update_filter_tags_index(self, context) -> None:
    """Toggle the tag filter when the user clicks a row in the filter tag list.

    ``self`` is the WindowManager instance.  After toggling, the index is
    reset to -1 so that clicking the same row a second time fires the
    callback again (enabling click-to-deselect).
    """
    if _rebuilding_filter_tags:
        return
    idx = self.melvil_filter_tags_index
    if idx < 0 or idx >= len(self.melvil_filter_tags):
        return
    tag_id = self.melvil_filter_tags[idx].tag_id
    active = [t for t in self.melvil_active_tag_filters.split(",") if t]
    if active == [tag_id]:
        self.melvil_active_tag_filters = ""
    else:
        self.melvil_active_tag_filters = tag_id
    # Reset so clicking the same row again fires this callback.
    self.melvil_filter_tags_index = -1


class MelvilFilterTagItem(PropertyGroup):
    """A single filter-tag entry for the browser left-column tag list."""
    tag_id: StringProperty(
        name="Tag ID",
        description="UUID of the tag",
        default="",
        options={"HIDDEN"},
    )
    is_active: BoolProperty(
        name="Active",
        description="Whether this tag is currently used as a filter",
        default=False,
        options={"HIDDEN"},
    )


class MelvilTagItem(PropertyGroup):
    """A single tag name, used to populate the asset detail tag list."""
    # ``name`` is inherited from PropertyGroup — no extra annotations needed.
    tag_id: StringProperty(
        name="Tag ID",
        description="UUID of the tag",
        default="",
        options={"HIDDEN"},
    )


def register() -> None:
    bpy.utils.register_class(MelvilFilterTagItem)
    bpy.utils.register_class(MelvilTagItem)
    bpy.types.Scene.melvil_active_kit_id = StringProperty(
        name="Active Kit",
        description="Kit used to filter Melvil items in the Add menus",
        default="ALL_KITS",
    )
    bpy.types.Scene.melvil_mru_kit_id = StringProperty(
        name="Most Recently Used Kit",
        description="Kit most recently used when saving an asset",
        default="",
        options={"HIDDEN"},
    )
    bpy.types.WindowManager.melvil_active_tag_filters = StringProperty(
        name="Active Tag Filters",
        description="Comma-separated tag UUIDs active as browser filters",
        default="",
        options={"HIDDEN", "SKIP_SAVE"},
    )
    bpy.types.WindowManager.melvil_selected_asset_id = StringProperty(
        name="Selected Asset",
        description="UUID of the asset currently selected for detail view in the browser",
        default="",
        options={"HIDDEN", "SKIP_SAVE"},
    )
    bpy.types.WindowManager.melvil_asset_tags = CollectionProperty(
        name="Asset Tags",
        description="Tags for the currently selected asset in the browser detail panel",
        type=MelvilTagItem,
        options={"HIDDEN", "SKIP_SAVE"},
    )
    bpy.types.WindowManager.melvil_asset_tags_index = IntProperty(
        name="Asset Tags Index",
        default=0,
        options={"HIDDEN", "SKIP_SAVE"},
    )
    bpy.types.WindowManager.melvil_filter_tags = CollectionProperty(
        name="Filter Tags",
        description="Visible tags shown in the browser left-column filter list",
        type=MelvilFilterTagItem,
        options={"HIDDEN", "SKIP_SAVE"},
    )
    bpy.types.WindowManager.melvil_filter_tags_index = IntProperty(
        name="Filter Tags Index",
        default=-1,
        min=-1,
        options={"HIDDEN", "SKIP_SAVE"},
        update=_update_filter_tags_index,
    )


def unregister() -> None:
    del bpy.types.Scene.melvil_active_kit_id
    del bpy.types.Scene.melvil_mru_kit_id
    del bpy.types.WindowManager.melvil_active_tag_filters
    del bpy.types.WindowManager.melvil_selected_asset_id
    del bpy.types.WindowManager.melvil_asset_tags
    del bpy.types.WindowManager.melvil_asset_tags_index
    del bpy.types.WindowManager.melvil_filter_tags
    del bpy.types.WindowManager.melvil_filter_tags_index
    bpy.utils.unregister_class(MelvilTagItem)
    bpy.utils.unregister_class(MelvilFilterTagItem)
