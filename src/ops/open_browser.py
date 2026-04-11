"""
MELVIL_OT_open_browser — floating popup library browser.

Invoked by ``Ctrl+Shift+A`` or the "Browse Library" button in the N-panel.
Uses ``window_manager.invoke_popup()`` to open a clean floating window
containing the full Melvil asset list — no Blender editor chrome.

The popup is split into two columns:
- Left: a plain column of toggle buttons for selecting the asset category
  (All, Materials, Meshes, Node Groups).
- Right: the filtered asset list for the selected category, drawn using
  the shared ``draw_asset_section`` helper.

The active category lives on the operator as ``type_filter`` (EnumProperty)
so that button-click events trigger ``check()`` and redraw the right column.

Clicking a Load button inside the popup immediately appends the asset and
closes the window.
"""

from __future__ import annotations

import sys

import bpy
from bpy.props import EnumProperty, StringProperty

from ..core.library import resolve_db_path
from ..db import open_db
from ..db.kits import list_kits
from ..ui.draw_helpers import draw_asset_section, load_assets, load_kits

_POPUP_WIDTH = 700

# Vertical offset (at UI scale 1.0) subtracted from the top of the TOOLS
# region so that the popup aligns with the first toolbar button rather than
# the very top edge of the region.
_POPUP_Y_ADJUST = 14

# Enum items for the category selector: (identifier, label, description, icon, value)
_TYPE_ENUM_ITEMS = [
    ("ALL",        "All",         "", "ASSET_MANAGER", 0),
    ("MATERIAL",   "Materials",   "", "MATERIAL",      1),
    ("MESH",       "Meshes",      "", "MESH_DATA",     2),
    ("NODE_GROUP", "Node Groups", "", "NODETREE",      3),
]

# Module-level cache to keep kit enum strings alive (Blender GC requirement).
# All strings are interned via sys.intern() so they are held permanently in
# Python's intern table — Blender's C-level char* pointers can never dangle.
_kit_enum_cache: list[tuple] = [("ALL_KITS", "All Kits", "", "ASSET_MANAGER", 0)]


def _get_kit_filter_items(self, context):
    global _kit_enum_cache
    items = [(sys.intern("ALL_KITS"), sys.intern("All Kits"), sys.intern(""), sys.intern("ASSET_MANAGER"), 0)]
    try:
        with open_db(resolve_db_path()) as conn:
            for i, kit in enumerate(list_kits(conn), 1):
                items.append((
                    sys.intern(str(kit["id"])),
                    sys.intern(str(kit["name"])),
                    sys.intern(""),
                    sys.intern("FOLDER_CURRENT"),
                    i,
                ))
    except Exception:  # noqa: BLE001
        pass
    _kit_enum_cache = items
    return _kit_enum_cache


# ---------------------------------------------------------------------------
# Popup operator
# ---------------------------------------------------------------------------


class MELVIL_OT_open_browser(bpy.types.Operator):
    """Open the Melvil library browser (Ctrl+Shift+A)"""

    bl_idname = "melvil.open_browser"
    bl_label = "Melvil Library"
    bl_options = {"REGISTER"}

    # Tracks the selected category; living on the operator so that
    # button-click events trigger check() and the right column redraws.
    type_filter: EnumProperty(
        name="Category",
        items=_TYPE_ENUM_ITEMS,
        default="ALL",
        options={"HIDDEN"},
    )

    # Tracks the selected kit (kit UUID or "" for All Kits).
    kit_filter: EnumProperty(
        name="Kit",
        items=_get_kit_filter_items,
        default=0,
        options={"HIDDEN"},
    )

    # ------------------------------------------------------------------
    # Blender operator interface
    # ------------------------------------------------------------------

    @classmethod
    def poll(cls, context):
        return context.area is not None and context.area.type == "VIEW_3D"

    def invoke(self, context, event):
        wm = context.window_manager
        self.type_filter = "ALL"
        self.kit_filter = "ALL_KITS"

        # Position the popup at the top-left of the viewport, just to the right
        # of the toolbar.  The gap between the popup and the toolbar matches the
        # gap between the toolbar buttons and the viewport's left edge (≈ 5 px
        # at UI scale 1.0).
        area = context.area
        tools_region = next(
            (r for r in area.regions if r.type == "TOOLS"), None
        )
        margin = round(context.preferences.system.ui_scale * 5)
        if tools_region is not None:
            popup_x = tools_region.x + tools_region.width + margin
            popup_y = tools_region.y + tools_region.height - round(context.preferences.system.ui_scale * _POPUP_Y_ADJUST)
        else:
            header_region = next(
                (r for r in area.regions if r.type == "HEADER"), None
            )
            header_height = header_region.height if header_region is not None else 0
            popup_x = area.x + margin
            popup_y = area.y + area.height - header_height
        context.window.cursor_warp(popup_x, popup_y)

        return wm.invoke_popup(self, width=_POPUP_WIDTH)

    def check(self, context):
        # Returning True forces Blender to redraw the popup whenever the
        # user clicks a different category button.
        return True

    def execute(self, context):
        return {"FINISHED"}

    def draw(self, context):
        layout = self.layout

        layout.label(text="Melvil Asset Library", icon="ASSET_MANAGER")
        layout.separator()

        split = layout.split(factor=0.25)

        # ------------------------------------------------------------------
        # Left column — category + kit selectors
        # ------------------------------------------------------------------
        left = split.column()

        left.label(text="Asset type")
        left.prop(self, "type_filter", expand=True)

        left.separator()

        # Kit selector header row with New Kit and Rename Kit buttons.
        kit_header = left.row(align=True)
        kit_header.label(text="Kit")
        kit_header.operator("melvil.kit_create", text="", icon="ADD")
        rename_sub = kit_header.row()
        rename_sub.enabled = self.kit_filter != "ALL_KITS"
        rename_op = rename_sub.operator("melvil.kit_rename", text="", icon="GREASEPENCIL")
        rename_op.kit_id = self.kit_filter if self.kit_filter != "ALL_KITS" else ""

        left.prop(self, "kit_filter", expand=True)

        # ------------------------------------------------------------------
        # Right column — filtered asset list
        # ------------------------------------------------------------------
        right = split.column()
        selected = self.type_filter
        kit_id = self.kit_filter if self.kit_filter != "ALL_KITS" else None

        try:
            kits = load_kits()
            if selected in ("ALL", "MATERIAL"):
                draw_asset_section(right, "Materials", "MATERIAL", load_assets("MATERIAL", kit_id=kit_id), kits=kits)
            if selected in ("ALL", "MESH"):
                draw_asset_section(right, "Meshes", "MESH_DATA", load_assets("MESH", kit_id=kit_id), kits=kits)
            if selected in ("ALL", "NODE_GROUP"):
                draw_asset_section(right, "Node Groups", "NODETREE", load_assets("NODE_GROUP", kit_id=kit_id), show_load=False, kits=kits)
        except Exception:
            right.label(text="Could not open library database", icon="ERROR")


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register() -> None:
    bpy.utils.register_class(MELVIL_OT_open_browser)


def unregister() -> None:
    bpy.utils.unregister_class(MELVIL_OT_open_browser)
