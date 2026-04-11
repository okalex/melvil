"""
MELVIL_OT_save_asset — save the active object or material to the library.

The operator presents a dialog for the user to confirm the asset name.
The asset type is inferred automatically from context:

- When invoked from a Node Editor or Properties editor with an active
  material, the material is saved as a ``"MATERIAL"`` asset.
- Otherwise the active object is saved as a ``"MESH"`` asset.

No manual type selection is required from the user.
"""

from __future__ import annotations

import bpy
from bpy.props import StringProperty

from ..core.asset_writer import AssetWriter
from ..core.library import LibraryNotConfiguredError, resolve_db_path, resolve_library_root
from ..db import open_db


class MELVIL_OT_save_asset(bpy.types.Operator):
    """Save the active object or material to the Melvil library"""

    bl_idname = "melvil.save_asset"
    bl_label = "Save as Melvil Asset"
    bl_options = {"REGISTER"}

    # Set automatically in invoke() based on context; hidden from the dialog.
    save_type: StringProperty(
        name="Save as",
        default="MESH",
        options={"HIDDEN"},
    )

    mesh_name: StringProperty(
        name="Mesh Name",
        description="Name for the new mesh asset",
        default="",
    )

    material_name: StringProperty(
        name="Material Name",
        description="Name for the new material asset",
        default="",
    )

    # ------------------------------------------------------------------
    # Blender operator interface
    # ------------------------------------------------------------------

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def invoke(self, context, event):
        obj = context.active_object
        mat = getattr(obj, "active_material", None)
        area_type = getattr(getattr(context, "area", None), "type", None)

        # Pre-fill names from current scene data.
        if obj:
            self.mesh_name = obj.name
        if mat:
            self.material_name = mat.name

        # Pick a sensible default save_type based on context.
        if area_type == "NODE_EDITOR" and mat:
            self.save_type = "MATERIAL"
        elif area_type == "PROPERTIES" and mat:
            # Invoked from the Properties editor (e.g. material slot context
            # menu) — the user is clearly working with a material.
            self.save_type = "MATERIAL"
        elif obj and obj.type == "MESH" and mat:
            self.save_type = "MESH"
        elif mat:
            self.save_type = "MATERIAL"
        else:
            self.save_type = "MESH"

        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        if self.save_type == "MESH":
            layout.prop(self, "mesh_name")
        elif self.save_type == "MATERIAL":
            layout.prop(self, "material_name")

    def execute(self, context):
        obj = context.active_object
        mat = getattr(obj, "active_material", None) if obj else None

        # ------------------------------------------------------------------
        # Validate inputs before touching the filesystem.
        # ------------------------------------------------------------------
        if self.save_type == "MESH":
            if obj is None or obj.type != "MESH":
                self.report({"ERROR"}, "Melvil: no active mesh object to save.")
                return {"CANCELLED"}
            if not self.mesh_name.strip():
                self.report({"ERROR"}, "Melvil: mesh name cannot be empty.")
                return {"CANCELLED"}

        elif self.save_type == "MATERIAL":
            if mat is None:
                self.report({"ERROR"}, "Melvil: no active material on the selected object.")
                return {"CANCELLED"}
            if not self.material_name.strip():
                self.report({"ERROR"}, "Melvil: material name cannot be empty.")
                return {"CANCELLED"}

        # ------------------------------------------------------------------
        # Resolve library paths.
        # ------------------------------------------------------------------
        try:
            library_root = resolve_library_root()
        except LibraryNotConfiguredError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}

        db_path = resolve_db_path()

        # ------------------------------------------------------------------
        # Write asset(s).
        # ------------------------------------------------------------------
        try:
            with open_db(db_path) as conn:
                writer = AssetWriter(library_root, conn)

                if self.save_type == "MESH":
                    asset_id = writer.write(obj, self.mesh_name.strip(), "MESH")
                    self.report(
                        {"INFO"},
                        f"Melvil: mesh '{self.mesh_name.strip()}' saved (id: {asset_id[:8]}…)",
                    )

                elif self.save_type == "MATERIAL":
                    asset_id = writer.write(mat, self.material_name.strip(), "MATERIAL")
                    self.report(
                        {"INFO"},
                        f"Melvil: material '{self.material_name.strip()}' saved (id: {asset_id[:8]}…)",
                    )

        except Exception as exc:  # noqa: BLE001
            self.report({"ERROR"}, f"Melvil: save failed — {exc}")
            return {"CANCELLED"}

        return {"FINISHED"}
