"""
Thin wrapper around bpy.utils.previews.ImagePreviewCollection.

The collection is created at addon register time and destroyed at unregister.
Callers use get_icon_id() to retrieve a Blender icon_id for a preview PNG;
the first call for a given asset loads it from disk and subsequent calls
return the cached value.
"""

from __future__ import annotations

import os
from typing import Optional

_collection = None  # bpy.utils.previews.ImagePreviewCollection


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
