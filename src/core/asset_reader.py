"""
AssetReader: loads a datablock from a managed .blend file back into the
current Blender session.

Usage::

    with open_db(resolve_db_path()) as conn:
        reader = AssetReader(resolve_library_root(), conn)
        material = reader.read(asset_id)

The returned datablock is appended (not linked) into the current session.
For ``"MESH"`` assets the caller is responsible for linking the returned
``bpy.types.Object`` to the desired collection.
"""

from __future__ import annotations

from pathlib import Path

from ..db.assets import get_asset


# Maps the asset_type stored in the DB to the bpy.data collection name used
# when appending with bpy.data.libraries.load().
_TYPE_TO_COLLECTION: dict[str, str] = {
    "MATERIAL": "materials",
    "MESH": "objects",
}


class AssetNotFoundError(Exception):
    """Raised when an asset_id does not exist in the database."""


def _load_datablock(filepath: str, asset_name: str, collection: str):
    """
    Thin wrapper around ``bpy.data.libraries.load()``.

    Isolated in its own function so tests can monkeypatch it without
    importing bpy.

    Returns the first appended item from *collection*, or ``None`` if
    the named datablock was not found in the file.
    """
    import bpy  # noqa: PLC0415 — imported here so the module loads outside Blender

    with bpy.data.libraries.load(filepath, link=False) as (data_from, data_to):
        available = getattr(data_from, collection, [])
        if asset_name in available:
            setattr(data_to, collection, [asset_name])

    loaded = getattr(data_to, collection, [])
    return loaded[0] if loaded else None


class AssetReader:
    """Append a managed asset into the current Blender session."""

    def __init__(self, library_root: Path, conn) -> None:
        self.library_root = library_root
        self.conn = conn

    def read(self, asset_id: str):
        """
        Append the asset identified by *asset_id* from its managed .blend file.

        Parameters
        ----------
        asset_id:
            UUID of the asset as stored in the database.

        Returns
        -------
        bpy.types.ID
            The appended datablock.  For ``"MESH"`` assets this is a
            ``bpy.types.Object``; for ``"MATERIAL"`` assets a
            ``bpy.types.Material``.

        Raises
        ------
        AssetNotFoundError
            If *asset_id* does not exist in the database.
        ValueError
            If the asset type is not recognised.
        """
        row = get_asset(self.conn, asset_id)
        if row is None:
            raise AssetNotFoundError(
                f"Melvil: asset '{asset_id}' was not found in the database."
            )

        asset_type = row["type"]
        collection = _TYPE_TO_COLLECTION.get(asset_type)
        if collection is None:
            raise ValueError(
                f"Melvil: unsupported asset type '{asset_type}'."
            )

        blend_path = self.library_root / row["blend_path"]
        return _load_datablock(str(blend_path), row["name"], collection)
