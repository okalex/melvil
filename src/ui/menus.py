"""
Melvil context-menu submenu system.

Any part of the addon can register draw callables into the Melvil submenu
without knowing about the others:

    from melvil.ui.menus import register_item, unregister_item

    def _draw_my_item(self, context):
        self.layout.operator("melvil.my_operator")

    # called during your module's register():
    register_item(_draw_my_item)

    # called during your module's unregister():
    unregister_item(_draw_my_item)

``MELVIL_MT_context_submenu`` is the shared Menu class.  It is appended to
every host menu listed in ``_HOST_MENUS`` at register-time as a single
"Melvil ▶" entry, keeping host-menu pollution to exactly one line regardless
of how many items are registered in the submenu.
"""

from __future__ import annotations

import bpy

# ---------------------------------------------------------------------------
# Host menus that should expose the "Melvil ▶" entry
# ---------------------------------------------------------------------------

# Each string is the bl_idname of a bpy.types.Menu to patch.
# Add more here as the addon grows (e.g. node-editor, UV editor …).
_HOST_MENUS: tuple[str, ...] = (
    "VIEW3D_MT_object_context_menu",  # Object Mode right-click
)

# ---------------------------------------------------------------------------
# Item registry
# ---------------------------------------------------------------------------

_items: list = []


def register_item(draw_fn) -> None:
    """Register *draw_fn* as an item in the Melvil submenu.

    *draw_fn* has the same signature as any ``bpy.types.Menu.draw`` method::

        def draw_fn(self, context): ...
    """
    if draw_fn not in _items:
        _items.append(draw_fn)


def unregister_item(draw_fn) -> None:
    """Remove *draw_fn* from the Melvil submenu.  No-op if not registered."""
    try:
        _items.remove(draw_fn)
    except ValueError:
        pass


# ---------------------------------------------------------------------------
# Submenu class
# ---------------------------------------------------------------------------


class MELVIL_MT_context_submenu(bpy.types.Menu):
    """Melvil actions — shown as a sub-menu inside host context menus."""

    bl_idname = "MELVIL_MT_context_submenu"
    bl_label = "Melvil"

    def draw(self, context):
        for item_fn in _items:
            item_fn(self, context)


# ---------------------------------------------------------------------------
# Draw function appended to host menus
# ---------------------------------------------------------------------------


def _draw_melvil_submenu_entry(self, context):
    """Single draw function appended to every host menu.

    Only shown when at least one object is selected so that the entry does
    not appear on an empty right-click.
    """
    if not getattr(context, "selected_objects", None):
        return
    self.layout.menu(MELVIL_MT_context_submenu.bl_idname)


# ---------------------------------------------------------------------------
# Register / unregister
# ---------------------------------------------------------------------------


def register() -> None:
    bpy.utils.register_class(MELVIL_MT_context_submenu)
    for menu_id in _HOST_MENUS:
        menu_type = getattr(bpy.types, menu_id, None)
        if menu_type is not None:
            menu_type.append(_draw_melvil_submenu_entry)


def unregister() -> None:
    for menu_id in _HOST_MENUS:
        menu_type = getattr(bpy.types, menu_id, None)
        if menu_type is not None:
            menu_type.remove(_draw_melvil_submenu_entry)
    bpy.utils.unregister_class(MELVIL_MT_context_submenu)
