"""BLAMMO_OT_tag_add — apply one or more tags to an asset."""

from __future__ import annotations

import bpy
from bpy.props import StringProperty

from ..core.library import LibraryNotConfiguredError, resolve_db_path
from ..db import open_db
from ..db.tags import add_asset_tag, normalize_tag


class BLAMMO_OT_tag_add(bpy.types.Operator):
    """Apply one or more tags to a Blammo asset"""

    bl_idname = "blammo.tag_add"
    bl_label = "Add Tags"
    bl_options = {"REGISTER"}

    asset_id: StringProperty(
        name="Asset ID",
        description="UUID of the target asset",
        default="",
        options={"HIDDEN"},
    )

    tags: StringProperty(
        name="Tags",
        description="Comma-separated tag names to apply",
        default="",
    )

    @classmethod
    def poll(cls, context):
        return True

    def invoke(self, context, event):
        self.tags = ""
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        self.layout.prop(self, "tags", text="Tags")

    def execute(self, context):
        asset_id = self.asset_id.strip()
        if not asset_id:
            self.report({"ERROR"}, "Blammo!: no asset ID provided.")
            return {"CANCELLED"}

        raw_names = [t for t in (n.strip() for n in self.tags.split(",")) if t]
        names = [normalize_tag(n) for n in raw_names]
        names = [n for n in names if n]

        if not names:
            self.report({"WARNING"}, "Blammo!: no valid tag names provided.")
            return {"CANCELLED"}

        try:
            with open_db(resolve_db_path()) as conn:
                for name in names:
                    add_asset_tag(conn, asset_id, name)
                conn.commit()
        except LibraryNotConfiguredError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        except Exception as exc:  # noqa: BLE001
            self.report({"ERROR"}, f"Blammo!: could not add tags — {exc}")
            return {"CANCELLED"}

        self.report({"INFO"}, f"Blammo!: added {len(names)} tag(s) to asset.")
        return {"FINISHED"}
