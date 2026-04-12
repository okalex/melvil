"""
MELVIL_OT_save_asset — save the active object, material, or node group to
the library.

The operator presents a dialog for the user to confirm the asset name.
The asset type is inferred automatically from context:

- When invoked from a Node Editor with a ``GROUP``-type node active, the
  referenced node group (and all its nested dependencies) is saved as a
  ``"NODE_GROUP"`` asset.
- When invoked from a Node Editor or Properties editor with an active
  material (and no active group node), the material is saved as a
  ``"MATERIAL"`` asset.
- Otherwise the active object is saved as a ``"MESH"`` asset.

No manual type selection is required from the user.
"""

from __future__ import annotations

import sys
from pathlib import Path

import bpy
from bpy.props import EnumProperty, StringProperty

from ..core.asset_writer import AssetWriter
from ..core.library import LibraryNotConfiguredError, resolve_db_path, resolve_library_root
from ..core.preview import generate_material_preview, generate_mesh_preview
from ..db import open_db
from ..db.assets import get_asset, update_asset
from ..db.kits import DEFAULT_KIT_ID, list_kits
from ..db.tags import add_asset_tag, normalize_tag
from ..preferences import MelvilPreferences

# Module-level cache keeps kit enum strings alive (Blender C GC requirement).
_save_kit_enum_cache: list[tuple] = [(DEFAULT_KIT_ID, "General", "")]


def _get_save_kit_items(self, context):
    """Enum callback: one item per kit (no All-Kits sentinel — save always targets a kit)."""
    global _save_kit_enum_cache
    items: list[tuple] = []
    try:
        with open_db(resolve_db_path()) as conn:
            for kit in list_kits(conn):
                kit_id = sys.intern(str(kit["id"]))
                kit_name = sys.intern(str(kit["name"]))
                kit_desc = sys.intern(str(kit["description"] or ""))
                items.append((kit_id, kit_name, kit_desc))
    except Exception:  # noqa: BLE001
        pass
    if not items:
        # Fallback so the enum is never empty (Blender requires ≥ 1 item).
        items = [(sys.intern(DEFAULT_KIT_ID), sys.intern("General"), sys.intern(""))]
    _save_kit_enum_cache = items
    return _save_kit_enum_cache


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

    node_group_name: StringProperty(
        name="Node Group Name",
        description="Name for the new node group asset",
        default="",
    )

    kit_id: EnumProperty(
        name="Kit",
        description="Kit to save the asset into",
        items=_get_save_kit_items,
        default=0,
    )

    tags: StringProperty(
        name="Tags",
        description="Comma-separated tag names to apply to this asset",
        default="",
    )

    # ------------------------------------------------------------------
    # Blender operator interface
    # ------------------------------------------------------------------

    @classmethod
    def poll(cls, context):
        if context.active_object is not None:
            return True
        # Also allow invocation when a GROUP node is active in the node editor,
        # even if there is no active object.
        active_node = getattr(context, "active_node", None)
        return (
            active_node is not None
            and getattr(active_node, "type", None) == "GROUP"
            and getattr(active_node, "node_tree", None) is not None
        )

    def invoke(self, context, event):
        obj = context.active_object
        mat = getattr(obj, "active_material", None)
        area_type = getattr(getattr(context, "area", None), "type", None)
        active_node = getattr(context, "active_node", None)

        # Pre-fill names from current scene data.
        if obj:
            self.mesh_name = obj.name
        if mat:
            self.material_name = mat.name

        # Pick a sensible default save_type based on context.
        # NODE_EDITOR + active GROUP node → save the node group.
        if (
            area_type == "NODE_EDITOR"
            and active_node is not None
            and getattr(active_node, "type", None) == "GROUP"
            and getattr(active_node, "node_tree", None) is not None
        ):
            self.save_type = "NODE_GROUP"
            # Prefer the node's user-visible label (set via F2 / double-click
            # on the header) over the underlying NodeTree datablock name.
            self.node_group_name = (
                getattr(active_node, "label", None) or active_node.node_tree.name
            )
        elif area_type == "NODE_EDITOR" and mat:
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

        # Resolve the default kit from scene state.
        scene = getattr(context, "scene", None)
        active_kit_id = getattr(scene, "melvil_active_kit_id", None)
        if not isinstance(active_kit_id, str):
            active_kit_id = "ALL_KITS"
        mru_kit_id = getattr(scene, "melvil_mru_kit_id", None)
        if not isinstance(mru_kit_id, str):
            mru_kit_id = ""

        if active_kit_id != "ALL_KITS":
            desired_kit_id = active_kit_id
        elif mru_kit_id:
            desired_kit_id = mru_kit_id
        else:
            desired_kit_id = DEFAULT_KIT_ID

        # Prime the enum cache before assigning so the identifier is valid.
        _get_save_kit_items(self, context)
        self.kit_id = desired_kit_id

        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "kit_id", text="Kit")
        if self.save_type == "MESH":
            layout.prop(self, "mesh_name", text="Name")
        elif self.save_type == "MATERIAL":
            layout.prop(self, "material_name", text="Name")
        elif self.save_type == "NODE_GROUP":
            layout.prop(self, "node_group_name", text="Name")
        layout.prop(self, "tags", text="Tags")

    def execute(self, context):
        obj = context.active_object
        mat = getattr(obj, "active_material", None) if obj else None
        active_node = getattr(context, "active_node", None)

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

        elif self.save_type == "NODE_GROUP":
            node_tree = (
                getattr(active_node, "node_tree", None)
                if active_node is not None
                else None
            )
            if node_tree is None:
                self.report({"ERROR"}, "Melvil: no active node group to save.")
                return {"CANCELLED"}
            if not self.node_group_name.strip():
                self.report({"ERROR"}, "Melvil: node group name cannot be empty.")
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
        kit_id = getattr(self, "kit_id", DEFAULT_KIT_ID) or DEFAULT_KIT_ID
        try:
            with open_db(db_path) as conn:
                writer = AssetWriter(library_root, conn)

                if self.save_type == "MESH":
                    asset_id = writer.write(obj, self.mesh_name.strip(), "MESH", kit_id=kit_id)
                    self.report(
                        {"INFO"},
                        f"Melvil: mesh '{self.mesh_name.strip()}' saved (id: {asset_id[:8]}…)",
                    )

                elif self.save_type == "MATERIAL":
                    asset_id = writer.write(mat, self.material_name.strip(), "MATERIAL", kit_id=kit_id)
                    self.report(
                        {"INFO"},
                        f"Melvil: material '{self.material_name.strip()}' saved (id: {asset_id[:8]}…)",
                    )

                elif self.save_type == "NODE_GROUP":
                    node_tree = getattr(active_node, "node_tree", None)
                    asset_id = writer.write(node_tree, self.node_group_name.strip(), "NODE_GROUP", kit_id=kit_id)
                    self.report(
                        {"INFO"},
                        f"Melvil: node group '{self.node_group_name.strip()}' saved (id: {asset_id[:8]}…)",
                    )

                # Apply any tags specified in the dialog.
                tag_names = [
                    normalize_tag(t)
                    for t in (getattr(self, "tags", None) or "").split(",")
                    if normalize_tag(t)
                ]
                for tag_name in tag_names:
                    add_asset_tag(conn, asset_id, tag_name)
                if tag_names:
                    conn.commit()

                # Generate a preview image for MESH and MATERIAL assets.
                # Node groups are skipped for now (out of scope).
                # Skipped entirely when the user has disabled auto-generation.
                _prefs = context.preferences.addons.get(MelvilPreferences.bl_idname)
                _auto_preview = _prefs.preferences.auto_generate_previews if _prefs else True
                if _auto_preview and self.save_type in ("MESH", "MATERIAL"):
                    previews_dir = Path(library_root) / "previews"
                    if self.save_type == "MESH":
                        abs_preview = generate_mesh_preview(context, obj, asset_id, previews_dir)
                    else:
                        _prev_mesh_id = (
                            _prefs.preferences.material_preview_object
                            if _prefs else "BUILTIN_UV_SPHERE"
                        )
                        if not isinstance(_prev_mesh_id, str) or not _prev_mesh_id:
                            _prev_mesh_id = "BUILTIN_UV_SPHERE"
                        _prev_blend_path = None
                        _prev_obj_name = None
                        if not _prev_mesh_id.startswith("BUILTIN_"):
                            _prev_row = get_asset(conn, _prev_mesh_id)
                            if _prev_row:
                                _prev_blend_path = str(
                                    Path(library_root) / _prev_row["blend_path"]
                                )
                                _prev_obj_name = str(_prev_row["name"])
                        abs_preview = generate_material_preview(
                            context, mat, asset_id, previews_dir,
                            preview_mesh_id=_prev_mesh_id,
                            preview_mesh_blend_path=_prev_blend_path,
                            preview_mesh_obj_name=_prev_obj_name,
                        )

                    if abs_preview is not None:
                        relative_preview = f"previews/{asset_id}.png"
                        update_asset(conn, asset_id, preview_path=relative_preview)
                        conn.commit()
                    else:
                        self.report(
                            {"WARNING"},
                            "Melvil: preview generation failed, asset saved without preview.",
                        )

        except Exception as exc:  # noqa: BLE001
            self.report({"ERROR"}, f"Melvil: save failed — {exc}")
            return {"CANCELLED"}

        # Update MRU kit on successful save.
        scene = getattr(context, "scene", None)
        if scene is not None:
            try:
                scene.melvil_mru_kit_id = kit_id
            except Exception:  # noqa: BLE001
                pass

        return {"FINISHED"}


class MELVIL_OT_save_nodes_as_asset(bpy.types.Operator):
    """Save the selected node group as a Melvil asset.

    Enabled only when exactly one GROUP-type node is selected.  Selecting
    multiple nodes or a non-group node disables the operator (shown grayed
    out in the context menu).
    """

    bl_idname = "melvil.save_nodes_as_asset"
    bl_label = "Save as Melvil Asset"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        if getattr(getattr(context, "area", None), "type", None) != "NODE_EDITOR":
            return False
        space = getattr(context, "space_data", None)
        node_tree = getattr(space, "node_tree", None) if space else None
        if node_tree is None:
            return False
        selected = [n for n in node_tree.nodes if getattr(n, "select", False)]
        return (
            len(selected) == 1
            and getattr(selected[0], "type", None) == "GROUP"
            and getattr(selected[0], "node_tree", None) is not None
        )

    def invoke(self, context, event):
        return bpy.ops.melvil.save_asset("INVOKE_DEFAULT")
