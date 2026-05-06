"""BLAMMO_OT_tag_create — create a new tag independently of any asset."""

from __future__ import annotations

import bpy
from bpy.props import StringProperty

from ..core.library import LibraryNotConfiguredError, resolve_db_path
from ..db import open_db
from ..db.tags import get_or_create_tag, normalize_tag


class BLAMMO_OT_tag_create(bpy.types.Operator):
    """Create one or more new tags in the library"""

    bl_idname = "blammo.tag_create"
    bl_label = "New Tag"
    bl_options = {"REGISTER"}

    names: StringProperty(
        name="Tags",
        description="Comma-separated tag names to create",
        default="",
    )

    @classmethod
    def poll(cls, context):
        return True

    def invoke(self, context, event):
        self.names = ""
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        self.layout.prop(self, "names")

    def execute(self, context):
        raw_names = [t for t in (n.strip() for n in self.names.split(",")) if t]
        normalized = [normalize_tag(n) for n in raw_names]
        normalized = [n for n in normalized if n]

        if not normalized:
            self.report({"ERROR"}, "Blammo!: tag name cannot be empty.")
            return {"CANCELLED"}

        try:
            with open_db(resolve_db_path()) as conn:
                for name in normalized:
                    get_or_create_tag(conn, name)
                conn.commit()
        except LibraryNotConfiguredError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        except Exception as exc:  # noqa: BLE001
            self.report({"ERROR"}, f"Blammo!: could not create tag — {exc}")
            return {"CANCELLED"}

        self.report({"INFO"}, f"Blammo!: created {len(normalized)} tag(s).")
        return {"FINISHED"}
