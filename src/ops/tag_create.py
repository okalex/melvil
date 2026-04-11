"""MELVIL_OT_tag_create — create a new tag independently of any asset."""

from __future__ import annotations

import bpy
from bpy.props import StringProperty

from ..core.library import LibraryNotConfiguredError, resolve_db_path
from ..db import open_db
from ..db.tags import get_or_create_tag, normalize_tag


class MELVIL_OT_tag_create(bpy.types.Operator):
    """Create a new tag in the library"""

    bl_idname = "melvil.tag_create"
    bl_label = "New Tag"
    bl_options = {"REGISTER"}

    name: StringProperty(
        name="Name",
        description="Name for the new tag",
        default="",
        maxlen=128,
    )

    @classmethod
    def poll(cls, context):
        return True

    def invoke(self, context, event):
        self.name = ""
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        self.layout.prop(self, "name")

    def execute(self, context):
        normalized = normalize_tag(self.name)
        if not normalized:
            self.report({"ERROR"}, "Melvil: tag name cannot be empty.")
            return {"CANCELLED"}

        try:
            with open_db(resolve_db_path()) as conn:
                get_or_create_tag(conn, normalized)
                conn.commit()
        except LibraryNotConfiguredError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        except Exception as exc:  # noqa: BLE001
            self.report({"ERROR"}, f"Melvil: could not create tag — {exc}")
            return {"CANCELLED"}

        self.report({"INFO"}, f"Melvil: tag '{normalized}' created.")
        return {"FINISHED"}
