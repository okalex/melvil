"""
Melvil submenu for the Node Editor context menu (right-click).

``MELVIL_MT_node_editor_submenu`` appears as a "Melvil ▶" entry in
``NODE_MT_context_menu`` whenever at least one node is selected.  It exposes:

- **Save as Asset** — saves the selected GROUP node as a ``"NODE_GROUP"``
  asset in the Melvil library.  The entry is grayed out unless exactly one
  GROUP-type node is selected.
"""

from __future__ import annotations

import bpy

from .menus_factory import register_submenu, unregister_submenu


class MELVIL_MT_node_editor_submenu(bpy.types.Menu):
    """Melvil node group actions — shown as a sub-menu in the node editor context menu."""

    bl_idname = "MELVIL_MT_node_editor_submenu"
    bl_label = "Melvil"

    def draw(self, context):
        self.layout.operator(
            "melvil.save_nodes_as_asset",
            text="Save as Asset",
            icon="EXPORT",
        )


# ---------------------------------------------------------------------------
# Draw function appended to NODE_MT_context_menu
# ---------------------------------------------------------------------------


def _draw_node_editor_entry(self, context):
    """Appended to NODE_MT_context_menu to insert the Melvil sub-menu.

    Shown only when at least one node is selected so the entry does not
    appear on an empty right-click.
    """
    space = getattr(context, "space_data", None)
    node_tree = getattr(space, "node_tree", None) if space else None
    if node_tree is None:
        return
    if not any(getattr(n, "select", False) for n in node_tree.nodes):
        return
    self.layout.menu(MELVIL_MT_node_editor_submenu.bl_idname)


# ---------------------------------------------------------------------------
# Register / unregister
# ---------------------------------------------------------------------------


def register() -> None:
    register_submenu(MELVIL_MT_node_editor_submenu, "NODE_MT_context_menu", _draw_node_editor_entry)


def unregister() -> None:
    unregister_submenu(MELVIL_MT_node_editor_submenu, "NODE_MT_context_menu", _draw_node_editor_entry)
