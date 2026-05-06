"""
BLAMMO_OT_set_preview_object — set the material preview mesh preference.

The selected mesh is stored in the addon preferences so it persists across
sessions.  The operator is surfaced in the N-panel via `operator_menu_enum`,
giving the user a native Blender dropdown.
"""

from __future__ import annotations

import sys

import bpy
from bpy.props import EnumProperty

from ..core.library import resolve_db_path
from ..db import open_db
from ..db.assets import list_assets
from ..preferences import BlammoPreferences

# Ordered list of built-in primitive items shown at the top of the menu.
_BUILTIN_ITEMS: list[tuple[str, str, str]] = [
    ("BUILTIN_UV_SPHERE", "UV Sphere", "Use a UV sphere as the preview mesh"),
    ("BUILTIN_CUBE", "Cube", "Use a cube as the preview mesh"),
    ("BUILTIN_TORUS", "Torus", "Use a torus as the preview mesh"),
    ("BUILTIN_MONKEY", "Monkey", "Use the Monkey (Suzanne) as the preview mesh"),
]

# Module-level cache keeps enum strings alive (Blender C GC requirement).
_enum_cache: list[tuple] = list(_BUILTIN_ITEMS)


def _get_items(self, context):
    global _enum_cache
    items = [
        (sys.intern(k), sys.intern(n), sys.intern(d))
        for k, n, d in _BUILTIN_ITEMS
    ]
    try:
        with open_db(resolve_db_path()) as conn:
            for row in list_assets(conn, type="MESH"):
                asset_id = sys.intern(str(row["id"]))
                asset_name = sys.intern(str(row["name"]))
                items.append((asset_id, asset_name, ""))
    except Exception:  # noqa: BLE001
        pass
    _enum_cache = items
    return _enum_cache


class BLAMMO_OT_set_preview_object(bpy.types.Operator):
    """Set the mesh object used for material preview images"""

    bl_idname = "blammo.set_preview_object"
    bl_label = "Material Preview Object"
    bl_options = {"REGISTER"}

    object_id: EnumProperty(
        name="Preview Object",
        description="Mesh to use when generating material preview images",
        items=_get_items,
        default=0,
    )

    def execute(self, context):
        prefs = context.preferences.addons.get(BlammoPreferences.bl_idname)
        if prefs is not None:
            prefs.preferences.material_preview_object = self.object_id
        return {"FINISHED"}
