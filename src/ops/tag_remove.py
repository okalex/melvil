"""MELVIL_OT_tag_remove — remove a tag from an asset."""

from __future__ import annotations

import bpy
from bpy.props import StringProperty

from ..core.library import LibraryNotConfiguredError, resolve_db_path
from ..db import open_db
from ..db.tags import remove_asset_tag


class MELVIL_OT_tag_remove(bpy.types.Operator):
    """Remove a tag from a Melvil asset"""

    bl_idname = "melvil.tag_remove"
    bl_label = "Remove Tag"
    bl_options = {"REGISTER"}

    asset_id: StringProperty(
        name="Asset ID",
        description="UUID of the target asset",
        default="",
        options={"HIDDEN"},
    )

    tag_id: StringProperty(
        name="Tag ID",
        description="UUID of the tag to remove",
        default="",
        options={"HIDDEN"},
    )

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        asset_id = self.asset_id.strip()
        tag_id = self.tag_id.strip()

        if not asset_id:
            self.report({"ERROR"}, "Melvil: no asset ID provided.")
            return {"CANCELLED"}
        if not tag_id:
            self.report({"ERROR"}, "Melvil: no tag ID provided.")
            return {"CANCELLED"}

        try:
            with open_db(resolve_db_path()) as conn:
                remove_asset_tag(conn, asset_id, tag_id)
                conn.commit()
        except LibraryNotConfiguredError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        except Exception as exc:  # noqa: BLE001
            self.report({"ERROR"}, f"Melvil: could not remove tag — {exc}")
            return {"CANCELLED"}

        return {"FINISHED"}
