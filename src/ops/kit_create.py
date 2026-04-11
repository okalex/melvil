"""MELVIL_OT_kit_create — create a new named kit."""

from __future__ import annotations

import uuid

import bpy
from bpy.props import StringProperty

from ..core.library import LibraryNotConfiguredError, resolve_db_path
from ..db import open_db
from ..db.kits import get_kit_by_name, insert_kit


class MELVIL_OT_kit_create(bpy.types.Operator):
    """Create a new kit in the Melvil library"""

    bl_idname = "melvil.kit_create"
    bl_label = "New Kit"
    bl_options = {"REGISTER"}

    name: StringProperty(
        name="Name",
        description="Name for the new kit (max 64 characters)",
        default="",
        maxlen=64,
    )

    description: StringProperty(
        name="Description",
        description="Optional description (max 256 characters)",
        default="",
        maxlen=256,
    )

    @classmethod
    def poll(cls, context):
        return True

    def invoke(self, context, event):
        self.name = ""
        self.description = ""
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "name")
        layout.prop(self, "description")

    def execute(self, context):
        name = self.name.strip()
        if not name:
            self.report({"ERROR"}, "Kit name cannot be empty.")
            return {"CANCELLED"}

        try:
            with open_db(resolve_db_path()) as conn:
                if get_kit_by_name(conn, name) is not None:
                    self.report({"ERROR"}, f"A kit named '{name}' already exists.")
                    return {"CANCELLED"}
                insert_kit(
                    conn,
                    id=str(uuid.uuid4()),
                    name=name,
                    description=self.description.strip() or None,
                )
                conn.commit()
        except LibraryNotConfiguredError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        except Exception as exc:  # noqa: BLE001
            self.report({"ERROR"}, f"Melvil: could not create kit — {exc}")
            return {"CANCELLED"}

        self.report({"INFO"}, f"Kit '{name}' created.")
        return {"FINISHED"}
