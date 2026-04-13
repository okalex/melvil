"""Icon atlas provider for the GPU UI toolkit.

Loads a pre-built PNG icon atlas shipped with the addon.  The atlas is
generated at build time by ``scripts/build_icon_atlas.py`` from Blender's
open-source SVG icons.

At runtime the provider:

1. Reads ``icon_atlas.png`` from the addon's ``resources/img/`` directory
   and uploads it as a GPU texture.
2. Reads ``icon_map.json`` (icon name → grid index) from the same
   directory.
3. Computes UV sub-regions for individual icons using the grid index and
   the atlas dimensions.

The atlas grid uses 32 × 32 pixel cells (``ICON_PX``) packed left-to-right,
top-to-bottom with a fixed column count of 32.
"""

from __future__ import annotations

import json
import os
from typing import Any

from ._logger import _logger

# Pixel size of each icon cell in the atlas.
ICON_PX = 32

# Column count must match the build script (``--columns`` default).
_ATLAS_COLUMNS = 32


def _addon_resources_dir() -> str | None:
    """Return the absolute path to ``resources/img/`` inside the addon."""
    # This file lives at  <addon>/ui/gpu/icons.py
    # resources/img/ is at <addon>/resources/img/
    here = os.path.dirname(os.path.abspath(__file__))
    candidate = os.path.normpath(os.path.join(here, os.pardir, os.pardir, "resources", "img"))
    if os.path.isdir(candidate):
        return candidate
    return None


class IconProvider:
    """Lazy-loaded provider of built-in icon atlas textures and UV rects.

    All public methods are safe to call even when the atlas is unavailable
    (test environments, missing resources, etc.) — they return ``None``
    gracefully.
    """

    def __init__(self) -> None:
        self._atlas: Any | None = None  # gpu.types.GPUTexture once loaded
        self._atlas_size: tuple[int, int] = (0, 0)
        self._columns: int = 0
        self._rows: int = 0
        self._icon_map: dict[str, int] = {}
        self._loaded: bool = False

    # -- Public API ----------------------------------------------------------

    @property
    def atlas(self) -> Any | None:
        """Return the GPU texture for the icon atlas, or ``None``."""
        if not self._loaded:
            self._load()
        return self._atlas

    def get_icon_uv(self, icon_name: str) -> tuple[float, float, float, float] | None:
        """Return ``(u0, v0, u1, v1)`` UV rect for *icon_name*, or ``None``.

        UV coordinates are in OpenGL convention (origin at bottom-left).
        """
        if not self._loaded:
            self._load()
        idx = self._icon_map.get(icon_name)
        if idx is None or self._columns == 0:
            return None
        col = idx % self._columns
        row = idx // self._columns
        if row >= self._rows:
            return None

        w, h = self._atlas_size
        u0 = (col * ICON_PX) / w
        u1 = ((col + 1) * ICON_PX) / w
        # The PNG is top-to-bottom; GPUTexture treats row 0 as the bottom.
        # After the vertical flip applied during loading, grid row 0

        # (top of image) maps to high v values.
        v1 = 1.0 - (row * ICON_PX) / h
        v0 = 1.0 - ((row + 1) * ICON_PX) / h
        return (u0, v0, u1, v1)

    # -- Loading internals ---------------------------------------------------

    def _load(self) -> None:
        """Attempt to load the atlas and icon map.  Called once."""
        self._loaded = True
        self._load_icon_map()
        self._load_atlas()

    def _load_icon_map(self) -> None:
        """Load icon-name → grid-index mapping from the shipped JSON."""
        res_dir = _addon_resources_dir()
        if res_dir is None:
            return
        map_path = os.path.join(res_dir, "icon_map.json")
        if not os.path.isfile(map_path):
            _logger.log("icon atlas: icon_map.json not found")
            return
        try:
            with open(map_path) as f:
                self._icon_map = json.load(f)
        except Exception as exc:  # noqa: BLE001
            _logger.log(f"icon atlas: failed to read icon_map.json: {exc}")

    def _load_atlas(self) -> None:
        """Load the PNG atlas and upload as a GPU texture."""
        res_dir = _addon_resources_dir()
        if res_dir is None:
            return
        atlas_path = os.path.join(res_dir, "icon_atlas.png")
        if not os.path.isfile(atlas_path):
            _logger.log("icon atlas: icon_atlas.png not found")
            return

        try:
            # Use Blender's bpy.data.images to load the PNG, then extract
            # raw pixel data and create a GPUTexture.
            import bpy
            import gpu

            img = bpy.data.images.load(atlas_path, check_existing=True)
            w, h = img.size
            # pixels is a flat float array [r,g,b,a, r,g,b,a, …]
            # in bottom-to-top row order (OpenGL convention) — no flip
            # needed.
            pixel_floats = list(img.pixels)
            buf = gpu.types.Buffer("FLOAT", len(pixel_floats), pixel_floats)
            self._atlas = gpu.types.GPUTexture((w, h), format="RGBA32F", data=buf)
            self._atlas_size = (w, h)
            self._columns = _ATLAS_COLUMNS
            self._rows = h // ICON_PX
            _logger.log(
                f"icon atlas: loaded {w}×{h} ({self._columns}×{self._rows} grid,"
                f" {len(self._icon_map)} mapped icons)",
            )
            # Clean up the temp image from bpy.data
            bpy.data.images.remove(img)
        except Exception as exc:  # noqa: BLE001
            _logger.log(f"icon atlas: failed to create GPU texture: {exc}")
