"""asset_rename — asset name editing for Blammo.

Contains ``BLAMMO_OT_asset_name_confirm``, the operator invoked by the
inline checkmark button in the browser detail panel.  It reads the draft
name from ``context.window_manager.blammo_pending_name`` and writes it to
the database via ``update_asset``.
"""

from __future__ import annotations

import bpy
from bpy.props import StringProperty

from ..core.library import LibraryNotConfiguredError, resolve_db_path
from ..db import open_db
from ..db.assets import get_asset, update_asset


class BLAMMO_OT_asset_rename(bpy.types.Operator):
    """Rename a Blammo asset"""

    bl_idname = "blammo.asset_rename"
    bl_label = "Rename Asset"
    bl_options = {"REGISTER"}

    asset_id: StringProperty(
        name="Asset ID",
        description="UUID of the asset to rename",
        default="",
        options={"HIDDEN"},
    )

    name: StringProperty(
        name="Name",
        description="New name for the asset",
        default="",
    )

    # ------------------------------------------------------------------
    # Blender operator interface
    # ------------------------------------------------------------------

    @classmethod
    def poll(cls, context):
        return True

    def invoke(self, context, event):
        asset_id = self.asset_id.strip()
        if not asset_id:
            self.report({"ERROR"}, "Blammo!: no asset ID provided.")
            return {"CANCELLED"}

        try:
            with open_db(resolve_db_path()) as conn:
                row = get_asset(conn, asset_id)
        except LibraryNotConfiguredError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        except Exception as exc:  # noqa: BLE001
            self.report({"ERROR"}, f"Blammo!: could not load asset — {exc}")
            return {"CANCELLED"}

        if row is None:
            self.report({"ERROR"}, f"Blammo!: asset '{asset_id}' not found.")
            return {"CANCELLED"}

        self.name = row["name"]
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        self.layout.prop(self, "name")

    def execute(self, context):
        asset_id = self.asset_id.strip()
        name = self.name.strip()

        if not asset_id:
            self.report({"ERROR"}, "Blammo!: no asset ID provided.")
            return {"CANCELLED"}

        if not name:
            self.report({"ERROR"}, "Blammo!: asset name cannot be empty.")
            return {"CANCELLED"}

        try:
            with open_db(resolve_db_path()) as conn:
                if get_asset(conn, asset_id) is None:
                    self.report({"ERROR"}, f"Blammo!: asset '{asset_id}' not found.")
                    return {"CANCELLED"}
                update_asset(conn, asset_id, name=name)
                conn.commit()
        except LibraryNotConfiguredError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        except Exception as exc:  # noqa: BLE001
            self.report({"ERROR"}, f"Blammo!: could not rename asset — {exc}")
            return {"CANCELLED"}

        self.report({"INFO"}, f"Blammo!: asset renamed to '{name}'.")
        return {"FINISHED"}


# ---------------------------------------------------------------------------
# Inline confirm operator
# ---------------------------------------------------------------------------


class BLAMMO_OT_asset_name_confirm(bpy.types.Operator):
    """Confirm the inline asset name edit in the browser detail panel"""

    bl_idname = "blammo.asset_name_confirm"
    bl_label = "Confirm Name"
    bl_options = {"REGISTER"}

    asset_id: StringProperty(
        name="Asset ID",
        description="UUID of the asset to rename",
        default="",
        options={"HIDDEN"},
    )

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        asset_id = self.asset_id.strip()
        name = context.window_manager.blammo_pending_name.strip()

        if not asset_id:
            self.report({"ERROR"}, "Blammo!: no asset ID provided.")
            return {"CANCELLED"}

        if not name:
            self.report({"ERROR"}, "Blammo!: asset name cannot be empty.")
            return {"CANCELLED"}

        try:
            with open_db(resolve_db_path()) as conn:
                if get_asset(conn, asset_id) is None:
                    self.report({"ERROR"}, f"Blammo!: asset '{asset_id}' not found.")
                    return {"CANCELLED"}
                update_asset(conn, asset_id, name=name)
                conn.commit()
        except LibraryNotConfiguredError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        except Exception as exc:  # noqa: BLE001
            self.report({"ERROR"}, f"Blammo!: could not rename asset — {exc}")
            return {"CANCELLED"}

        # Reset so draw_asset_details re-syncs the pending name from the DB
        # on the next draw, showing the newly saved name with the button grey.
        context.window_manager.blammo_pending_name_asset_id = ""
        self.report({"INFO"}, f"Blammo!: asset renamed to '{name}'.")
        return {"FINISHED"}


def register() -> None:
    bpy.utils.register_class(BLAMMO_OT_asset_name_confirm)


def unregister() -> None:
    bpy.utils.unregister_class(BLAMMO_OT_asset_name_confirm)
