"""
Shared UI drawing helpers for Melvil.

Any panel or popup that needs to render an asset list imports
``draw_asset_section`` from here rather than duplicating the layout code.
"""

from __future__ import annotations

from ..core.library import resolve_db_path
from ..db import open_db
from ..db.assets import get_asset as _get_asset, list_assets
from ..db.kits import list_kits
from ..db import tags as tags_db
from ..db.tags import (
    get_asset_tag_memberships as _get_asset_tag_memberships,
    get_asset_tag_names as _get_asset_tag_names,
    list_tags_for_asset_ids as _list_tags_for_asset_ids,
)

_TYPE_LABELS: dict[str, str] = {
    "MATERIAL": "Material",
    "MESH": "Mesh",
    "NODE_GROUP": "Node Group",
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
            icon="PROPERTIES",
            depress=(asset["id"] == selected_asset_id),
        )
        detail_op.asset_id = asset["id"]

    layout.separator()


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


def load_tags_with_usage():
    """Return all tags with usage counts from the configured library DB.

    Raises on configuration or database errors — callers decide how to surface
    the failure in the UI.
    """
    with open_db(resolve_db_path()) as conn:
        return tags_db.list_tags_with_usage(conn)


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


def draw_tag_filter_pills(
    layout,
    visible_tags,
    active_tag_ids: list[str],
) -> None:
    """Draw the tag filter pill row and, when filters are active, a clear button.

    Parameters
    ----------
    layout:
        The ``bpy.types.UILayout`` to draw into.
    visible_tags:
        Sequence of tag rows with ``"id"`` and ``"name"`` keys — only the tags
        present on assets currently visible in the browser.
    active_tag_ids:
        UUIDs of tags currently used as filters (rendered depressed).
    """
    if not visible_tags:
        return

    row = layout.row(align=True)
    active_set = set(active_tag_ids)
    for tag in visible_tags:  # already sorted by name from DB query
        btn = row.operator(
            "melvil.tag_filter_toggle",
            text=tag["name"],
            depress=(tag["id"] in active_set),
        )
        btn.tag_id = tag["id"]

    if active_tag_ids:
        layout.operator("melvil.tag_filter_clear", text="Clear filters", icon="X")


def draw_tag_management_section(layout, tags_with_usage, sort_by: str = "NAME") -> None:
    """Draw the tag management inline section.

    Parameters
    ----------
    layout:
        The ``bpy.types.UILayout`` to draw into.
    tags_with_usage:
        Sequence of tag rows, each with ``"id"``, ``"name"``, and
        ``"usage_count"`` keys.
    sort_by:
        ``"NAME"`` (alphabetical) or ``"USAGE"`` (descending usage count,
        then alphabetical).
    """
    # Header row: sort toggles on the left, New Tag button on the right.
    header_row = layout.row(align=False)
    sort_row = header_row.row(align=True)
    sort_row.label(text="Sort:")
    name_btn = sort_row.operator(
        "melvil.tag_sort_toggle",
        text="Name",
        depress=(sort_by == "NAME"),
    )
    name_btn.sort_by = "NAME"
    usage_btn = sort_row.operator(
        "melvil.tag_sort_toggle",
        text="Usage",
        depress=(sort_by == "USAGE"),
    )
    usage_btn.sort_by = "USAGE"
    header_row.operator("melvil.tag_create", text="", icon="ADD")

    # Sort the tags.
    if sort_by == "USAGE":
        sorted_tags = sorted(tags_with_usage, key=lambda t: (-t["usage_count"], t["name"]))
    else:
        sorted_tags = sorted(tags_with_usage, key=lambda t: t["name"])

    box = layout.box()
    if not sorted_tags:
        box.label(text="No tags in library")
    else:
        for tag in sorted_tags:
            row = box.row(align=True)

            # Name column — visually muted (disabled) when usage is zero.
            name_col = row.column()
            name_col.enabled = tag["usage_count"] > 0
            name_col.label(text=tag["name"])

            row.label(text=f"({tag['usage_count']})")

            rename_op = row.operator("melvil.tag_rename", text="", icon="GREASEPENCIL")
            rename_op.tag_id = tag["id"]

            del_op = row.operator("melvil.tag_delete", text="", icon="TRASH")
            del_op.tag_id = tag["id"]

    # "Delete Unused Tags" button — only shown when at least one unused tag exists.
    if any(t["usage_count"] == 0 for t in tags_with_usage):
        layout.operator(
            "melvil.tag_delete_unused",
            text="Delete Unused Tags",
            icon="CANCEL",
        )


def draw_asset_details(
    layout,
    asset,
    tags: list,
    kit_name: str,
    active_tag_ids=(),
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
    active_tag_ids:
        UUIDs of tags currently active as filters (renders pills depressed).
    """
    layout.label(text=asset["name"], icon="INFO")
    layout.separator()

    col = layout.column(align=False)

    # Type
    type_row = col.row()
    type_row.label(text="Type:")
    type_row.label(text=_TYPE_LABELS.get(asset["type"], asset["type"]))

    # Kit
    kit_row = col.row()
    kit_row.label(text="Kit:")
    kit_row.label(text=kit_name)

    col.separator()

    # Tags
    col.label(text="Tags:")
    if tags:
        active_set = set(active_tag_ids)
        tag_row = col.row(align=True)
        for tag in tags:
            pill = tag_row.operator(
                "melvil.tag_filter_toggle",
                text=tag["name"],
                depress=(tag["id"] in active_set),
            )
            pill.tag_id = tag["id"]
    else:
        sub = col.row()
        sub.enabled = False
        sub.label(text="No tags")

    col.separator()

    # Action buttons
    rename_op = col.operator("melvil.asset_rename", text="Rename", icon="GREASEPENCIL")
    rename_op.asset_id = asset["id"]

    edit_tags_op = col.operator("melvil.asset_edit_tags", text="Edit Tags", icon="TAG")
    edit_tags_op.asset_id = asset["id"]
    edit_tags_op.asset_name = asset["name"]

    kit_op = col.operator("melvil.asset_set_kit", text="Move to Kit", icon="FOLDER_REDIRECT")
    kit_op.asset_id = asset["id"]

    col.separator()

    del_op = col.operator("melvil.delete_asset", text="Delete", icon="TRASH")
    del_op.asset_id = asset["id"]


def load_asset(asset_id: str):
    """Return a single asset DB row by *asset_id*, or ``None`` if not found.

    Raises on configuration or database errors — callers decide how to surface
    the failure in the UI.
    """
    with open_db(resolve_db_path()) as conn:
        return _get_asset(conn, asset_id)
