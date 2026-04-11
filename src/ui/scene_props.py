"""
Scene-level properties for Melvil.

Registered on ``bpy.types.Scene`` so values persist with the .blend file.

Properties
----------
melvil_active_kit_id : str
    The kit currently active for filtering add-menu items.  ``"ALL_KITS"``
    means no kit filter is applied.

melvil_mru_kit_id : str
    The kit most recently used when saving an asset.  Empty string means no
    MRU kit has been recorded yet.  Used as a fallback default in the save
    dialog when the active kit is "All Kits".
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


def unregister() -> None:
    del bpy.types.Scene.melvil_active_kit_id
    del bpy.types.Scene.melvil_mru_kit_id
