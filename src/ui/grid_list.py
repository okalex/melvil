"""
Custom GPU-drawn scrollable grid/list component.

Replaces ``template_list`` for card-style UIs where custom selection
highlights, hover states, and scroll capture are needed.  Renders via
``gpu`` and ``blf`` inside a popup operator's ``draw()`` method.

See projects/005-grid-list.md for the full design spec.
"""

from __future__ import annotations

import math

import gpu
import blf
from gpu_extras.batch import batch_for_shader


# ---------------------------------------------------------------------------
# Layout constants (base values at ui_scale 1.0)
# ---------------------------------------------------------------------------

CARD_W = 120
CARD_H = 80
CARD_PAD = 8
CARD_GAP = 6
GRID_ORIGIN_X = 10
GRID_ORIGIN_Y = 10

COLOR_CARD_BG = (0.18, 0.18, 0.18, 1.0)
COLOR_CARD_BORDER = (0.35, 0.35, 0.35, 1.0)
COLOR_GRID_BG = (0.12, 0.12, 0.12, 0.90)
COLOR_TEXT_PRIMARY = (0.90, 0.90, 0.90, 1.0)
COLOR_TEXT_SECONDARY = (0.60, 0.60, 0.60, 1.0)

FONT_ID = 0
FONT_SIZE_PRIMARY = 12
FONT_SIZE_SECONDARY = 10

_TYPE_LABELS: dict[str, str] = {
    "MATERIAL": "Material",
    "MESH": "Mesh",
    "NODE_GROUP": "Node Group",
}

# Card rect cache — written by draw_grid, read by modal operator for hit testing.
# Each entry: (x, y, w, h, item_id)
_card_rects: list[tuple[float, float, float, float, str]] = []


# ---------------------------------------------------------------------------
# GPU helpers
# ---------------------------------------------------------------------------

def draw_rect(x: float, y: float, w: float, h: float, color: tuple) -> None:
    """Draw a filled rectangle at (*x*, *y*) with size *w* × *h*."""
    shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    verts = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
    indices = [(0, 1, 2), (0, 2, 3)]
    batch = batch_for_shader(shader, 'TRIS', {"pos": verts}, indices=indices)
    shader.bind()
    shader.uniform_float("color", color)
    batch.draw(shader)


def draw_rect_outline(
    x: float, y: float, w: float, h: float, color: tuple, thickness: int = 1,
) -> None:
    """Draw a rectangular outline at (*x*, *y*) with size *w* × *h*."""
    shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    t = thickness
    rects = [
        (x,         y,         w, t),   # bottom
        (x,         y + h - t, w, t),   # top
        (x,         y,         t, h),   # left
        (x + w - t, y,         t, h),   # right
    ]
    shader.bind()
    shader.uniform_float("color", color)
    for rx, ry, rw, rh in rects:
        verts = [(rx, ry), (rx + rw, ry), (rx + rw, ry + rh), (rx, ry + rh)]
        indices = [(0, 1, 2), (0, 2, 3)]
        batch = batch_for_shader(shader, 'TRIS', {"pos": verts}, indices=indices)
        batch.draw(shader)


# ---------------------------------------------------------------------------
# Main draw function
# ---------------------------------------------------------------------------

def draw_grid(
    region,
    items: list[dict],
    cols: int,
    rows_visible: int,
    scroll_offset: int = 0,
    selected_id: str = "",
    hovered_index: int = -1,
    offset_x: int = 0,
    offset_y: int = 0,
) -> int:
    """Draw a card grid into the current GPU context and return pixel height.

    Parameters
    ----------
    region:
        The ``bpy.types.Region`` the grid is drawn into.  Used for
        ``region.height`` to convert top-down row indices to bottom-up
        GPU coordinates.
    items:
        List of dicts with at least ``"id"``, ``"name"``, and ``"type"``
        keys.  Matches the asset DB row shape so the real browser can
        pass rows directly.
    cols:
        Number of columns.  ``1`` = single-column list mode.
    rows_visible:
        Maximum number of rows visible at once.
    scroll_offset:
        Current scroll position in rows (0-indexed).
    selected_id:
        UUID of the currently selected item (highlight), or ``""`` for none.
    hovered_index:
        Flat index (into the *visible* slice) of the hovered card, or
        ``-1`` for none.
    offset_x:
        Additional horizontal offset in pixels (e.g. to clear the toolbar).
    offset_y:
        Additional vertical offset from the top in pixels (e.g. to clear
        the header).

    Returns
    -------
    int
        Total pixel height consumed by the grid area (including padding).
    """
    global _card_rects
    _card_rects = []

    if not items:
        return 0

    start = scroll_offset * cols
    end = start + cols * rows_visible
    visible_items = list(enumerate(items))[start:end]

    if not visible_items:
        return 0

    # Scale all layout values by Blender's UI scale factor.
    try:
        import bpy
        scale = bpy.context.preferences.system.ui_scale
    except Exception:
        scale = 1.0

    cw = round(CARD_W * scale)
    ch = round(CARD_H * scale)
    cp = round(CARD_PAD * scale)
    cg = round(CARD_GAP * scale)
    ox = round(GRID_ORIGIN_X * scale)
    oy = round(GRID_ORIGIN_Y * scale)
    fsp = round(FONT_SIZE_PRIMARY * scale)
    fss = round(FONT_SIZE_SECONDARY * scale)

    region_h = region.height
    actual_rows = math.ceil(len(visible_items) / cols)

    # Background panel dimensions.
    bg_x = offset_x + ox
    bg_y = region_h - offset_y - oy - actual_rows * (ch + cg)
    bg_w = cols * (cw + cg) - cg + ox * 2
    bg_h = actual_rows * (ch + cg) - cg + oy * 2

    gpu.state.blend_set('ALPHA')

    # Draw containing background.
    draw_rect(bg_x - ox, bg_y - oy, bg_w, bg_h, COLOR_GRID_BG)

    for slot_idx, (real_idx, item) in enumerate(visible_items):
        col_idx = slot_idx % cols
        row_idx = slot_idx // cols

        x = offset_x + ox + col_idx * (cw + cg)
        y = region_h - offset_y - oy - (row_idx + 1) * (ch + cg) + cg

        _card_rects.append((x, y, cw, ch, item["id"]))

        bg = COLOR_CARD_BG
        draw_rect(x, y, cw, ch, bg)
        draw_rect_outline(x, y, cw, ch, COLOR_CARD_BORDER)

        # Primary text — asset name
        blf.size(FONT_ID, fsp)
        blf.color(FONT_ID, *COLOR_TEXT_PRIMARY)
        blf.position(FONT_ID, x + cp, y + ch - cp - fsp, 0)
        blf.draw(FONT_ID, item["name"])

        # Secondary text — type label
        type_label = _TYPE_LABELS.get(item["type"], item["type"])
        blf.size(FONT_ID, fss)
        blf.color(FONT_ID, *COLOR_TEXT_SECONDARY)
        blf.position(
            FONT_ID,
            x + cp,
            y + ch - cp - fsp - round(4 * scale) - fss,
            0,
        )
        blf.draw(FONT_ID, type_label)

    gpu.state.blend_set('NONE')

    return actual_rows * (ch + cg) + oy * 2

# TODO Phase 2: MelvilGridScrollProps PropertyGroup
# TODO Phase 2: MELVIL_OT_grid_scroll_nav operator
# TODO Phase 2: hit_test / is_over_grid helpers
# TODO Phase 3: Selection & hover highlight colors
# TODO Phase 4: Preview image rendering
# TODO Phase 5: Grid/list layout toggle
