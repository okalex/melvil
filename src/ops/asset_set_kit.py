"""MELVIL_OT_asset_set_kit — reassign an asset to a different kit."""

from __future__ import annotations

import bpy
from bpy.props import EnumProperty, StringProperty

from ..core.library import LibraryNotConfiguredError, resolve_db_path
from ..db import open_db
from ..db.assets import get_asset, update_asset
from ..db.kits import list_kits

# Module-level cache to prevent Blender from garbage-collecting enum strings.
_kit_items_cache: list[tuple] = []


def _get_kit_items(self, context):
    items = []
    try:
        with open_db(resolve_db_path()) as conn:
            kits = list_kits(conn)
        for i, kit in enumerate(kits):
            items.append((kit["id"], kit["name"], "", "FOLDER_CURRENT", i))
    except Exception:  # noqa: BLE001
        pass
    _kit_items_cache[:] = items
    return _kit_items_cache


class MELVIL_OT_asset_set_kit(bpy.types.Operator):
    """Move this asset to a different kit"""

    bl_idname = "melvil.asset_set_kit"
    bl_label = "Move to Kit"
    bl_options = {"REGISTER"}

    asset_id: StringProperty(
        name="Asset ID",
        description="UUID of the asset to reassign",
        default="",
        options={"HIDDEN"},
    )

    kit_id: EnumProperty(
        name="Kit",
        description="Destination kit",
        items=_get_kit_items,
        default=0,
    )

    @classmethod
    def poll(cls, context):
        return True

    def invoke(self, context, event):
        if not self.asset_id.strip():
            self.report({"ERROR"}, "No asset ID provided.")
            return {"CANCELLED"}
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        self.layout.prop(self, "kit_id")

    def execute(self, context):
        asset_id = self.asset_id.strip()
        kit_id = self.kit_id

        if not asset_id:
            self.report({"ERROR"}, "No asset ID provided.")
            return {"CANCELLED"}

        if not kit_id:
            self.report({"ERROR"}, "No kit selected.")
            return {"CANCELLED"}

        try:
            with open_db(resolve_db_path()) as conn:
                if get_asset(conn, asset_id) is None:
                    self.report({"ERROR"}, f"Asset '{asset_id}' not found.")
                    return {"CANCELLED"}
                update_asset(conn, asset_id, kit_id=kit_id)
                conn.commit()
        except LibraryNotConfiguredError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        except Exception as exc:  # noqa: BLE001
            self.report({"ERROR"}, f"Melvil: could not move asset — {exc}")
            return {"CANCELLED"}

        return {"FINISHED"}
