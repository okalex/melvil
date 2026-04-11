"""
MELVIL_OT_add_node_group — append a saved node group into the active node
tree and place it at the cursor so it floats interactively.

Invoked from the Melvil sub-menu inside the Node Editor Add menu (Shift+A).

The operator:

1. Loads the ``NODE_GROUP`` asset from the managed .blend file.
2. Verifies the loaded group is compatible with the current node tree type.
3. Creates a group node of the correct bl_idname in the active node tree.
4. Positions it at the current mouse cursor in node space.
5. Hands off to ``node.translate_attach`` so the node floats interactively
   with the cursor until the user clicks to place it — identical to
   Blender's built-in node-add behaviour.
"""

from __future__ import annotations

import bpy
from bpy.props import StringProperty

from ..core.asset_reader import AssetNotFoundError, AssetReader
from ..core.library import LibraryNotConfiguredError, resolve_db_path, resolve_library_root
from ..db import open_db

# Maps the node tree .type attribute to the bl_idname for a group node
# inside that tree.  Blender uses separate subtypes per editor.
_TREE_TYPE_TO_GROUP_NODE: dict[str, str] = {
    "SHADER": "ShaderNodeGroup",
    "GEOMETRY": "GeometryNodeGroup",
    "COMPOSITING": "CompositorNodeGroup",
}


class MELVIL_OT_add_node_group(bpy.types.Operator):
    """Append a saved node group into the active node tree"""

    bl_idname = "melvil.add_node_group"
    bl_label = "Add Node Group"
    bl_options = {"REGISTER", "UNDO"}

    asset_id: StringProperty(
        name="Asset ID",
        description="UUID of the NODE_GROUP asset to load",
        default="",
        options={"HIDDEN"},
    )

    # ------------------------------------------------------------------
    # Blender operator interface
    # ------------------------------------------------------------------

    @classmethod
    def poll(cls, context):
        space = getattr(context, "space_data", None)
        return (
            getattr(getattr(context, "area", None), "type", None) == "NODE_EDITOR"
            and space is not None
            and getattr(space, "node_tree", None) is not None
        )

    def invoke(self, context, event):
        # --- Resolve library -----------------------------------------------
        try:
            library_root = resolve_library_root()
        except LibraryNotConfiguredError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}

        # --- Load the node group from the managed .blend -------------------
        db_path = resolve_db_path()
        try:
            with open_db(db_path) as conn:
                reader = AssetReader(library_root, conn)
                ng = reader.read(self.asset_id)
        except AssetNotFoundError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        except Exception as exc:  # noqa: BLE001
            self.report({"ERROR"}, f"Melvil: could not load node group — {exc}")
            return {"CANCELLED"}

        if ng is None:
            self.report({"ERROR"}, "Melvil: node group not found in the blend file.")
            return {"CANCELLED"}

        # --- Determine the group-node type for this editor -----------------
        node_tree = context.space_data.node_tree
        tree_type = getattr(node_tree, "type", None)
        group_node_type = _TREE_TYPE_TO_GROUP_NODE.get(tree_type)

        if group_node_type is None:
            self.report({"ERROR"}, f"Melvil: unsupported node tree type '{tree_type}'.")
            return {"CANCELLED"}

        # Verify the loaded group's type matches the editor.
        ng_type = getattr(ng, "type", None)
        if ng_type and ng_type != tree_type:
            self.report(
                {"ERROR"},
                f"Melvil: '{ng.name}' is a {ng_type} node group and cannot be added"
                f" to a {tree_type} node tree.",
            )
            return {"CANCELLED"}

        # --- Create the group node -----------------------------------------
        # Deselect everything so only the new node ends up selected.
        for node in node_tree.nodes:
            node.select = False

        group_node = node_tree.nodes.new(type=group_node_type)
        group_node.node_tree = ng
        group_node.select = True
        node_tree.nodes.active = group_node

        # Convert the mouse position to node-graph coordinates.
        #
        # Mirrors the C-side pattern used by every built-in add-node operator
        # (node_add.cc: node_add_group_invoke, etc.):
        #
        #   ARegion *region = CTX_wm_region(C);
        #   view2d_region_to_view(&region->v2d, event->mval[0], event->mval[1], &cx, &cy);
        #   cx /= UI_SCALE_FAC;  cy /= UI_SCALE_FAC;
        #
        # We find the WINDOW region explicitly so the calculation is correct
        # whether context.region is the canvas or a transient popup.  The
        # absolute mouse coords minus the region's screen origin give the same
        # region-local pixel pair as event->mval in C.
        #
        # The division by ui_scale is critical on HiDPI displays where
        # region_to_view returns scaled pixel units; without it the node
        # location is inflated (2× on a Retina screen) causing a large offset.
        #
        # translate_attach must also run with canvas_region as context.region
        # so its internal cursor→view conversion uses the same view2d and the
        # initial grab-offset is zero.
        canvas_region = next(
            (r for r in context.area.regions if r.type == "WINDOW"),
            context.region,  # fallback — should not be needed in practice
        )
        ui_scale = context.preferences.system.ui_scale
        x, y = canvas_region.view2d.region_to_view(
            event.mouse_x - canvas_region.x,
            event.mouse_y - canvas_region.y,
        )
        group_node.location = (x / ui_scale, y / ui_scale)

        # Hand off to interactive translate — node will float with the
        # cursor until the user clicks to confirm placement.
        with context.temp_override(region=canvas_region):
            bpy.ops.node.translate_attach("INVOKE_DEFAULT")
        return {"RUNNING_MODAL"}
