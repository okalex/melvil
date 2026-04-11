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

import bpy
from bpy.props import EnumProperty

from ..ui.draw_helpers import draw_asset_section, load_assets

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

    # ------------------------------------------------------------------
    # Blender operator interface
    # ------------------------------------------------------------------

    @classmethod
    def poll(cls, context):
        return context.area is not None and context.area.type == "VIEW_3D"

    def invoke(self, context, event):
        wm = context.window_manager
        self.type_filter = "ALL"

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
        # Left column — category selector
        # ------------------------------------------------------------------
        left = split.column()
        left.label(text="Asset type")
        left.prop(self, "type_filter", expand=True)

        # ------------------------------------------------------------------
        # Right column — filtered asset list
        # ------------------------------------------------------------------
        right = split.column()
        selected = self.type_filter

        try:
            if selected in ("ALL", "MATERIAL"):
                draw_asset_section(right, "Materials", "MATERIAL", load_assets("MATERIAL"))
            if selected in ("ALL", "MESH"):
                draw_asset_section(right, "Meshes", "MESH_DATA", load_assets("MESH"))
            if selected in ("ALL", "NODE_GROUP"):
                draw_asset_section(right, "Node Groups", "NODETREE", load_assets("NODE_GROUP"), show_load=False)
        except Exception:
            right.label(text="Could not open library database", icon="ERROR")


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register() -> None:
    bpy.utils.register_class(MELVIL_OT_open_browser)


def unregister() -> None:
    bpy.utils.unregister_class(MELVIL_OT_open_browser)
