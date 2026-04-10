"""
Texture discovery and copying utilities for managed .blend files.

When writing an asset to the library, we:
1. Find all externally-referenced images used by the datablock.
2. Copy those image files into ``<library_root>/textures/``.
3. Temporarily repoint each image's filepath to the relative path
   ``//textures/<filename>`` (relative to the managed .blend file,
   which lives directly inside the library root).
4. Write the .blend file.
5. Restore the original filepaths.

Packed images (embedded in the current .blend) are left as-is; they will
be packed into the managed .blend file automatically by Blender.
"""

from __future__ import annotations

import shutil
from pathlib import Path


def collect_external_images(datablock) -> list:
    """
    Return a list of ``bpy.types.Image`` objects that are externally
    referenced (not packed) and are used by *datablock*.

    Handles:
    - Materials with a node tree (``ShaderNodeTexImage`` nodes).
    - Objects with material slots (recurses into each material).
    """
    images: list = []
    seen: set = set()

    def _scan_material(mat) -> None:
        if mat is None or not getattr(mat, "node_tree", None):
            return
        for node in mat.node_tree.nodes:
            if node.type == "TEX_IMAGE" and getattr(node, "image", None):
                img = node.image
                if img.id_data not in seen and _is_external(img):
                    seen.add(img.id_data)
                    images.append(img)

    # Material datablock
    if hasattr(datablock, "node_tree"):
        _scan_material(datablock)
    # Object datablock with material slots
    elif hasattr(datablock, "material_slots"):
        for slot in datablock.material_slots:
            _scan_material(slot.material)

    return images


def _is_external(img) -> bool:
    """Return True iff the image has an external filepath and is not packed."""
    if getattr(img, "packed_file", None) is not None:
        return False
    filepath = getattr(img, "filepath", "").strip()
    return bool(filepath) and img.source == "FILE"


def copy_textures(images: list, textures_dir: Path) -> dict[str, str]:
    """
    Copy *images* into *textures_dir*, creating the directory if necessary.

    Returns a mapping of ``original_filepath -> relative_blender_path`` where
    the relative path is ``//textures/<filename>`` (suitable for use as
    ``bpy.types.Image.filepath`` in a .blend file stored at the library root).

    If a destination file already exists it is not overwritten (assumed to be
    the same file from a previous write).  Filename collisions between
    different source images are resolved by appending a counter suffix before
    the extension.
    """
    if not images:
        return {}

    textures_dir.mkdir(parents=True, exist_ok=True)
    remapping: dict[str, str] = {}

    for img in images:
        src = Path(img.filepath_from_user())
        if not src.is_file():
            continue  # missing source — skip silently; Blender will warn

        dest_name = _unique_dest_name(src.name, textures_dir)
        dest = textures_dir / dest_name

        if not dest.exists():
            shutil.copy2(src, dest)

        remapping[img.filepath] = f"//textures/{dest_name}"

    return remapping


def _unique_dest_name(name: str, directory: Path) -> str:
    """
    Return a filename that does not collide with existing files in *directory*.
    If *name* is free, return it unchanged; otherwise append ``_2``, ``_3``, …
    before the extension.
    """
    candidate = Path(name)
    stem, suffix = candidate.stem, candidate.suffix
    dest = directory / name
    if not dest.exists():
        return name

    counter = 2
    while True:
        new_name = f"{stem}_{counter}{suffix}"
        if not (directory / new_name).exists():
            return new_name
        counter += 1
