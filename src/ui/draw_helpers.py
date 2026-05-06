"""
Shared UI drawing helpers for Blammo.

Any panel or popup that needs to render an asset list imports
helpers from here rather than duplicating the layout code.
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
from .asset_types import type_label


class BLAMMO_UL_asset_tags(bpy.types.UIList):
    """UIList for displaying asset tags in the browser detail panel."""

    def draw_filter(self, context, layout):
        pass

    def draw_item(self, context, layout, data, item, icon, active_data, active_property):
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            layout.label(text=item.name)
        elif self.layout_type == "GRID":
            layout.alignment = "CENTER"
            layout.label(text="", icon="TAG")





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
    if wm.blammo_pending_name_asset_id != asset["id"]:
        wm.blammo_pending_name = asset["name"]
        wm.blammo_pending_name_asset_id = asset["id"]

    name_split = layout.split(factor=0.15)
    name_split.label(text="Name:")
    name_val = name_split.row()
    name_val.prop(wm, "blammo_pending_name", text="", textedit_update=True)
    confirm_col = name_val.column()
    confirm_col.scale_x = 0.15
    confirm_col.enabled = (
        wm.blammo_pending_name.strip() != asset["name"]
        and bool(wm.blammo_pending_name.strip())
    )
    confirm_op = confirm_col.operator(
        "blammo.asset_name_confirm", text="", icon="CHECKMARK"
    )
    confirm_op.asset_id = asset["id"]

    # Kit
    kit_split = layout.split(factor=0.15)
    kit_split.label(text="Kit:")
    kit_op = kit_split.operator_menu_enum("blammo.asset_set_kit", "kit_id", text=kit_name)
    kit_op.asset_id = asset["id"]

    # Type
    type_split = layout.split(factor=0.15)
    type_split.label(text="Type:")
    type_split.box(padding=0).label(text=type_label(asset["type"]))

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
        "blammo.open_blend_file", text="", icon="BLENDER"
    )
    open_op.blend_path = abs_blend_path
    btn_col2 = source_val.column()
    btn_col2.scale_x = 0.15
    reveal_op = btn_col2.operator(
        "blammo.reveal_blend_file", text="", icon="FILE_FOLDER"
    )
    reveal_op.blend_path = abs_blend_path

    layout.separator(factor=2.0)

    # Preview image (if available)
    preview_path = asset["preview_path"]
    if preview_path:
        layout.label(text="Preview image", icon="IMAGE_DATA")

        abs_preview_path = str(Path(resolve_library_root()) / preview_path)
        icon_id = get_icon_id(asset["id"], abs_preview_path)
        if icon_id is not None:
            box = layout.box()
            box.template_icon(icon_value=icon_id, scale=8.0)

    layout.separator(factor=2.0)

    # Tags
    layout.label(text="Tags", icon="TAG")
    if wm is not None:
        list_row = layout.row()
        list_col = list_row.column()
        list_col.template_list(
            "BLAMMO_UL_asset_tags", "",
            wm, "blammo_asset_tags",
            wm, "blammo_asset_tags_index",
            rows=5,
        )
        list_row.separator(factor=0.5)
        side_col = list_row.column()
        side_col.scale_x = 0.06

        add_op = side_col.operator("blammo.tag_add", text="", icon="ADD")
        add_op.asset_id = asset["id"]

        side_col.separator(factor=0.5)
        idx = wm.blammo_asset_tags_index
        tag_items = wm.blammo_asset_tags
        remove_col = side_col.column()
        remove_col.enabled = bool(tag_items) and 0 <= idx < len(tag_items)
        remove_op = remove_col.operator("blammo.tag_remove", text="", icon="REMOVE")
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

    layout.separator(factor=2.0)

    del_row = layout.row()
    del_row.alignment = "LEFT"
    del_row.alert = True
    del_op = del_row.operator("blammo.delete_asset", text="Delete Asset", icon="TRASH")
    del_op.asset_id = asset["id"]

    layout.separator()


def load_asset(asset_id: str):
    """Return a single asset DB row by *asset_id*, or ``None`` if not found.

    Raises on configuration or database errors — callers decide how to surface
    the failure in the UI.
    """
    with open_db(resolve_db_path()) as conn:
        return _get_asset(conn, asset_id)
