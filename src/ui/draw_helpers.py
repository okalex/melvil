"""
Shared UI drawing helpers for Melvil.

Any panel or popup that needs to render an asset list imports
``draw_asset_section`` from here rather than duplicating the layout code.
"""

from __future__ import annotations

import bpy
from pathlib import Path

from ..core.library import resolve_db_path, resolve_library_root
from .previews_collection import get_icon_id, get_placeholder_icon_id
from ..db import open_db
from ..db.assets import get_asset as _get_asset, list_assets
from ..db.kits import list_kits
from ..db import tags as tags_db
from ..db.tags import (
    get_asset_tag_memberships as _get_asset_tag_memberships,
    get_asset_tag_names as _get_asset_tag_names,
    list_tags as _list_tags,
    list_tags_for_asset_ids as _list_tags_for_asset_ids,
)


class MELVIL_UL_asset_grid(bpy.types.UIList):
    """Scrollable asset card list for the browser middle column.

    Each row renders one asset card: a type icon + name row, then a box
    containing the preview image (or placeholder) and Load / Details buttons.
    """

    def draw_item(
        self,
        context,
        layout,
        data,
        item,
        icon,
        active_data,
        active_property,
        index: int = 0,
        flt_flag: int = 0,
    ) -> None:
        box = layout.box()

        # Name + type icon inline at the top of the card.
        name_row = box.row(align=True)
        name_row.label(text="", icon=_TYPE_ICONS.get(item.asset_type, "OBJECT_DATA"))
        name_row.label(text=item.name)

        icon_id = (
            get_icon_id(item.asset_id, item.abs_preview_path)
            if item.abs_preview_path
            else None
        )
        if icon_id is None:
            icon_id = get_placeholder_icon_id(item.asset_type)
        if icon_id is not None:
            box.template_icon(icon_value=icon_id, scale=5.0)

        selected_id = getattr(data, "melvil_selected_asset_id", "")
        btn_row = box.row(align=True)

        if _SHOW_LOAD_FOR_TYPE.get(item.asset_type, True):
            load_op = btn_row.operator("melvil.load_asset", text="Load")
            load_op.asset_id = item.asset_id

        detail_op = btn_row.operator(
            "melvil.asset_select",
            text="",
            icon="DISCLOSURE_TRI_RIGHT",
            depress=(item.asset_id == selected_id),
        )
        detail_op.asset_id = item.asset_id


class MELVIL_UL_asset_tags(bpy.types.UIList):
    """UIList for displaying asset tags in the browser detail panel."""

    def draw_filter(self, context, layout):
        pass

    def draw_item(self, context, layout, data, item, icon, active_data, active_property):
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            layout.label(text=item.name)
        elif self.layout_type == "GRID":
            layout.alignment = "CENTER"
            layout.label(text="", icon="TAG")


class MELVIL_UL_filter_tags(bpy.types.UIList):
    """UIList for the browser left-column tag filter list.

    Each item is rendered as a clickable toggle button so clicking
    a tag row invokes ``melvil.tag_filter_toggle`` for that tag.
    """

    def draw_item(self, context, layout, data, item, icon, active_data, active_property, index=0, flt_flag=0):
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            row = layout.row(align=True)
            row.label(
                text=item.name,
                icon="RADIOBUT_ON" if item.is_active else "RADIOBUT_OFF",
            )
            if item.is_active:
                rename_op = row.operator(
                    "melvil.tag_rename",
                    text="",
                    icon="GREASEPENCIL",
                    emboss=False,
                )
                rename_op.tag_id = item.tag_id


_TYPE_LABELS: dict[str, str] = {
    "MATERIAL": "Material",
    "MESH": "Mesh",
    "NODE_GROUP": "Node Group",
}

_TYPE_ICONS: dict[str, str] = {
    "MATERIAL": "MATERIAL",
    "MESH": "MESH_DATA",
    "NODE_GROUP": "NODETREE",
}

# Whether the Load button is shown for each asset type.
_SHOW_LOAD_FOR_TYPE: dict[str, bool] = {
    "MATERIAL": True,
    "MESH": True,
    "NODE_GROUP": False,
}


def draw_asset_section(
    layout,
    title: str,
    icon: str,
    assets,
    *,
    show_load: bool = True,
    selected_asset_id: str = "",
) -> None:
    """
    Draw a titled box containing one row per asset in *assets*.

    Each row has:
    - the asset name (label)
    - a Load button  (IMPORT icon → ``melvil.load_asset``) — only if *show_load* is True
    - a Details button (PROPERTIES icon → ``melvil.asset_select``) — always shown

    The Details button is rendered depressed when the asset is currently selected
    in the detail panel.  Clicking it again deselects.

    When *assets* is empty a placeholder label is shown instead.

    Parameters
    ----------
    layout:
        The ``bpy.types.UILayout`` to draw into.
    title:
        Section heading (e.g. ``"Meshes"``).
    icon:
        Blender icon identifier for the heading (e.g. ``"MESH_DATA"``).
    assets:
        Sequence of DB rows with at least ``"id"`` and ``"name"`` keys.
    show_load:
        When ``False`` the Load button is omitted (e.g. for asset types that
        must be loaded from a specific editor context).
    selected_asset_id:
        The UUID of the currently selected asset, used to depress its Details
        button so the user can see which asset is open in the detail panel.
    """

    layout.label(text=title, icon=icon)
    box = layout.box()

    if not assets:
        box.label(text=f"No {title.lower()} saved yet")
        layout.separator()
        return

    for asset in assets:
        row = box.row(align=True)
        row.label(text=asset["name"])

        if show_load:
            load_op = row.operator("melvil.load_asset", text="", icon="IMPORT")
            load_op.asset_id = asset["id"]

        detail_op = row.operator(
            "melvil.asset_select",
            text="",
            icon="FORWARD",
            depress=(asset["id"] == selected_asset_id),
        )
        detail_op.asset_id = asset["id"]

    layout.separator()


def draw_unified_asset_section(
    layout,
    assets,
    *,
    selected_asset_id: str = "",
    wm=None,
) -> None:
    """Draw the scrollable "Assets" card list for all *assets*.

    When *wm* is provided the assets are synced into the
    ``melvil_browser_assets`` collection on the WindowManager and rendered
    via ``template_list`` so that only the asset list scrolls — the rest of
    the popup stays fixed.

    Without *wm* the cards are drawn directly (no scroll container).

    Parameters
    ----------
    layout:
        The ``bpy.types.UILayout`` to draw into.
    assets:
        Sequence of DB rows with at least ``"id"``, ``"name"``, ``"type"``,
        and ``"preview_path"`` keys.  Should already be sorted by the caller.
    selected_asset_id:
        UUID of the currently selected asset; its Details button is shown
        depressed.
    wm:
        The ``bpy.types.WindowManager`` instance.  Required for the scrollable
        ``template_list`` path; when ``None`` the cards render inline.
    """
    layout.label(text="Assets", icon="ASSET_MANAGER")

    if not assets:
        box = layout.box()
        box.label(text="No assets saved yet")
        return

    if wm is not None:
        # Sync assets into the WM collection so template_list can display them.
        # Guard prevents the index-update callback from firing during rebuild.
        from . import scene_props as _sp

        _sp._rebuilding_browser_assets = True
        try:
            wm.melvil_browser_assets.clear()
            lib_root = resolve_library_root()
            for asset in assets:
                item = wm.melvil_browser_assets.add()
                item.name = asset["name"]
                item.asset_id = asset["id"]
                item.asset_type = asset["type"]
                preview_path = asset["preview_path"]
                item.abs_preview_path = (
                    str(Path(lib_root) / preview_path) if preview_path else ""
                )
                item.blend_path = asset["blend_path"]
        finally:
            _sp._rebuilding_browser_assets = False

        layout.template_list(
            "MELVIL_UL_asset_grid", "",
            wm, "melvil_browser_assets",
            wm, "melvil_browser_assets_index",
            rows=6,
        )
        return

    # Fallback: render cards directly (no scroll container).
    for asset in assets:
        _draw_asset_card(layout, asset, selected_asset_id)


def _draw_asset_card(layout, asset, selected_asset_id: str) -> None:
    """Render a single asset card into *layout*."""
    asset_type = asset["type"]

    box = layout.box()

    # Name + type icon at the top of the card.
    name_row = box.row(align=True)
    name_row.label(text="", icon=_TYPE_ICONS.get(asset_type, "OBJECT_DATA"))
    name_row.label(text=asset["name"])

    preview_path = asset["preview_path"]
    abs_preview_path = (
        str(Path(resolve_library_root()) / preview_path) if preview_path else None
    )
    icon_id = get_icon_id(asset["id"], abs_preview_path)
    if icon_id is None:
        icon_id = get_placeholder_icon_id(asset_type)
    if icon_id is not None:
        box.template_icon(icon_value=icon_id, scale=5.0)

    btn_row = box.row(align=True)
    if _SHOW_LOAD_FOR_TYPE.get(asset_type, True):
        load_op = btn_row.operator("melvil.load_asset", text="Load")
        load_op.asset_id = asset["id"]

    detail_op = btn_row.operator(
        "melvil.asset_select",
        text="",
        icon="DISCLOSURE_TRI_RIGHT",
        depress=(asset["id"] == selected_asset_id),
    )
    detail_op.asset_id = asset["id"]


def load_assets(asset_type=None, kit_id=None):
    """Query the configured library DB and return assets of *asset_type*.

    Raises on configuration or database errors — callers decide how to surface
    the failure in the UI.

    Parameters
    ----------
    asset_type:
        ``"MATERIAL"``, ``"MESH"``, or ``None`` to return all assets.
    kit_id:
        Kit UUID to filter by, or ``None`` to return assets from all kits.
    """
    with open_db(resolve_db_path()) as conn:
        return list_assets(conn, type=asset_type, kit_id=kit_id)


def load_kits():
    """Return all kits from the configured library DB, ordered by name.

    Raises on configuration or database errors — callers decide how to surface
    the failure in the UI.
    """
    with open_db(resolve_db_path()) as conn:
        return list_kits(conn)


def filter_assets(assets, query: str, asset_tag_names: dict | None = None):
    """Return assets whose names or tags contain *query* (case-insensitive, whitespace-ignored).

    When *asset_tag_names* is provided (a ``{asset_id: [tag_name, ...]}`` map),
    an asset is also included if any of its tag names match the query.

    When *query* is empty, blank, or ``None`` all assets are returned unchanged.
    """
    if not query:
        return assets
    normalized = query.replace(" ", "").lower()
    if not normalized:
        return assets
    result = []
    for a in assets:
        if normalized in a["name"].replace(" ", "").lower():
            result.append(a)
            continue
        if asset_tag_names:
            for tag_name in asset_tag_names.get(a["id"], []):
                if normalized in tag_name.replace(" ", "").lower():
                    result.append(a)
                    break
    return result


def load_asset_tag_memberships(asset_ids: list[str]) -> dict[str, set]:
    """Return ``{asset_id: {tag_id, ...}}`` for *asset_ids*.

    Returns an empty dict immediately when *asset_ids* is empty, without
    opening the database.  Raises on configuration or DB errors.
    """
    if not asset_ids:
        return {}
    with open_db(resolve_db_path()) as conn:
        return _get_asset_tag_memberships(conn, asset_ids)


def load_asset_tag_names(asset_ids: list[str]) -> dict[str, list[str]]:
    """Return ``{asset_id: [tag_name, ...]}`` (alphabetical) for *asset_ids*.

    Returns an empty dict immediately when *asset_ids* is empty, without
    opening the database.  Raises on configuration or DB errors.
    """
    if not asset_ids:
        return {}
    with open_db(resolve_db_path()) as conn:
        return _get_asset_tag_names(conn, asset_ids)


def load_tags_for_asset_ids(asset_ids: list[str]):
    """Return distinct tag rows (id, name) present on any of *asset_ids*.

    Raises on configuration or database errors — caller decides how to surface
    the failure in the UI.  Returns an empty list when *asset_ids* is empty.
    """
    if not asset_ids:
        return []
    with open_db(resolve_db_path()) as conn:
        return _list_tags_for_asset_ids(conn, asset_ids)


def load_all_tags():
    """Return all tag rows (id, name) ordered by name, regardless of usage.

    Raises on configuration or database errors — caller decides how to surface
    the failure in the UI.
    """
    with open_db(resolve_db_path()) as conn:
        return _list_tags(conn)


def draw_asset_details(
    layout,
    asset,
    tags: list,
    kit_name: str,
    wm,
) -> None:
    """Draw the asset detail panel with metadata and action buttons.

    Parameters
    ----------
    layout:
        The ``bpy.types.UILayout`` to draw into.
    asset:
        DB row with at least ``"id"``, ``"name"``, and ``"type"`` keys.
    tags:
        List of tag rows with ``"id"`` and ``"name"`` keys for this asset.
    kit_name:
        Human-readable name of the kit this asset belongs to.
    wm:
        The ``bpy.types.WindowManager`` instance; used for the inline name
        editor's draft state.
    """

    # Sync the draft name whenever the selected asset changes so that
    # switching assets always shows the current saved name.
    if wm.melvil_pending_name_asset_id != asset["id"]:
        wm.melvil_pending_name = asset["name"]
        wm.melvil_pending_name_asset_id = asset["id"]

    name_split = layout.split(factor=0.15)
    name_split.label(text="Name:")
    name_val = name_split.row()
    name_val.prop(wm, "melvil_pending_name", text="", textedit_update=True)
    confirm_col = name_val.column()
    confirm_col.scale_x = 0.15
    confirm_col.enabled = (
        wm.melvil_pending_name.strip() != asset["name"]
        and bool(wm.melvil_pending_name.strip())
    )
    confirm_op = confirm_col.operator(
        "melvil.asset_name_confirm", text="", icon="CHECKMARK"
    )
    confirm_op.asset_id = asset["id"]

    # Kit
    kit_split = layout.split(factor=0.15)
    kit_split.label(text="Kit:")
    kit_op = kit_split.operator_menu_enum("melvil.asset_set_kit", "kit_id", text=kit_name)
    kit_op.asset_id = asset["id"]

    # Type
    type_split = layout.split(factor=0.15)
    type_split.label(text="Type:")
    type_split.box(padding=0).label(text=_TYPE_LABELS.get(asset["type"], asset["type"]))

    # Source — path to the managed .blend file
    try:
        abs_blend_path = str(Path(resolve_library_root()) / asset["blend_path"])
    except Exception:  # noqa: BLE001
        abs_blend_path = ""
    source_split = layout.split(factor=0.15)
    source_split.label(text="Source:")
    source_val = source_split.row()
    source_val.box(padding=0).label(text=asset["blend_path"] or "")
    btn_col = source_val.column()
    btn_col.scale_x = 0.15
    open_op = btn_col.operator(
        "melvil.open_blend_file", text="", icon="BLENDER"
    )
    open_op.blend_path = abs_blend_path
    btn_col2 = source_val.column()
    btn_col2.scale_x = 0.15
    reveal_op = btn_col2.operator(
        "melvil.reveal_blend_file", text="", icon="FILE_FOLDER"
    )
    reveal_op.blend_path = abs_blend_path

    layout.separator()

    # Preview image (if available)
    preview_path = asset["preview_path"]
    if preview_path:
        layout.label(text="Preview image", icon="IMAGE_DATA")

        abs_preview_path = str(Path(resolve_library_root()) / preview_path)
        icon_id = get_icon_id(asset["id"], abs_preview_path)
        if icon_id is not None:
            box = layout.box()
            box.template_icon(icon_value=icon_id, scale=8.0)

    layout.separator()

    # Tags
    layout.label(text="Tags", icon="TAG")
    if wm is not None:
        list_row = layout.row()
        list_col = list_row.column()
        list_col.template_list(
            "MELVIL_UL_asset_tags", "",
            wm, "melvil_asset_tags",
            wm, "melvil_asset_tags_index",
            rows=5,
        )
        list_row.separator(factor=0.5)
        side_col = list_row.column()
        side_col.scale_x = 0.06

        add_op = side_col.operator("melvil.tag_add", text="", icon="ADD")
        add_op.asset_id = asset["id"]

        side_col.separator(factor=0.5)
        idx = wm.melvil_asset_tags_index
        tag_items = wm.melvil_asset_tags
        remove_col = side_col.column()
        remove_col.enabled = bool(tag_items) and 0 <= idx < len(tag_items)
        remove_op = remove_col.operator("melvil.tag_remove", text="", icon="REMOVE")
        remove_op.asset_id = asset["id"]
        remove_op.tag_id = tag_items[idx].tag_id if remove_col.enabled else ""
    elif tags:
        grid = layout.grid_flow(row_major=True, columns=0, even_columns=True, align=True)
        for tag in tags:
            grid.label(text=tag["name"])
    else:
        sub = layout.row()
        sub.enabled = False
        sub.label(text="No tags")

    layout.separator()

    del_row = layout.row()
    del_row.alignment = "LEFT"
    del_row.alert = True
    del_op = del_row.operator("melvil.delete_asset", text="Delete Asset", icon="TRASH")
    del_op.asset_id = asset["id"]

    layout.separator()


def load_asset(asset_id: str):
    """Return a single asset DB row by *asset_id*, or ``None`` if not found.

    Raises on configuration or database errors — callers decide how to surface
    the failure in the UI.
    """
    with open_db(resolve_db_path()) as conn:
        return _get_asset(conn, asset_id)
