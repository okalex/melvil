"""MELVIL_OT_asset_edit_tags — edit the tags assigned to an asset."""

from __future__ import annotations

import bpy
from bpy.props import StringProperty

from ..core.library import LibraryNotConfiguredError, resolve_db_path
from ..db import open_db
from ..db.tags import add_asset_tag, clear_asset_tags, get_asset_tags, normalize_tag


class MELVIL_OT_asset_edit_tags(bpy.types.Operator):
    """Edit the tags assigned to a Melvil asset"""

    bl_idname = "melvil.asset_edit_tags"
    bl_label = "Edit Tags"
    bl_options = {"REGISTER", "INTERNAL"}

    asset_id: StringProperty(
        name="Asset ID",
        description="UUID of the target asset",
        default="",
        options={"HIDDEN"},
    )

    asset_name: StringProperty(
        name="Asset Name",
        description="Display name of the asset (for the dialog heading)",
        default="",
        options={"HIDDEN"},
    )

    tags: StringProperty(
        name="Tags",
        description="Comma-separated tag names",
        default="",
    )

    @classmethod
    def poll(cls, context):
        return True

    def invoke(self, context, event):
        asset_id = self.asset_id.strip()
        if not asset_id:
            self.report({"ERROR"}, "Melvil: no asset ID provided.")
            return {"CANCELLED"}

        try:
            with open_db(resolve_db_path()) as conn:
                current_names = get_asset_tags(conn, asset_id)
            self.tags = ", ".join(current_names)
        except LibraryNotConfiguredError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        except Exception as exc:  # noqa: BLE001
            self.report({"ERROR"}, f"Melvil: could not load tags — {exc}")
            return {"CANCELLED"}

        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        if self.asset_name:
            layout.label(text=self.asset_name)
        layout.prop(self, "tags", text="Tags")

    def execute(self, context):
        asset_id = self.asset_id.strip()
        if not asset_id:
            self.report({"ERROR"}, "Melvil: no asset ID provided.")
            return {"CANCELLED"}

        raw_names = [n.strip() for n in self.tags.split(",")]
        new_names = [normalize_tag(n) for n in raw_names]
        new_names = [n for n in new_names if n]

        try:
            with open_db(resolve_db_path()) as conn:
                clear_asset_tags(conn, asset_id)
                for name in new_names:
                    add_asset_tag(conn, asset_id, name)
                conn.commit()
        except LibraryNotConfiguredError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        except Exception as exc:  # noqa: BLE001
            self.report({"ERROR"}, f"Melvil: could not save tags — {exc}")
            return {"CANCELLED"}

        return {"FINISHED"}
