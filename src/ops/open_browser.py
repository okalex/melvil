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
from .tag_filter_toggle import get_active_tag_filters
from ..ui import scene_props as _scene_props
from ..ui.draw_helpers import (
    draw_asset_details,
    draw_asset_section,
    filter_assets,
    load_all_tags,
    load_asset,
    load_asset_tag_memberships,
    load_asset_tag_names,
    load_assets,
    load_kits,
    load_tags_for_asset_ids,
)

_POPUP_WIDTH = 900

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

    # Free-text search query applied on top of the type and kit filters.
    search_query: StringProperty(
        name="Search",
        default="",
        # TEXTEDIT_UPDATE causes check() to fire on every keypress so the
        # asset list filters in real time without requiring Enter.
        options={"HIDDEN", "TEXTEDIT_UPDATE"},
    )

    # ------------------------------------------------------------------
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

        self.search_query = ""
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

        # Three-column split: left filters | asset list | asset details.
        outer_split = layout.split(factor=0.24)
        left = outer_split.column()
        rest_col = outer_split.column()
        inner_split = rest_col.split(factor=0.45)
        middle = inner_split.column()
        right = inner_split.column()

        # ------------------------------------------------------------------
        # Front-load all data so both columns can share it without extra queries.
        # ------------------------------------------------------------------
        selected = self.type_filter
        kit_id = self.kit_filter if self.kit_filter != "ALL_KITS" else None
        query = self.search_query
        wm = context.window_manager
        active_tag_ids = get_active_tag_filters(wm)
        selected_id = getattr(wm, "melvil_selected_asset_id", "")

        # Determine which type sections are visible (respects type_filter).
        visible_types = [
            t for t in ("MATERIAL", "MESH", "NODE_GROUP")
            if selected in ("ALL", t)
        ]

        try:
            kits = load_kits()

            # Load all kit-filtered assets per type (before search).
            all_assets: dict[str, list] = {
                t: load_assets(t, kit_id=kit_id)
                for t in visible_types
            }

            # Load tag names for every candidate asset so that search can
            # match on tags in addition to asset names.  Skipped when the
            # query is empty to avoid an unnecessary round-trip.
            all_ids = [a["id"] for assets in all_assets.values() for a in assets]
            tag_names_map = load_asset_tag_names(all_ids) if query else {}

            # Apply search filter (name + tag names) per type.
            pre_tag: dict[str, list] = {
                t: filter_assets(assets, query, tag_names_map)
                for t, assets in all_assets.items()
            }

            # Bulk-load tag memberships for all pre-filtered assets in one
            # query, then use them for pill derivation and tag filtering.
            all_pre_ids = [a["id"] for assets in pre_tag.values() for a in assets]
            memberships = load_asset_tag_memberships(all_pre_ids)
            visible_tags = load_all_tags()

            # Apply the active tag filter (AND semantics).
            if active_tag_ids:
                active_set = set(active_tag_ids)
                section_assets: dict[str, list] = {
                    t: [
                        a for a in assets
                        if active_set.issubset(memberships.get(a["id"], set()))
                    ]
                    for t, assets in pre_tag.items()
                }
            else:
                section_assets = pre_tag

            load_error = None
        except Exception as exc:  # noqa: BLE001
            load_error = exc
            kits = []
            visible_tags = []
            active_tag_ids = []
            section_assets = {t: [] for t in visible_types}

        # Load the selected asset details in a separate try so that a missing
        # selection does not pollute the main load_error path.
        selected_asset = None
        selected_tags: list = []
        selected_kit_name = "Default"
        if selected_id and load_error is None:
            try:
                selected_asset = load_asset(selected_id)
                if selected_asset is not None:
                    selected_tags = list(load_tags_for_asset_ids([selected_id]))
                    selected_kit_name = next(
                        (k["name"] for k in kits if k["id"] == selected_asset["kit_id"]),
                        "Default",
                    )
            except Exception:  # noqa: BLE001
                selected_asset = None

        # ------------------------------------------------------------------
        # Left column — category + kit selectors + tag pills + manage tags
        # ------------------------------------------------------------------

        left.prop(self, "search_query", text="", icon="VIEWZOOM")
        left.separator()

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

        # Tag filter list — shown below the kit selector.
        if visible_tags:
            left.separator()
            tag_header = left.row(align=True)
            tag_header.label(text="Tags", icon="TAG")

            active_set = set(active_tag_ids)
            _scene_props._rebuilding_filter_tags = True
            try:
                wm.melvil_filter_tags.clear()
                for _ftag in visible_tags:
                    _item = wm.melvil_filter_tags.add()
                    _item.name = _ftag["name"]
                    _item.tag_id = _ftag["id"]
                    _item.is_active = _ftag["id"] in active_set
                wm.melvil_filter_tags_index = -1
            finally:
                _scene_props._rebuilding_filter_tags = False
            tag_list_row = left.row()
            tag_list_row.template_list(
                "MELVIL_UL_filter_tags", "",
                wm, "melvil_filter_tags",
                wm, "melvil_filter_tags_index",
                rows=min(len(visible_tags), 8),
            )
            tag_side_col = tag_list_row.column(align=True)
            tag_side_col.operator("melvil.tag_create", text="", icon="ADD")
            delete_col = tag_side_col.column()
            delete_col.enabled = bool(active_tag_ids)
            delete_op = delete_col.operator("melvil.tag_delete", text="", icon="REMOVE")
            delete_op.tag_id = active_tag_ids[0] if active_tag_ids else ""

        left.separator()

        # ------------------------------------------------------------------
        # Middle column — filtered asset list
        # ------------------------------------------------------------------
        if load_error is not None:
            middle.label(text="Could not open library database", icon="ERROR")
            return

        _SECTION_SPECS = {
            "MATERIAL":   ("Materials",   "MATERIAL",  True),
            "MESH":        ("Meshes",       "MESH_DATA", True),
            "NODE_GROUP": ("Node Groups",  "NODETREE",  False),
        }
        for type_key in visible_types:
            title, icon, show_load = _SECTION_SPECS[type_key]
            draw_asset_section(
                middle, title, icon,
                section_assets.get(type_key, []),
                show_load=show_load,
                selected_asset_id=selected_id,
            )

        # ------------------------------------------------------------------
        # Right column — asset detail panel
        # ------------------------------------------------------------------

        # Populate the WM tag collection so template_list has data to display.
        wm.melvil_asset_tags.clear()
        for _tag in selected_tags:
            item = wm.melvil_asset_tags.add()
            item.name = _tag["name"]
            item.tag_id = _tag["id"]

        right_box = right.box()
        if selected_asset is not None:
            draw_asset_details(
                right_box,
                selected_asset,
                selected_tags,
                selected_kit_name,
                wm=wm,
            )
        else:
            right_box.label(text="Select an asset", icon="INFO")
            right_box.label(text="to view its details.")


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register() -> None:
    bpy.utils.register_class(MELVIL_OT_open_browser)


def unregister() -> None:
    bpy.utils.unregister_class(MELVIL_OT_open_browser)
