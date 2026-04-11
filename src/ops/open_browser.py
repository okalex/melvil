"""
MELVIL_OT_open_browser — floating popup library browser.

Invoked by ``Ctrl+Shift+A`` or the "Browse Library" button in the N-panel.
Uses ``window_manager.invoke_popup()`` to open a clean floating window
containing the full Melvil asset list — no Blender editor chrome.

The popup is split into two columns:
- Left: a UIList tree-style view for selecting the asset category
  (All, Materials, Meshes).
- Right: the filtered asset list for the selected category, drawn using
  the shared ``draw_asset_section`` helper.

Category items are stored in ``WindowManager.melvil_type_items``
(a ``CollectionProperty`` of ``MELVIL_PG_TypeItem``) so that
``template_list`` can render them with the native Blender list look.
The active selection index lives on the operator as ``type_index``
so that list-click events trigger ``check()`` and redraw the right column.

Clicking a Load button inside the popup immediately appends the asset and
closes the window.
"""

from __future__ import annotations

import bpy
from bpy.props import CollectionProperty, IntProperty, StringProperty

from ..ui.draw_helpers import draw_asset_section, load_assets

_POPUP_WIDTH = 700

# Vertical offset (at UI scale 1.0) subtracted from the top of the TOOLS
# region so that the popup aligns with the first toolbar button rather than
# the very top edge of the region.
_POPUP_Y_ADJUST = 14

# Static definition of the category tree entries.
# Each tuple: (value, label, icon)
_TYPE_ENTRIES = [
    ("ALL", "All", "ASSET_MANAGER"),
    ("MATERIAL", "Materials", "MATERIAL"),
    ("MESH", "Meshes", "MESH_DATA"),
]


# ---------------------------------------------------------------------------
# PropertyGroup — one row in the category list
# ---------------------------------------------------------------------------


class MELVIL_PG_TypeItem(bpy.types.PropertyGroup):
    """A single category entry in the browser type list."""

    label: StringProperty(name="Label")
    value: StringProperty(name="Value")
    icon: StringProperty(name="Icon")


# ---------------------------------------------------------------------------
# UIList — the scrollable category selector
# ---------------------------------------------------------------------------


class MELVIL_UL_TypeList(bpy.types.UIList):
    """Tree-style category selector for the Melvil browser."""

    bl_idname = "MELVIL_UL_type_list"

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            layout.label(text=item.label, icon=item.icon or "NONE")
        elif self.layout_type == "GRID":
            layout.alignment = "CENTER"
            layout.label(text="", icon=item.icon or "NONE")


# ---------------------------------------------------------------------------
# Popup operator
# ---------------------------------------------------------------------------


class MELVIL_OT_open_browser(bpy.types.Operator):
    """Open the Melvil library browser (Ctrl+Shift+A)"""

    bl_idname = "melvil.open_browser"
    bl_label = "Melvil Library"
    bl_options = {"REGISTER"}

    # Tracks the selected row in the UIList; living on the operator so that
    # list-click events trigger check() and the right column redraws.
    type_index: IntProperty(
        name="Category",
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
        wm.melvil_type_items.clear()
        for value, label, icon in _TYPE_ENTRIES:
            item = wm.melvil_type_items.add()
            item.label = label
            item.value = value
            item.icon = icon
        self.type_index = 0

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
        # user clicks a different row in the UIList.
        return True

    def execute(self, context):
        return {"FINISHED"}

    def draw(self, context):
        layout = self.layout
        wm = context.window_manager

        layout.label(text="Melvil Library", icon="ASSET_MANAGER")
        layout.separator()

        split = layout.split(factor=0.25)

        # ------------------------------------------------------------------
        # Left column — category tree list
        # ------------------------------------------------------------------
        left = split.column()
        left.template_list(
            "MELVIL_UL_type_list",
            "",
            wm, "melvil_type_items",
            self, "type_index",
            rows=len(_TYPE_ENTRIES),
        )

        # ------------------------------------------------------------------
        # Right column — filtered asset list
        # ------------------------------------------------------------------
        right = split.column()
        items = getattr(wm, "melvil_type_items", None)
        if items and 0 <= self.type_index < len(items):
            selected = items[self.type_index].value
        else:
            selected = "ALL"

        try:
            if selected in ("ALL", "MATERIAL"):
                draw_asset_section(right, "Materials", "MATERIAL", load_assets("MATERIAL"))
            if selected in ("ALL", "MESH"):
                draw_asset_section(right, "Meshes", "MESH_DATA", load_assets("MESH"))
        except Exception:
            right.label(text="Could not open library database", icon="ERROR")


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register() -> None:
    bpy.utils.register_class(MELVIL_PG_TypeItem)
    bpy.utils.register_class(MELVIL_UL_TypeList)
    bpy.types.WindowManager.melvil_type_items = CollectionProperty(type=MELVIL_PG_TypeItem)


def unregister() -> None:
    if hasattr(bpy.types.WindowManager, "melvil_type_items"):
        delattr(bpy.types.WindowManager, "melvil_type_items")
    bpy.utils.unregister_class(MELVIL_UL_TypeList)
    bpy.utils.unregister_class(MELVIL_PG_TypeItem)
