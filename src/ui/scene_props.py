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
from bpy.props import StringProperty


def register() -> None:
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
    bpy.types.WindowManager.melvil_tag_sort = StringProperty(
        name="Tag Sort Order",
        description="Current sort order for the tag management section: 'NAME' or 'USAGE'",
        default="NAME",
        options={"HIDDEN", "SKIP_SAVE"},
    )


def unregister() -> None:
    del bpy.types.Scene.melvil_active_kit_id
    del bpy.types.Scene.melvil_mru_kit_id
    del bpy.types.WindowManager.melvil_active_tag_filters
    del bpy.types.WindowManager.melvil_tag_sort
