"""BLAMMO_OT_kit_rename — rename an existing kit."""

from __future__ import annotations

import bpy
from bpy.props import StringProperty

from ..core.library import LibraryNotConfiguredError, resolve_db_path
from ..db import open_db
from ..db.kits import get_kit, get_kit_by_name, update_kit


class BLAMMO_OT_kit_rename(bpy.types.Operator):
    """Rename the specified kit"""

    bl_idname = "blammo.kit_rename"
    bl_label = "Rename Kit"
    bl_options = {"REGISTER"}

    kit_id: StringProperty(
        name="Kit ID",
        description="UUID of the kit to rename",
        default="",
        options={"HIDDEN"},
    )

    name: StringProperty(
        name="Name",
        description="New name for the kit (max 64 characters)",
        default="",
        maxlen=64,
    )

    @classmethod
    def poll(cls, context):
        return True

    def invoke(self, context, event):
        if not self.kit_id.strip():
            self.report({"ERROR"}, "No kit selected.")
            return {"CANCELLED"}

        try:
            with open_db(resolve_db_path()) as conn:
                row = get_kit(conn, self.kit_id.strip())
        except LibraryNotConfiguredError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        except Exception as exc:  # noqa: BLE001
            self.report({"ERROR"}, f"Blammo!: could not load kit — {exc}")
            return {"CANCELLED"}

        if row is None:
            self.report({"ERROR"}, "Kit not found.")
            return {"CANCELLED"}

        self.name = row["name"]
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        self.layout.prop(self, "name")

    def execute(self, context):
        name = self.name.strip()
        if not name:
            self.report({"ERROR"}, "Kit name cannot be empty.")
            return {"CANCELLED"}

        kit_id = self.kit_id.strip()

        try:
            with open_db(resolve_db_path()) as conn:
                existing = get_kit_by_name(conn, name)
                if existing is not None and existing["id"] != kit_id:
                    self.report({"ERROR"}, f"A kit named '{name}' already exists.")
                    return {"CANCELLED"}
                update_kit(conn, kit_id, name=name)
                conn.commit()
        except LibraryNotConfiguredError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        except Exception as exc:  # noqa: BLE001
            self.report({"ERROR"}, f"Blammo!: could not rename kit — {exc}")
            return {"CANCELLED"}

        self.report({"INFO"}, f"Kit renamed to '{name}'.")
        return {"FINISHED"}
