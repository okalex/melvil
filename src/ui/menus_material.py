"""
Melvil submenu for the material slot context menu (Properties ▸ Material
▸ option arrow).

``MELVIL_MT_material_submenu`` appears as a "Melvil ▶" entry in
``MATERIAL_MT_context_menu`` whenever the active object exists.  It exposes:

- **Load Material (New Slot)** — always visible; opens the material picker
  and appends the chosen material as a new slot on the active object.
- **Load Material (Replace Active)** — visible only when the object already
  has an active material; replaces that slot with the chosen material.
- **Save as Asset** — visible only when the object has an active material;
  saves the active material to the library.
"""

from __future__ import annotations

import bpy


class MELVIL_MT_material_submenu(bpy.types.Menu):
    """Melvil material actions — shown as a sub-menu in the material context menu."""

    bl_idname = "MELVIL_MT_material_submenu"
    bl_label = "Melvil"

    def draw(self, context):
        layout = self.layout
        obj = getattr(context, "active_object", None)
        has_material = obj is not None and getattr(obj, "active_material", None) is not None

        op = layout.operator(
            "melvil.load_material_to_slot",
            text="Load Material (New Slot)",
            icon="IMPORT",
        )
        op.slot_mode = "NEW"

        if has_material:
            op = layout.operator(
                "melvil.load_material_to_slot",
                text="Load Material (Replace Active)",
                icon="IMPORT",
            )
            op.slot_mode = "REPLACE"

            layout.separator()
            layout.operator("melvil.save_asset", text="Save as Asset", icon="EXPORT")


# ---------------------------------------------------------------------------
# Draw function appended to MATERIAL_MT_context_menu
# ---------------------------------------------------------------------------


def _draw_material_entry(self, context):
    """Appended to MATERIAL_MT_context_menu to insert the Melvil sub-menu.

    Shown whenever the active object exists (a material slot is not required,
    since "Load Material (New Slot)" is always available).
    """
    obj = getattr(context, "active_object", None)
    if obj is None:
        return
    self.layout.menu(MELVIL_MT_material_submenu.bl_idname)


# ---------------------------------------------------------------------------
# Register / unregister
# ---------------------------------------------------------------------------


def register() -> None:
    bpy.utils.register_class(MELVIL_MT_material_submenu)
    menu_type = getattr(bpy.types, "MATERIAL_MT_context_menu", None)
    if menu_type is not None:
        menu_type.append(_draw_material_entry)


def unregister() -> None:
    menu_type = getattr(bpy.types, "MATERIAL_MT_context_menu", None)
    if menu_type is not None:
        menu_type.remove(_draw_material_entry)
    bpy.utils.unregister_class(MELVIL_MT_material_submenu)
