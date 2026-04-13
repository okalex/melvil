"""
Thin wrapper around bpy.utils.previews.ImagePreviewCollection.

The collection is created at addon register time and destroyed at unregister.
Callers use get_icon_id() to retrieve a Blender icon_id for a preview PNG;
the first call for a given asset loads it from disk and subsequent calls
return the cached value.

Placeholder images for assets without a preview are stored inside the addon
at ``resources/img/placeholder_{type}.png`` and loaded on first access via
get_placeholder_icon_id().
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

_collection = None  # bpy.utils.previews.ImagePreviewCollection

# Stable keys used to cache placeholder images in the collection.
_PLACEHOLDER_KEYS: dict[str, str] = {
    "MATERIAL": "PLACEHOLDER_MATERIAL",
    "MESH": "PLACEHOLDER_MESH",
    "NODE_GROUP": "PLACEHOLDER_NODE_GROUP",
}

_PLACEHOLDER_FILENAMES: dict[str, str] = {
    "MATERIAL": "placeholder_material.png",
    "MESH": "placeholder_mesh.png",
    "NODE_GROUP": "placeholder_node_group.png",
}

# Resources directory is two levels up from this file: src/ui/ → src/ → resources/img/
_RESOURCES_DIR = Path(__file__).parent.parent / "resources" / "img"


def _placeholder_path(asset_type: str) -> Optional[str]:
    filename = _PLACEHOLDER_FILENAMES.get(asset_type)
    if filename is None:
        return None
    return str(_RESOURCES_DIR / filename)


def register() -> None:
    import bpy

    global _collection
    _collection = bpy.utils.previews.new()


def unregister() -> None:
    import bpy

    global _collection
    if _collection is not None:
        bpy.utils.previews.remove(_collection)
        _collection = None


def get_icon_id(asset_id: str, abs_path: Optional[str]) -> Optional[int]:
    """
    Return the Blender icon_id for the asset preview, or None if the
    preview file does not exist. Loads from disk on first access;
    subsequent calls for the same asset_id return the cached icon_id.
    """
    if _collection is None or abs_path is None:
        return None
    if not os.path.isfile(abs_path):
        return None
    if asset_id not in _collection:
        _collection.load(asset_id, abs_path, "IMAGE")
    return _collection[asset_id].icon_id


def get_placeholder_icon_id(asset_type: str) -> Optional[int]:
    """
    Return the Blender icon_id for the placeholder image matching *asset_type*,
    or None if the collection is not initialised or the image file is missing.

    Uses a stable per-type key so the placeholder is only loaded once per
    Blender session regardless of how many assets are drawn.
    """
    if _collection is None:
        return None
    key = _PLACEHOLDER_KEYS.get(asset_type)
    if key is None:
        return None
    path = _placeholder_path(asset_type)
    if path is None or not os.path.isfile(path):
        return None
    if key not in _collection:
        _collection.load(key, path, "IMAGE")
    return _collection[key].icon_id
