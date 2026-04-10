"""
AssetWriter: serialises a Blender datablock to a managed .blend file and
registers the asset in the Melvil database.

Usage::

    with open_db(resolve_db_path()) as conn:
        writer = AssetWriter(resolve_library_root(), conn)
        asset_id = writer.write(bpy.context.object, "Red Metal", "MESH")

The managed .blend file is written at::

    <library_root>/<slug>_<short_id>.blend

where *slug* is a lower-case, ASCII-safe version of *name* and *short_id* is
the first 8 hex characters of the asset UUID (hyphens removed).

Texture handling
----------------
Externally-referenced images used by the datablock are:

1. Copied into ``<library_root>/textures/``.
2. Temporarily repointed to ``//textures/<filename>`` (relative to the
   managed .blend file, which is stored directly in the library root).
3. After ``bpy.data.libraries.write()`` completes the original paths are
   restored unconditionally (even on error).
"""

from __future__ import annotations

import re
import uuid
from pathlib import Path

from .textures import collect_external_images, copy_textures
from ..db.assets import insert_asset


def _slugify(name: str) -> str:
    """Convert *name* to a lowercase, filesystem-safe ASCII slug."""
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower())
    return slug.strip("_") or "asset"


def _write_blend_file(filepath: str, datablocks: set) -> None:
    """
    Thin wrapper around ``bpy.data.libraries.write()``.

    Isolated in its own function so tests can monkeypatch it without
    importing bpy.
    """
    import bpy  # noqa: PLC0415 — imported here so the module loads outside Blender

    bpy.data.libraries.write(
        filepath,
        datablocks,
        relative_remap=True,
        compress=False,
        fake_user=True,
    )


class AssetWriter:
    """Write a datablock to the library and register it in the database."""

    def __init__(self, library_root: Path, conn) -> None:
        self.library_root = library_root
        self.conn = conn

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def write(self, datablock, name: str, asset_type: str) -> str:
        """
        Persist *datablock* as a managed .blend file and insert a DB record.

        Parameters
        ----------
        datablock:
            Any Blender data-block (``bpy.types.Material``,
            ``bpy.types.Object``, …).
        name:
            Human-readable name for the asset (stored in the DB and used to
            derive the filename).
        asset_type:
            One of ``"MATERIAL"`` or ``"MESH"``.

        Returns
        -------
        str
            The UUID of the newly created asset record.
        """
        asset_id = str(uuid.uuid4())
        blend_filename = self._build_filename(name, asset_id)
        blend_path = self.library_root / blend_filename

        self._write_with_textures(datablock, blend_path)

        insert_asset(
            self.conn,
            id=asset_id,
            name=name,
            type=asset_type,
            blend_path=blend_filename,  # relative to library root
        )
        self.conn.commit()
        return asset_id

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_filename(name: str, asset_id: str) -> str:
        slug = _slugify(name)
        short_id = asset_id.replace("-", "")[:8]
        return f"{slug}_{short_id}.blend"

    def _write_with_textures(self, datablock, blend_path: Path) -> None:
        """Copy textures, temporarily repoint paths, write blend, then restore."""
        textures_dir = self.library_root / "textures"
        images = collect_external_images(datablock)
        remapping = copy_textures(images, textures_dir)

        # Record original paths so we can unconditionally restore them.
        original_paths: dict = {img: img.filepath for img in images if img.filepath in remapping}

        try:
            # Repoint to relative paths (//textures/<file>) before writing.
            for img in original_paths:
                img.filepath = remapping[img.filepath]

            self.library_root.mkdir(parents=True, exist_ok=True)
            _write_blend_file(str(blend_path), {datablock})
        finally:
            for img, original in original_paths.items():
                img.filepath = original
