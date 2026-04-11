"""MELVIL_OT_tag_rename — rename a tag globally."""

from __future__ import annotations

import bpy
from bpy.props import StringProperty

from ..core.library import LibraryNotConfiguredError, resolve_db_path
from ..db import open_db
from ..db.tags import get_tag_by_id, rename_tag


class MELVIL_OT_tag_rename(bpy.types.Operator):
    """Rename a tag globally across all assets"""

    bl_idname = "melvil.tag_rename"
    bl_label = "Rename Tag"
    bl_options = {"REGISTER"}

    tag_id: StringProperty(
        name="Tag ID",
        description="UUID of the tag to rename",
        default="",
        options={"HIDDEN"},
    )

    name: StringProperty(
        name="Name",
        description="New name for the tag",
        default="",
        maxlen=128,
    )

    @classmethod
    def poll(cls, context):
        return True

    def invoke(self, context, event):
        tag_id = self.tag_id.strip()
        if not tag_id:
            self.report({"ERROR"}, "Melvil: no tag ID provided.")
            return {"CANCELLED"}

        try:
            with open_db(resolve_db_path()) as conn:
                row = get_tag_by_id(conn, tag_id)
        except LibraryNotConfiguredError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        except Exception as exc:  # noqa: BLE001
            self.report({"ERROR"}, f"Melvil: could not load tag — {exc}")
            return {"CANCELLED"}

        if row is None:
            self.report({"ERROR"}, "Melvil: tag not found.")
            return {"CANCELLED"}

        self.name = row["name"]
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        self.layout.prop(self, "name")

    def execute(self, context):
        tag_id = self.tag_id.strip()
        if not tag_id:
            self.report({"ERROR"}, "Melvil: no tag ID provided.")
            return {"CANCELLED"}

        try:
            with open_db(resolve_db_path()) as conn:
                rename_tag(conn, tag_id, self.name)
                conn.commit()
        except LibraryNotConfiguredError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        except ValueError as exc:
            self.report({"ERROR"}, f"Melvil: {exc}")
            return {"CANCELLED"}
        except Exception as exc:  # noqa: BLE001
            self.report({"ERROR"}, f"Melvil: could not rename tag — {exc}")
            return {"CANCELLED"}

        self.report({"INFO"}, f"Melvil: tag renamed to '{self.name.strip()}'.")
        return {"FINISHED"}
