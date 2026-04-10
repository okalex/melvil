"""
MELVIL_OT_load_asset — append an asset from the library into the current scene.

Typical usage — the operator is invoked from the UI list with ``asset_id``
already set as a property::

    bpy.ops.melvil.load_asset(asset_id="<uuid>")

Post-load behaviour
-------------------
- **Mesh (Object) assets**: the appended object is linked to the active scene
  collection (``context.collection``) and made the active selection.
- **Material assets**: the material is appended into ``bpy.data.materials``
  and no scene placement is needed; the caller can assign it as required.

``bl_options`` includes ``"UNDO"`` so the append can be reversed with
Ctrl+Z.
"""

from __future__ import annotations

import bpy
from bpy.props import StringProperty

from ..core.asset_reader import AssetNotFoundError, AssetReader
from ..core.library import LibraryNotConfiguredError, resolve_db_path, resolve_library_root
from ..db import open_db


class MELVIL_OT_load_asset(bpy.types.Operator):
    """Append a Melvil asset into the current scene"""

    bl_idname = "melvil.load_asset"
    bl_label = "Load Melvil Asset"
    bl_options = {"REGISTER", "UNDO"}

    asset_id: StringProperty(
        name="Asset ID",
        description="UUID of the asset to load from the library",
        default="",
    )

    # ------------------------------------------------------------------
    # Blender operator interface
    # ------------------------------------------------------------------

    @classmethod
    def poll(cls, context):
        return context.scene is not None

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
                reader = AssetReader(library_root, conn)
                datablock = reader.read(self.asset_id.strip())
        except AssetNotFoundError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        except Exception as exc:  # noqa: BLE001
            self.report({"ERROR"}, f"Melvil: load failed — {exc}")
            return {"CANCELLED"}

        if datablock is None:
            self.report({"ERROR"}, "Melvil: datablock not found inside managed .blend file.")
            return {"CANCELLED"}

        # Link object-type datablocks into the active collection.
        if hasattr(datablock, "users_collection"):
            context.collection.objects.link(datablock)
            if context.mode == "OBJECT":
                bpy.ops.object.select_all(action="DESELECT")
                datablock.select_set(True)
                context.view_layer.objects.active = datablock

        self.report({"INFO"}, f"Melvil: '{datablock.name}' loaded.")
        return {"FINISHED"}
