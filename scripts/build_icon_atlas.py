#!/usr/bin/env python3
"""Build a PNG icon atlas from Blender's SVG icon source files.

This script:
1. Parses Blender's ``UI_icons.hh`` header to get the canonical icon order.
2. Downloads corresponding SVG files from the Blender GitHub mirror.
3. Rasterises each SVG to ICON_PX × ICON_PX white-on-transparent pixels.
4. Packs everything into a single PNG atlas and writes a companion JSON map
   (icon_name → grid index) so the addon can look up UV coordinates at
   runtime.

Build dependencies (install with ``uv pip install``):
    cairosvg, Pillow

Usage::

    python scripts/build_icon_atlas.py          # defaults for Blender 5.0
    python scripts/build_icon_atlas.py --tag v5.0.1

The outputs land in ``src/resources/img/``:
    icon_atlas.png   – RGBA atlas (32 px per icon cell)
    icon_map.json    – {"ICON_NAME": grid_index, …}
"""

from __future__ import annotations

import argparse
import io
import json
import math
import os
import re
import sys
import tempfile
import urllib.request
from pathlib import Path

try:
    import cairosvg
except ImportError:
    sys.exit("cairosvg is required: uv pip install cairosvg")

try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow is required: uv pip install Pillow")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ICON_PX = 32  # pixels per icon cell
GITHUB_RAW = "https://raw.githubusercontent.com/blender/blender"
DEF_ICON_RE = re.compile(r"DEF_ICON\w*\((\w+)\)")

OUT_DIR = Path(__file__).resolve().parent.parent / "src" / "resources" / "img"


# ---------------------------------------------------------------------------
# Step 1 – Parse UI_icons.hh
# ---------------------------------------------------------------------------


def fetch_icon_order(tag: str) -> list[str]:
    """Return the ordered list of icon names from *UI_icons.hh*."""
    url = f"{GITHUB_RAW}/{tag}/source/blender/editors/include/UI_icons.hh"
    print(f"  Fetching {url}")
    with urllib.request.urlopen(url, timeout=30) as resp:
        text = resp.read().decode()
    names: list[str] = []
    for m in DEF_ICON_RE.finditer(text):
        names.append(m.group(1))
    print(f"  Found {len(names)} icon definitions")
    return names


# ---------------------------------------------------------------------------
# Step 2 – Download & rasterise SVGs
# ---------------------------------------------------------------------------


def _svg_url(tag: str, name: str) -> str:
    return f"{GITHUB_RAW}/{tag}/release/datafiles/icons_svg/{name.lower()}.svg"


def rasterise_icon(tag: str, name: str) -> Image.Image | None:
    """Download and rasterise a single SVG icon, or return *None*."""
    url = _svg_url(tag, name)
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            svg_data = resp.read()
    except Exception:
        return None
    try:
        png_data = cairosvg.svg2png(
            bytestring=svg_data,
            output_width=ICON_PX,
            output_height=ICON_PX,
        )
        return Image.open(io.BytesIO(png_data)).convert("RGBA")
    except Exception as exc:
        print(f"    ⚠ rasterise failed for {name}: {exc}")
        return None


# ---------------------------------------------------------------------------
# Step 3 – Pack atlas
# ---------------------------------------------------------------------------


def build_atlas(
    icon_names: list[str],
    tag: str,
    columns: int = 32,
) -> tuple[Image.Image, dict[str, int]]:
    """Build the atlas image and icon-name → index mapping."""
    total = len(icon_names)
    rows = math.ceil(total / columns)
    atlas = Image.new("RGBA", (columns * ICON_PX, rows * ICON_PX), (0, 0, 0, 0))
    icon_map: dict[str, int] = {}

    for idx, name in enumerate(icon_names):
        col = idx % columns
        row = idx // columns
        img = rasterise_icon(tag, name)
        if img is not None:
            atlas.paste(img, (col * ICON_PX, row * ICON_PX))
        icon_map[name] = idx
        # Progress indicator
        if (idx + 1) % 50 == 0 or idx + 1 == total:
            print(f"    [{idx + 1}/{total}]")

    return atlas, icon_map


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Blender icon atlas")
    parser.add_argument(
        "--tag",
        default="main",
        help="Git ref to fetch icons from (default: main)",
    )
    parser.add_argument(
        "--columns",
        type=int,
        default=32,
        help="Number of columns in the atlas grid (default: 32)",
    )
    args = parser.parse_args()

    print("Step 1: Fetching icon order from UI_icons.hh …")
    icon_names = fetch_icon_order(args.tag)

    print("Step 2: Downloading & rasterising SVGs …")
    atlas, icon_map = build_atlas(icon_names, args.tag, columns=args.columns)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    atlas_path = OUT_DIR / "icon_atlas.png"
    map_path = OUT_DIR / "icon_map.json"

    atlas.save(atlas_path, "PNG", optimize=True)
    with open(map_path, "w") as f:
        json.dump(icon_map, f, separators=(",", ":"))

    atlas_kb = atlas_path.stat().st_size / 1024
    print(f"\nDone!  Atlas: {atlas_path}  ({atlas_kb:.0f} KB)")
    print(f"       Map:   {map_path}  ({len(icon_map)} icons)")


if __name__ == "__main__":
    main()
