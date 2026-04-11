"""
MELVIL_OT_save_asset — save the active object or material to the library.

The operator presents a dialog letting the user choose what to save and
provide names for the asset(s):

- **Mesh** — saves the active object (must be of type ``MESH``) as a
  ``"MESH"`` asset.
- **Material** — saves the active material on the active object as a
  ``"MATERIAL"`` asset.
- **Both** — saves both as two separate assets in a single operator call.

The default selection adapts to the calling context:
- When invoked from a Node Editor (shader graph), *Material* is pre-selected.
- Otherwise, *Mesh* is pre-selected when an active object is present.
"""

from __future__ import annotations

import bpy
from bpy.props import EnumProperty, StringProperty

from ..core.asset_writer import AssetWriter
from ..core.library import LibraryNotConfiguredError, resolve_db_path, resolve_library_root
from ..db import open_db

_SAVE_TYPE_ITEMS = [
    ("MESH", "Mesh", "Save the active object as a managed mesh asset"),
    ("MATERIAL", "Material", "Save the active material as a managed material asset"),
    ("BOTH", "Both", "Save the active object and its active material as separate assets"),
]


class MELVIL_OT_save_asset(bpy.types.Operator):
    """Save the active object or material to the Melvil library"""

    bl_idname = "melvil.save_asset"
    bl_label = "Save as Melvil Asset"
    bl_options = {"REGISTER"}

    save_type: EnumProperty(
        name="Save as",
        description="Which datablock(s) to save to the library",
        items=_SAVE_TYPE_ITEMS,
        default="MESH",
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
        layout.prop(self, "save_type")
        if self.save_type in {"MESH", "BOTH"}:
            layout.prop(self, "mesh_name")
        if self.save_type in {"MATERIAL", "BOTH"}:
            layout.prop(self, "material_name")

    def execute(self, context):
        obj = context.active_object
        mat = getattr(obj, "active_material", None) if obj else None

        # ------------------------------------------------------------------
        # Validate inputs before touching the filesystem.
        # ------------------------------------------------------------------
        if self.save_type in {"MESH", "BOTH"}:
            if obj is None or obj.type != "MESH":
                self.report({"ERROR"}, "Melvil: no active mesh object to save.")
                return {"CANCELLED"}
            if not self.mesh_name.strip():
                self.report({"ERROR"}, "Melvil: mesh name cannot be empty.")
                return {"CANCELLED"}

        if self.save_type in {"MATERIAL", "BOTH"}:
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

                if self.save_type in {"MESH", "BOTH"}:
                    asset_id = writer.write(obj, self.mesh_name.strip(), "MESH")
                    self.report(
                        {"INFO"},
                        f"Melvil: mesh '{self.mesh_name.strip()}' saved (id: {asset_id[:8]}…)",
                    )

                if self.save_type in {"MATERIAL", "BOTH"}:
                    asset_id = writer.write(mat, self.material_name.strip(), "MATERIAL")
                    self.report(
                        {"INFO"},
                        f"Melvil: material '{self.material_name.strip()}' saved (id: {asset_id[:8]}…)",
                    )

        except Exception as exc:  # noqa: BLE001
            self.report({"ERROR"}, f"Melvil: save failed — {exc}")
            return {"CANCELLED"}

        return {"FINISHED"}
