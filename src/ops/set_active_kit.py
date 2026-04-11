"""
MELVIL_OT_set_active_kit — set the active kit on the current scene.

The active kit is stored as a StringProperty on ``bpy.types.Scene`` so it
persists with the .blend file.  Other Melvil features (add-menu items, save
dialog default) read ``context.scene.melvil_active_kit_id`` to react.

This operator is surfaced in the N-panel as an ``operator_menu_enum`` button,
giving the user a native Blender dropdown to pick the active kit.
"""

from __future__ import annotations

import sys

import bpy
from bpy.props import EnumProperty

from ..core.library import resolve_db_path
from ..db import open_db
from ..db.kits import list_kits

# Module-level cache keeps enum strings alive (Blender C GC requirement).
# sys.intern() pins them permanently in Python's intern table.
_kit_enum_cache: list[tuple] = [("ALL_KITS", "All Kits", "")]


def _get_kit_items(self, context):
    global _kit_enum_cache
    items = [
        (sys.intern("ALL_KITS"), sys.intern("All Kits"), sys.intern("Show assets from all kits")),
    ]
    try:
        with open_db(resolve_db_path()) as conn:
            for kit in list_kits(conn):
                kit_id = sys.intern(str(kit["id"]))
                kit_name = sys.intern(str(kit["name"]))
                kit_desc = sys.intern(str(kit["description"] or ""))
                items.append((kit_id, kit_name, kit_desc))
    except Exception:  # noqa: BLE001
        pass
    _kit_enum_cache = items
    return _kit_enum_cache


class MELVIL_OT_set_active_kit(bpy.types.Operator):
    """Set the active kit used to filter Melvil items in the Add menus"""

    bl_idname = "melvil.set_active_kit"
    bl_label = "Active Kit"
    bl_options = {"REGISTER", "UNDO"}

    kit_id: EnumProperty(
        name="Kit",
        description="Kit to set as active",
        items=_get_kit_items,
        default=0,
    )

    def execute(self, context):
        scene = getattr(context, "scene", None)
        if scene is not None:
            scene.melvil_active_kit_id = self.kit_id
        return {"FINISHED"}
