"""
MELVIL_OT_delete_asset — permanently remove an asset from the library.

The operator presents a confirmation dialog before proceeding.  On
confirmation it:

1. Looks up the asset in the database.
2. Deletes the managed ``.blend`` file from the library root.
3. Removes the database record.

Texture files in ``<library_root>/textures/`` are **not** removed because
they may be shared by other assets.  A dedicated cleanup operator can be
added in a later milestone if needed.
"""

from __future__ import annotations

import bpy
from bpy.props import StringProperty

from ..core.library import LibraryNotConfiguredError, resolve_db_path, resolve_library_root
from ..db import open_db
from ..db.assets import delete_asset, get_asset


class MELVIL_OT_delete_asset(bpy.types.Operator):
    """Permanently remove an asset from the Melvil library"""

    bl_idname = "melvil.delete_asset"
    bl_label = "Delete Melvil Asset"
    bl_options = {"REGISTER"}

    asset_id: StringProperty(
        name="Asset ID",
        description="UUID of the asset to delete",
        default="",
    )

    # ------------------------------------------------------------------
    # Blender operator interface
    # ------------------------------------------------------------------

    @classmethod
    def poll(cls, context):
        return True

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        if not self.asset_id.strip():
            self.report({"ERROR"}, "Melvil: no asset ID provided.")
            return {"CANCELLED"}

        try:
            library_root = resolve_library_root()
        except LibraryNotConfiguredError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}

        try:
            with open_db(resolve_db_path()) as conn:
                row = get_asset(conn, self.asset_id.strip())
                if row is None:
                    self.report(
                        {"ERROR"},
                        f"Melvil: asset '{self.asset_id}' not found in the database.",
                    )
                    return {"CANCELLED"}

                asset_name = row["name"]
                blend_path = library_root / row["blend_path"]
                preview_path = row["preview_path"]

                # Remove the managed .blend file if it still exists.
                if blend_path.exists():
                    blend_path.unlink()

                # Remove the database record.
                delete_asset(conn, self.asset_id.strip())
                conn.commit()

                # Remove the preview PNG if one was generated.
                if preview_path:
                    abs_preview = library_root / preview_path
                    try:
                        abs_preview.unlink(missing_ok=True)
                    except OSError:
                        pass  # non-fatal; orphaned preview files are harmless

        except Exception as exc:  # noqa: BLE001
            self.report({"ERROR"}, f"Melvil: delete failed — {exc}")
            return {"CANCELLED"}

        self.report({"INFO"}, f"Melvil: asset '{asset_name}' deleted.")
        return {"FINISHED"}
