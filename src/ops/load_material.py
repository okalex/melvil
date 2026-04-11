"""
MELVIL_OT_load_material_to_slot — pick a saved material from the library
and assign it to the active object, either in a new slot or replacing the
currently active slot.

``slot_mode`` controls the assignment strategy:

- ``"NEW"``     — appends the material as a new slot on the object.
- ``"REPLACE"`` — overwrites the currently active material slot.

The picker uses an ``invoke_popup`` with a ``UIList`` for scrollable
single-selection.  The material list is stored on ``WindowManager``
(``melvil_material_items``) populated at invoke time.  The active index
(``material_index``) is an operator property so that clicking a row triggers
``check()``, which redraws the dialog and immediately reflects the enabled
state of the Load button.

Typical usage from the material context menu::

    bpy.ops.melvil.load_material_to_slot("INVOKE_DEFAULT", slot_mode="NEW")
    bpy.ops.melvil.load_material_to_slot("INVOKE_DEFAULT", slot_mode="REPLACE")
"""

from __future__ import annotations

import bpy
from bpy.props import BoolProperty, CollectionProperty, IntProperty, StringProperty

from ..core.asset_reader import AssetNotFoundError, AssetReader
from ..core.library import LibraryNotConfiguredError, resolve_db_path, resolve_library_root
from ..db import open_db
from ..ui.draw_helpers import load_assets


# ---------------------------------------------------------------------------
# PropertyGroup — one row in the material picker list
# ---------------------------------------------------------------------------


class MELVIL_PG_MaterialItem(bpy.types.PropertyGroup):
    """A single material entry in the picker list."""

    asset_id: StringProperty(name="Asset ID")


# ---------------------------------------------------------------------------
# UIList — the scrollable, selectable list drawn inside the dialog
# ---------------------------------------------------------------------------


class MELVIL_UL_MaterialList(bpy.types.UIList):
    """Scrollable material picker list."""

    bl_idname = "MELVIL_UL_material_list"

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            layout.label(text=item.name, icon="MATERIAL")
        elif self.layout_type == "GRID":
            layout.alignment = "CENTER"
            layout.label(text="", icon="MATERIAL")


# ---------------------------------------------------------------------------
# Picker operator
# ---------------------------------------------------------------------------


class MELVIL_OT_load_material_to_slot(bpy.types.Operator):
    """Pick a saved Melvil material and assign it to the active object"""

    bl_idname = "melvil.load_material_to_slot"
    bl_label = "Load Material"
    bl_options = {"REGISTER", "UNDO"}

    # Set by the Load button in draw() with the resolved UUID so that
    # execute() does not need to reach back into the WM list.
    asset_id: StringProperty(
        name="Asset ID",
        description="UUID of the saved material to load",
        default="",
        options={"HIDDEN"},
    )

    slot_mode: StringProperty(
        name="Slot Mode",
        description="NEW to append a new material slot, REPLACE to overwrite the active slot",
        default="NEW",
        options={"HIDDEN"},
    )

    # Operator property so that list-click events trigger check() and the
    # popup redraws, updating the Load button's enabled state immediately.
    material_index: IntProperty(
        name="Material Index",
        default=-1,
        options={"HIDDEN"},
    )

    # ------------------------------------------------------------------
    # Blender operator interface
    # ------------------------------------------------------------------

    @classmethod
    def poll(cls, context):
        if getattr(context, "active_object", None) is None:
            return False
        wm = getattr(context, "window_manager", None)
        if wm is None:
            return True
        # While the picker dialog is open, gate the OK button on having a
        # valid selection (kept in sync by check()).
        if getattr(wm, "melvil_picker_active", False):
            return getattr(wm, "melvil_selection_valid", False)
        return True

    def check(self, context):
        # material_index is an operator property, so clicking the UIList
        # updates it and Blender calls check().  We sync the selection state
        # onto WindowManager so that poll() — a classmethod — can read it
        # and Blender can re-evaluate the enabled state of the OK button.
        wm = context.window_manager
        has_selection = 0 <= self.material_index < len(wm.melvil_material_items)
        wm.melvil_selection_valid = has_selection
        self.asset_id = (
            wm.melvil_material_items[self.material_index].asset_id
            if has_selection
            else ""
        )
        return True

    def draw(self, context):
        layout = self.layout
        wm = context.window_manager

        layout.label(text="Select a material to load:", icon="MATERIAL")
        layout.separator()

        if getattr(self, "_load_error", None):
            layout.label(text="Could not open library database", icon="ERROR")
        elif len(wm.melvil_material_items) == 0:
            layout.label(text="No materials saved yet")
        else:
            layout.template_list(
                "MELVIL_UL_material_list",
                "",
                wm, "melvil_material_items",
                self, "material_index",
                rows=5,
                maxrows=8,
            )



    def invoke(self, context, event):
        self.material_index = -1
        self.asset_id = ""
        wm = context.window_manager
        wm.melvil_material_items.clear()
        wm.melvil_picker_active = True
        wm.melvil_selection_valid = False

        scene = getattr(context, "scene", None)
        active_kit_id = getattr(scene, "melvil_active_kit_id", None)
        kit_id = None
        if isinstance(active_kit_id, str) and active_kit_id != "ALL_KITS":
            kit_id = active_kit_id

        self._load_error = None
        try:
            materials = load_assets("MATERIAL", kit_id=kit_id)
        except Exception:  # noqa: BLE001
            self._load_error = "db_error"
            materials = []

        for mat in materials:
            item = wm.melvil_material_items.add()
            item.name = mat["name"]
            item.asset_id = mat["id"]

        return context.window_manager.invoke_props_dialog(
            self, width=400, confirm_text="Load Material"
        )

    def execute(self, context):
        wm = context.window_manager
        wm.melvil_picker_active = False
        wm.melvil_selection_valid = False

        if not self.asset_id or self.asset_id.strip() == "":
            self.report({"ERROR"}, "Melvil: no material selected.")
            return {"CANCELLED"}

        obj = context.active_object
        if obj is None:
            self.report({"ERROR"}, "Melvil: no active object.")
            return {"CANCELLED"}

        try:
            library_root = resolve_library_root()
        except LibraryNotConfiguredError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}

        try:
            with open_db(resolve_db_path()) as conn:
                reader = AssetReader(library_root, conn)
                material = reader.read(self.asset_id.strip())
        except AssetNotFoundError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        except Exception as exc:  # noqa: BLE001
            self.report({"ERROR"}, f"Melvil: load failed — {exc}")
            return {"CANCELLED"}

        if material is None:
            self.report({"ERROR"}, "Melvil: material not found inside managed .blend file.")
            return {"CANCELLED"}

        if self.slot_mode == "REPLACE":
            obj.active_material = material
        else:
            obj.data.materials.append(material)

        self.report({"INFO"}, f"Melvil: '{material.name}' assigned.")
        return {"FINISHED"}

    def cancel(self, context):
        wm = context.window_manager
        wm.melvil_picker_active = False
        wm.melvil_selection_valid = False
        wm.melvil_material_items.clear()


# ---------------------------------------------------------------------------
# Register / unregister (also wires up WindowManager properties)
# ---------------------------------------------------------------------------


def register() -> None:
    bpy.utils.register_class(MELVIL_PG_MaterialItem)
    bpy.utils.register_class(MELVIL_UL_MaterialList)
    bpy.types.WindowManager.melvil_material_items = CollectionProperty(
        type=MELVIL_PG_MaterialItem
    )
    bpy.types.WindowManager.melvil_picker_active = BoolProperty(default=False)
    bpy.types.WindowManager.melvil_selection_valid = BoolProperty(default=False)


def unregister() -> None:
    for attr in ("melvil_material_items", "melvil_picker_active", "melvil_selection_valid"):
        if hasattr(bpy.types.WindowManager, attr):
            delattr(bpy.types.WindowManager, attr)
    bpy.utils.unregister_class(MELVIL_UL_MaterialList)
    bpy.utils.unregister_class(MELVIL_PG_MaterialItem)
