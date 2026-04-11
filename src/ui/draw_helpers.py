"""
Shared UI drawing helpers for Melvil.

Any panel or popup that needs to render an asset list imports
``draw_asset_section`` from here rather than duplicating the layout code.
"""

from __future__ import annotations

from ..core.library import resolve_db_path
from ..db import open_db
from ..db.assets import list_assets
from ..db.kits import list_kits
from ..db import tags as tags_db
from ..db.tags import (
    get_asset_tag_memberships as _get_asset_tag_memberships,
    list_tags_for_asset_ids as _list_tags_for_asset_ids,
)


def draw_asset_section(
    layout,
    title: str,
    icon: str,
    assets,
    *,
    show_load: bool = True,
    kits=(),
    asset_tags: dict | None = None,
    active_tag_ids=(),
) -> None:
    """
    Draw a titled box containing one row per asset in *assets*.

    Each row has:
    - the asset name (label)
    - a Load button  (IMPORT icon → ``melvil.load_asset``) — only if *show_load* is True
    - a Move to Kit button — only if *kits* is non-empty
    - a Delete button (TRASH icon → ``melvil.delete_asset``)

    When *asset_tags* is provided, a second sub-row is rendered below each asset
    showing its tag pills (clickable, invoking ``melvil.tag_filter_toggle``) and
    a pencil button (``melvil.asset_edit_tags``).  The sub-row is always drawn
    so the layout height stays consistent even for untagged assets.

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
    kits:
        When provided, a "Move to Kit" button is shown per asset row that
        invokes ``melvil.asset_set_kit``.
    asset_tags:
        Optional ``{asset_id: [{id, name}, ...]}`` mapping.  When supplied,
        each asset gets an inline tag pill row below its main row.
    active_tag_ids:
        UUIDs of tags currently active as filters (renders pills depressed).
    """

    layout.label(text=title, icon=icon)
    box = layout.box()

    if not assets:
        box.label(text=f"No {title.lower()} saved yet")
        return

    active_set = set(active_tag_ids)

    for asset in assets:
        row = box.row(align=True)
        row.label(text=asset["name"])

        if show_load:
            load_op = row.operator("melvil.load_asset", text="", icon="IMPORT")
            load_op.asset_id = asset["id"]

        if kits:
            move_op = row.operator("melvil.asset_set_kit", text="", icon="FOLDER_REDIRECT")
            move_op.asset_id = asset["id"]

        del_op = row.operator("melvil.delete_asset", text="", icon="TRASH")
        del_op.asset_id = asset["id"]

        if asset_tags is not None:
            tag_row = box.row(align=True)
            tags_for_asset = asset_tags.get(asset["id"], [])
            if tags_for_asset:
                for tag in tags_for_asset:
                    pill = tag_row.operator(
                        "melvil.tag_filter_toggle",
                        text=tag["name"],
                        depress=(tag["id"] in active_set),
                    )
                    pill.tag_id = tag["id"]
            else:
                sub = tag_row.row()
                sub.enabled = False
                sub.label(text="No tags")
            edit_op = tag_row.operator(
                "melvil.asset_edit_tags", text="", icon="GREASEPENCIL"
            )
            edit_op.asset_id = asset["id"]
            edit_op.asset_name = asset["name"]

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


def filter_assets(assets, query: str):
    """Return assets whose names contain *query* (case-insensitive, whitespace-ignored).

    When *query* is empty, blank, or ``None`` all assets are returned unchanged.
    """
    if not query:
        return assets
    normalized = query.replace(" ", "").lower()
    if not normalized:
        return assets
    return [a for a in assets if normalized in a["name"].replace(" ", "").lower()]


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
