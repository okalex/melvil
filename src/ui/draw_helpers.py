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


def draw_asset_section(layout, title: str, icon: str, assets, *, show_load: bool = True, kits=()) -> None:
    """
    Draw a titled box containing one row per asset in *assets*.

    Each row has:
    - the asset name (label)
    - a Load button  (IMPORT icon → ``melvil.load_asset``) — only if *show_load* is True
    - a Delete button (TRASH icon → ``melvil.delete_asset``)

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

        if kits:
            move_op = row.operator("melvil.asset_set_kit", text="", icon="FOLDER_REDIRECT")
            move_op.asset_id = asset["id"]

        del_op = row.operator("melvil.delete_asset", text="", icon="TRASH")
        del_op.asset_id = asset["id"]

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
