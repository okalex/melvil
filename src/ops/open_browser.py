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
from bpy.props import BoolProperty, EnumProperty, StringProperty

from ..core.library import resolve_db_path
from ..db import open_db
from ..db.kits import list_kits
from .tag_filter_toggle import get_active_tag_filters
from ..ui.draw_helpers import (
    draw_asset_section,
    draw_tag_filter_pills,
    draw_tag_management_section,
    filter_assets,
    load_asset_tag_memberships,
    load_assets,
    load_kits,
    load_tags_for_asset_ids,
    load_tags_with_usage,
)

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

    # Free-text search query applied on top of the type and kit filters.
    search_query: StringProperty(
        name="Search",
        default="",
        # TEXTEDIT_UPDATE causes check() to fire on every keypress so the
        # asset list filters in real time without requiring Enter.
        options={"HIDDEN", "TEXTEDIT_UPDATE"},
    )

    # Controls visibility of the tag management section in the left column.
    show_manage_tags: BoolProperty(
        name="Manage Tags",
        default=False,
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

        self.search_query = ""
        self.show_manage_tags = False
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
        # Front-load all data so both columns can share it without extra queries.
        # ------------------------------------------------------------------
        selected = self.type_filter
        kit_id = self.kit_filter if self.kit_filter != "ALL_KITS" else None
        query = self.search_query
        active_tag_ids = get_active_tag_filters(context.window_manager)

        # Determine which type sections are visible (respects type_filter).
        visible_types = [
            t for t in ("MATERIAL", "MESH", "NODE_GROUP")
            if selected in ("ALL", t)
        ]

        try:
            kits = load_kits()

            # Load and search-filter assets per type (no tag filter yet).
            # These are used both to derive the tag pills and (after tag
            # filtering) to draw the actual asset sections.
            pre_tag: dict[str, list] = {
                t: filter_assets(load_assets(t, kit_id=kit_id), query)
                for t in visible_types
            }

            # Bulk-load tag memberships for all pre-filtered assets in one
            # query, then use them for both pill derivation and tag filtering.
            all_pre_ids = [a["id"] for assets in pre_tag.values() for a in assets]
            memberships = load_asset_tag_memberships(all_pre_ids)
            visible_tags = load_tags_for_asset_ids(all_pre_ids)

            # Build a tag-id → name lookup and then a per-asset tag map so that
            # draw_asset_section can render inline tag pills without extra queries.
            tag_lookup = {t["id"]: t["name"] for t in visible_tags}
            asset_tags_map: dict[str, list] = {
                aid: sorted(
                    [{"id": tid, "name": tag_lookup[tid]} for tid in tids if tid in tag_lookup],
                    key=lambda t: t["name"],
                )
                for aid, tids in memberships.items()
            }

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
            asset_tags_map = {}

        # ------------------------------------------------------------------
        # Left column — category + kit selectors + tag pills + manage tags
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

        # Tag filter pills — shown below the kit selector.
        if visible_tags:
            left.separator()
            draw_tag_filter_pills(left, visible_tags, active_tag_ids)

        left.separator()

        # Tag management section — toggled by the "Manage Tags" button.
        left.prop(self, "show_manage_tags", text="Manage Tags", icon="TAG", toggle=True)
        if getattr(self, "show_manage_tags", False):
            try:
                tags = load_tags_with_usage()
                sort_by = getattr(context.window_manager, "melvil_tag_sort", "NAME") or "NAME"
                draw_tag_management_section(left, tags, sort_by)
            except Exception:  # noqa: BLE001
                left.label(text="Could not load tags", icon="ERROR")

        # ------------------------------------------------------------------
        # Right column — filtered asset list
        # ------------------------------------------------------------------
        right = split.column()
        right.prop(self, "search_query", text="", icon="VIEWZOOM")
        right.separator()

        if load_error is not None:
            right.label(text="Could not open library database", icon="ERROR")
            return

        _SECTION_SPECS = {
            "MATERIAL":   ("Materials",   "MATERIAL",  True),
            "MESH":        ("Meshes",       "MESH_DATA", True),
            "NODE_GROUP": ("Node Groups",  "NODETREE",  False),
        }
        for type_key in visible_types:
            title, icon, show_load = _SECTION_SPECS[type_key]
            draw_asset_section(
                right, title, icon,
                section_assets.get(type_key, []),
                show_load=show_load,
                kits=kits,
                asset_tags=asset_tags_map,
                active_tag_ids=active_tag_ids,
            )


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register() -> None:
    bpy.utils.register_class(MELVIL_OT_open_browser)


def unregister() -> None:
    bpy.utils.unregister_class(MELVIL_OT_open_browser)
