"""
AssetWriter: serialises a Blender datablock to a managed .blend file and
registers the asset in the Blammo database.

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

Node group handling
-------------------
When ``asset_type`` is ``"NODE_GROUP"`` the writer discovers all nested node
groups referenced by the root node tree (recursively) and writes every one of
them into the same managed ``.blend`` file.  This ensures that a group which
depends on shared sub-groups is fully self-contained inside the library.
"""

from __future__ import annotations

import re
import uuid
from pathlib import Path

from .textures import collect_external_images, copy_textures
from ..db.assets import insert_asset
from ..db.kits import DEFAULT_KIT_ID


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
        path_remap="RELATIVE_ALL",
        compress=False,
        fake_user=True,
    )


def _collect_nested_node_groups(node_tree) -> set:
    """
    Recursively collect *node_tree* and every node group it references.

    Traverses GROUP-type nodes in *node_tree* and follows their
    ``node_tree`` pointer, continuing recursively until all dependencies
    have been visited.  The returned set contains the root node tree and
    all discovered nested node trees.
    """
    collected: set = set()

    def _walk(tree) -> None:
        if tree in collected:
            return
        collected.add(tree)
        for node in tree.nodes:
            if node.type == "GROUP":
                nested = getattr(node, "node_tree", None)
                if nested is not None:
                    _walk(nested)

    _walk(node_tree)
    return collected


class AssetWriter:
    """Write a datablock to the library and register it in the database."""

    def __init__(self, library_root: Path, conn) -> None:
        self.library_root = library_root
        self.conn = conn

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def write(self, datablock, name: str, asset_type: str, kit_id: str = DEFAULT_KIT_ID) -> str:
        """
        Persist *datablock* as a managed .blend file and insert a DB record.

        Parameters
        ----------
        datablock:
            Any Blender data-block (``bpy.types.Material``,
            ``bpy.types.Object``, ``bpy.types.NodeTree``, …).
        name:
            Human-readable name for the asset (stored in the DB and used to
            derive the filename).
        asset_type:
            One of ``"MATERIAL"``, ``"MESH"``, or ``"NODE_GROUP"``.
        kit_id:
            UUID of the kit this asset belongs to.  Defaults to the General
            kit when not specified.

        Returns
        -------
        str
            The UUID of the newly created asset record.
        """
        asset_id = str(uuid.uuid4())
        blend_filename = self._build_filename(name, asset_id)
        blend_path = self.library_root / blend_filename

        if asset_type == "NODE_GROUP":
            self._write_node_group_with_textures(datablock, name, blend_path)
        else:
            self._write_with_textures(datablock, name, blend_path)

        insert_asset(
            self.conn,
            id=asset_id,
            name=name,
            type=asset_type,
            blend_path=blend_filename,  # relative to library root
            kit_id=kit_id,
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

    def _write_with_textures(self, datablock, name: str, blend_path: Path) -> None:
        """Copy textures, temporarily repoint paths, write blend, then restore.

        The datablock is temporarily renamed to *name* before writing so that
        the name stored in the DB matches the name inside the .blend file,
        which is what ``AssetReader`` uses to locate the datablock on load.

        The datablock is also temporarily marked as an asset so that Blender's
        Asset Browser can discover it after the .blend file is written.  If the
        datablock was not already an asset it is cleared again afterwards so
        the user's scene state is unchanged.
        """
        textures_dir = self.library_root / "textures"
        images = collect_external_images(datablock)
        remapping = copy_textures(images, textures_dir)

        # Record original paths so we can unconditionally restore them.
        original_paths: dict = {img: img.filepath for img in images if img.filepath in remapping}
        original_name: str = datablock.name
        was_asset: bool = datablock.asset_data is not None

        try:
            # Rename to the user-chosen name so the .blend file and DB agree.
            datablock.name = name
            # Repoint to relative paths (//textures/<file>) before writing.
            for img in original_paths:
                img.filepath = remapping[img.filepath]
            # Mark as asset so that Blender's Asset Browser indexes this datablock.
            if not was_asset:
                datablock.asset_mark()

            self.library_root.mkdir(parents=True, exist_ok=True)
            _write_blend_file(str(blend_path), {datablock})
        finally:
            datablock.name = original_name
            for img, original in original_paths.items():
                img.filepath = original
            # Restore original asset state so the live scene datablock is unchanged.
            if not was_asset:
                datablock.asset_clear()

    def _write_node_group_with_textures(self, node_tree, name: str, blend_path: Path) -> None:
        """Write a node group and all its nested dependencies to a .blend file.

        Collects every node group reachable from *node_tree* (recursively
        following GROUP-type nodes), gathers external textures from the full
        dependency tree, temporarily repoints image paths, writes the complete
        set of datablocks, then unconditionally restores all original paths.

        The root *node_tree* is temporarily renamed to *name* before writing
        so that the name stored in the DB matches the name inside the .blend
        file, which is what ``AssetReader`` uses to locate the datablock.
        """
        # Collect the root group plus all nested groups.
        all_groups = _collect_nested_node_groups(node_tree)

        textures_dir = self.library_root / "textures"
        # collect_external_images recurses into nested groups automatically.
        images = collect_external_images(node_tree)
        remapping = copy_textures(images, textures_dir)

        original_paths: dict = {img: img.filepath for img in images if img.filepath in remapping}
        original_name: str = node_tree.name
        was_asset: bool = node_tree.asset_data is not None

        try:
            node_tree.name = name
            for img in original_paths:
                img.filepath = remapping[img.filepath]
            # Mark only the root node tree as an asset; nested dependencies
            # should not appear as independent assets in the browser.
            if not was_asset:
                node_tree.asset_mark()

            self.library_root.mkdir(parents=True, exist_ok=True)
            _write_blend_file(str(blend_path), all_groups)
        finally:
            node_tree.name = original_name
            for img, original in original_paths.items():
                img.filepath = original
            if not was_asset:
                node_tree.asset_clear()
