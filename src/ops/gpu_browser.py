"""
MELVIL_OT_gpu_browser — GPU-drawn asset browser.

Invoked by ``Ctrl+Shift+A`` in the 3D View.  Creates a :class:`GpuPanel`
that renders the Melvil asset browser entirely via GPU draw handlers.
Press ``ESC`` or ``RMB`` to dismiss.
"""

import sys

import bpy
from bpy.props import EnumProperty, StringProperty
from pathlib import Path

from ..core.library import resolve_db_path, resolve_library_root
from ..db import open_db
from ..db.kits import DEFAULT_KIT_ID, list_kits
from ..ui.gpu import GpuPanel, EventResult, get_region_offsets
from ..ui.gpu.theme import get_theme
from ..ui import scene_props as _scene_props
from ..ui.asset_types import type_icon, show_load
from ..ui.draw_helpers import (
    draw_asset_details,
    filter_assets,
    load_all_tags,
    load_asset,
    load_asset_tag_memberships,
    load_asset_tag_names,
    load_assets,
    load_kits,
    load_tags_for_asset_ids,
)
from ..ui.previews_collection import (
    get_icon_id,
    get_placeholder_icon_id,
    _placeholder_path,
)
from .tag_filter_toggle import get_active_tag_filters

_PANEL_MARGIN_X = 0
_PANEL_MARGIN_Y = 18

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
                icon = "BOOKMARKS" if kit["id"] == DEFAULT_KIT_ID else "PACKAGE"
                items.append((
                    sys.intern(str(kit["id"])),
                    sys.intern(str(kit["name"])),
                    sys.intern(""),
                    sys.intern(icon),
                    i,
                ))
    except Exception:  # noqa: BLE001
        pass
    _kit_enum_cache = items
    return _kit_enum_cache



# Cell height for asset cards (unscaled pixels):
# BOX_PAD*2 + name_row + gap + template_icon(12*5) + gap + btn_row
# = 16 + 20 + 4 + 60 + 4 + 20 = 124
_ASSET_CARD_HEIGHT = 124


def _draw_asset_tag_item(layout, item, index, is_active):
    """Draw a single tag row in the asset detail tag list."""
    layout.label(text=item.name)


def _draw_filter_tag_item(layout, item, index, is_active):
    """Draw a single tag-filter row."""
    row = layout.row(align=True)
    row.label(text=item.name)
    sub = row.row()
    sub.scale_x = 0.15
    sub.icon_button(
        icon="GREASEPENCIL", button_id="tag_rename", style="GHOST",
    )


def _draw_asset_card(layout, item, index, is_active):
    """Draw a single asset card in the asset grid list."""
    box = layout.box()
    if is_active:
        theme = get_theme()
        box._box_bg = theme.widget_bg_active
        box._box_border = theme.widget_bg_active

    # Name + type icon at the top of the card.
    name_row = box.row(align=True)
    icon_col = name_row.column()
    icon_col.scale_x = 0.15
    icon_col.label(text="", icon=type_icon(item.asset_type))
    name_row.label(text=item.name)

    # Preview image.
    icon_id = (
        get_icon_id(item.asset_id, item.abs_preview_path)
        if item.abs_preview_path else None
    )
    if icon_id is None:
        icon_id = get_placeholder_icon_id(item.asset_type)
    if icon_id is not None:
        box.template_icon(icon_value=icon_id, scale=5.0)

    # Action buttons.
    if show_load(item.asset_type):
        load_op = box.operator("melvil.load_asset", text="Add to scene")
        load_op.asset_id = item.asset_id


class MELVIL_OT_gpu_browser(bpy.types.Operator):
    bl_idname = "melvil.gpu_browser"
    bl_label = "Melvil Browser (GPU)"
    bl_options = {"REGISTER", "INTERNAL"}

    type_filter: EnumProperty(
        name="Category",
        items=_TYPE_ENUM_ITEMS,
        default="ALL",
        options={"HIDDEN"},
    )

    kit_filter: EnumProperty(
        name="Kit",
        items=_get_kit_filter_items,
        default=0,
        options={"HIDDEN"},
    )

    search_query: StringProperty(
        name="Asset name",
        default="",
        options={"HIDDEN", "TEXTEDIT_UPDATE"},
    )

    _panel = None

    @classmethod
    def poll(cls, context):
        return context.area is not None and context.area.type == "VIEW_3D"

    @staticmethod
    def _compute_anchor() -> tuple[int, int]:
        """Return ``(x, y)`` top-left anchor in WINDOW-region pixels.

        Places the panel to the right of the vertical toolbar with a
        margin, and below any overlay button rows at the top of the
        WINDOW region.
        """
        try:
            area = bpy.context.area
            region = bpy.context.region
            offset_x, offset_y = get_region_offsets(area)
            x = offset_x + _PANEL_MARGIN_X
            y = region.height - offset_y - _PANEL_MARGIN_Y
            return (x, y)
        except Exception:
            return (0, 800)

    def invoke(self, context, event):
        self._panel = GpuPanel(
            width=900,
            anchor=self._compute_anchor,
            build_fn=self._build,
        )
        self._panel.register_list_drawer(
            "MELVIL_UL_filter_tags", _draw_filter_tag_item,
        )
        self._panel.register_list_drawer(
            "MELVIL_UL_asset_grid", _draw_asset_card,
        )
        self._panel.register_list_drawer(
            "MELVIL_UL_asset_tags", _draw_asset_tag_item,
        )
        self._panel.register_widget_handler(
            "icon_button", self._handle_icon_button,
        )
        self._panel.attach(context.area)
        context.window_manager.modal_handler_add(self)
        context.area.tag_redraw()
        return {"RUNNING_MODAL"}

    def _build(self, layout):
        """Build the browser widget tree.

        Mirrors the three-column structure of ``open_browser.py`` using
        only implemented GPU UI elements. Unsupported elements
        (template_list, template_icon, operator_menu_enum) are omitted.
        """
        layout.label(text="Melvil Asset Library", icon="ASSET_MANAGER")
        layout.separator()

        # Three-column split: left filters | asset list | asset details.
        outer_split = layout.split(factor=0.24)
        left = outer_split.column()
        rest_col = outer_split.column()
        inner_split = rest_col.split(factor=0.45)
        middle = inner_split.column()
        right = inner_split.column()

        # -- Left column: filters --------------------------------------------
        left.label(text="Search by name/tag", icon="VIEWZOOM")
        left.prop(self, "search_query", text="")
        left.separator()

        left.label(text="Asset type")
        left.prop(self, "type_filter", expand=True)
        left.separator(factor=2.0)

        # Kit selector header row with New Kit and Rename Kit buttons.
        kit_header = left.row(align=True)
        kit_header.label(text="Kit")
        new_col = kit_header.column()
        new_col.scale_x = 0.15
        new_col.operator("melvil.kit_create", text="", icon="ADD")
        rename_col = kit_header.column()
        rename_col.scale_x = 0.15
        rename_col.enabled = self.kit_filter != "ALL_KITS"
        rename_op = rename_col.operator(
            "melvil.kit_rename", text="", icon="GREASEPENCIL",
        )
        rename_op.kit_id = (
            self.kit_filter if self.kit_filter != "ALL_KITS" else ""
        )

        left.prop(self, "kit_filter", expand=True)
        left.separator(factor=2.0)

        # Tag filter section.
        tag_header = left.row(align=True)
        tag_header.label(text="Tags", icon="TAG")

        wm = bpy.context.window_manager
        try:
            visible_tags = load_all_tags()
        except Exception:  # noqa: BLE001
            visible_tags = []

        if visible_tags:
            active_tag_ids = get_active_tag_filters(wm)
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

            tag_row = left.row()
            tag_list_col = tag_row.column()
            tag_list_col.scale_x = 0.9
            tag_list_col.template_list(
                "MELVIL_UL_filter_tags", "gpu_tag_filter",
                wm, "melvil_filter_tags",
                wm, "melvil_filter_tags_index",
                rows=min(len(visible_tags), 8),
                allow_deselect=True,
            )
            tag_row.separator(factor=0.5)
            tag_btn_col = tag_row.column()
            tag_btn_col.scale_x = 0.1
            tag_btn_col.operator(
                "melvil.tag_create", text="", icon="ADD",
            )
            tag_btn_col.separator(factor=0.5)
            selected_idx = (
                self._panel._list_selections.get("gpu_tag_filter", -1)
                if self._panel is not None else -1
            )
            selected_tag = (
                wm.melvil_filter_tags[selected_idx]
                if 0 <= selected_idx < len(wm.melvil_filter_tags)
                else None
            )
            delete_btn = tag_btn_col.column()
            delete_btn.enabled = selected_tag is not None
            delete_op = delete_btn.operator(
                "melvil.tag_delete", text="", icon="REMOVE",
            )
            if selected_tag is not None:
                delete_op.tag_id = selected_tag.tag_id
        else:
            tag_row = left.row()
            tag_empty_box = tag_row.column()
            tag_empty_box.scale_x = 0.9
            tag_empty_box.box().label(text="No tags saved")
            tag_row.separator(factor=0.5)
            tag_btn_col = tag_row.column()
            tag_btn_col.scale_x = 0.1
            tag_btn_col.operator(
                "melvil.tag_create", text="", icon="ADD",
            )
            tag_btn_col.separator(factor=0.5)
            delete_btn = tag_btn_col.column()
            delete_btn.enabled = False
            delete_btn.operator(
                "melvil.tag_delete", text="", icon="REMOVE",
            )

        left.separator()

        # -- Middle column: asset list ---------------------------------------
        middle.label(text="Assets", icon="ASSET_MANAGER")

        selected = self.type_filter
        visible_types = [
            t for t in ("MATERIAL", "MESH", "NODE_GROUP")
            if selected in ("ALL", t)
        ]
        kit_id = self.kit_filter if self.kit_filter != "ALL_KITS" else None
        query = self.search_query
        active_tag_ids = get_active_tag_filters(wm)

        try:
            all_assets = {
                t: load_assets(t, kit_id=kit_id)
                for t in visible_types
            }
            all_ids = [
                a["id"]
                for assets in all_assets.values()
                for a in assets
            ]
            tag_names_map = (
                load_asset_tag_names(all_ids) if query else {}
            )
            pre_tag = {
                t: filter_assets(assets, query, tag_names_map)
                for t, assets in all_assets.items()
            }
            all_pre_ids = [
                a["id"]
                for assets in pre_tag.values()
                for a in assets
            ]
            memberships = load_asset_tag_memberships(all_pre_ids)

            if active_tag_ids:
                active_set = set(active_tag_ids)
                section_assets = {
                    t: [
                        a for a in assets
                        if active_set.issubset(
                            memberships.get(a["id"], set()),
                        )
                    ]
                    for t, assets in pre_tag.items()
                }
            else:
                section_assets = pre_tag

            all_visible = sorted(
                (
                    a
                    for assets in section_assets.values()
                    for a in assets
                ),
                key=lambda a: a["name"].lower(),
            )
        except Exception:  # noqa: BLE001
            all_visible = []

        if not all_visible:
            no_box = middle.box()
            no_box.label(text="No assets saved yet")
        else:
            lib_root = resolve_library_root()
            _scene_props._rebuilding_browser_assets = True
            try:
                wm.melvil_browser_assets.clear()
                for asset in all_visible:
                    item = wm.melvil_browser_assets.add()
                    item.name = asset["name"]
                    item.asset_id = asset["id"]
                    item.asset_type = asset["type"]
                    preview_path = asset["preview_path"]
                    abs_path = (
                        str(Path(lib_root) / preview_path)
                        if preview_path else ""
                    )
                    item.abs_preview_path = abs_path
                    item.blend_path = asset["blend_path"]

                    # Register preview for GPU rendering.
                    icon_id = (
                        get_icon_id(asset["id"], abs_path)
                        if abs_path else None
                    )
                    preview_file = abs_path
                    if icon_id is None:
                        icon_id = get_placeholder_icon_id(asset["type"])
                        preview_file = (
                            _placeholder_path(asset["type"]) or ""
                        )
                    if icon_id is not None and preview_file:
                        self._panel.register_preview(
                            icon_id, preview_file,
                        )
            finally:
                _scene_props._rebuilding_browser_assets = False

            middle.template_list(
                "MELVIL_UL_asset_grid", "gpu_asset_list",
                wm, "melvil_browser_assets",
                wm, "melvil_browser_assets_index",
                rows=5,
                cols=2,
                cell_height=_ASSET_CARD_HEIGHT,
            )

        middle.separator()

        # -- Right column: asset details -------------------------------------
        selected_id = getattr(wm, "melvil_selected_asset_id", "")
        selected_asset = None
        selected_tags: list = []
        selected_kit_name = "Default"
        if selected_id:
            try:
                selected_asset = load_asset(selected_id)
                if selected_asset is not None:
                    selected_tags = list(load_tags_for_asset_ids([selected_id]))
                    kits = load_kits()
                    selected_kit_name = next(
                        (k["name"] for k in kits if k["id"] == selected_asset["kit_id"]),
                        "Default",
                    )
            except Exception:  # noqa: BLE001
                selected_asset = None

        wm.melvil_asset_tags.clear()
        for _tag in selected_tags:
            item = wm.melvil_asset_tags.add()
            item.name = _tag["name"]
            item.tag_id = _tag["id"]

        right.label(text="Asset details", icon="PROPERTIES")
        right_box = right.box()
        if selected_asset is not None:
            # Register the detail preview for GPU rendering.
            detail_preview_path = selected_asset["preview_path"]
            if detail_preview_path:
                abs_detail_preview = str(
                    Path(resolve_library_root()) / detail_preview_path
                )
                detail_icon_id = get_icon_id(selected_asset["id"], abs_detail_preview)
                if detail_icon_id is not None:
                    self._panel.register_preview(detail_icon_id, abs_detail_preview)

            draw_asset_details(
                right_box,
                selected_asset,
                selected_tags,
                selected_kit_name,
                wm=wm,
            )
        else:
            right_box.label(text="No asset selected", icon="INFO")

    def modal(self, context, event):
        if self._panel is None:
            return {"RUNNING_MODAL"}

        result = self._panel.handle_event(event)

        if result.redraw and context.area is not None:
            context.area.tag_redraw()
        if result.cancelled:
            self._cleanup(context)
            return {"CANCELLED"}
        return {"RUNNING_MODAL"}

    def cancel(self, context):
        self._cleanup(context)

    def _handle_icon_button(self, hit):
        """Dispatch an icon_button click to the appropriate action."""
        button_id = hit.id
        idx = hit.kwargs.get("index")
        if button_id == "tag_rename" and idx is not None:
            wm = bpy.context.window_manager
            tags = getattr(wm, "melvil_filter_tags", [])
            if 0 <= idx < len(tags):
                tag_item = tags[idx]
                bpy.ops.melvil.tag_rename("INVOKE_DEFAULT", tag_id=tag_item.tag_id)
        return EventResult(consumed=True, redraw=True)

    def _cleanup(self, context):
        if self._panel is not None:
            self._panel.detach()
            self._panel = None
        if context.area is not None:
            context.area.tag_redraw()
