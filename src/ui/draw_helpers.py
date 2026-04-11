"""
Shared UI drawing helpers for Melvil.

Any panel or popup that needs to render an asset list imports
``draw_asset_section`` from here rather than duplicating the layout code.
"""

from __future__ import annotations

from ..core.library import resolve_db_path
from ..db import open_db
from ..db.assets import list_assets


def draw_asset_section(layout, title: str, icon: str, assets) -> None:
    """
    Draw a titled box containing one row per asset in *assets*.

    Each row has:
    - the asset name (label)
    - a Load button  (IMPORT icon → ``melvil.load_asset``)
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
    """
    box = layout.box()
    box.label(text=title, icon=icon)

    if not assets:
        box.label(text=f"No {title.lower()} saved yet")
        return

    for asset in assets:
        row = box.row(align=True)
        row.label(text=asset["name"])

        load_op = row.operator("melvil.load_asset", text="", icon="IMPORT")
        load_op.asset_id = asset["id"]

        del_op = row.operator("melvil.delete_asset", text="", icon="TRASH")
        del_op.asset_id = asset["id"]


def load_assets(asset_type=None):
    """Query the configured library DB and return assets of *asset_type*.

    Raises on configuration or database errors — callers decide how to surface
    the failure in the UI.

    Parameters
    ----------
    asset_type:
        ``"MATERIAL"``, ``"MESH"``, or ``None`` to return all assets.
    """
    with open_db(resolve_db_path()) as conn:
        return list_assets(conn, type=asset_type)
