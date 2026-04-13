"""
Custom GPU-drawn scrollable grid/list component.

Replaces ``template_list`` for card-style UIs where custom selection
highlights, hover states, and scroll capture are needed.  Renders via
``gpu`` and ``blf`` inside a popup operator's ``draw()`` method.

See projects/005-grid-list.md for the full design spec.
"""

from __future__ import annotations

import math

import bpy
import gpu
import blf
from bpy.props import EnumProperty, IntProperty, StringProperty

from .gpu import (
    ThemeColors,
    draw_rect,
    draw_rect_outline,
    draw_texture,
    get_theme,
    reset_theme,
)


# ---------------------------------------------------------------------------
# Layout constants (base values at ui_scale 1.0)
# ---------------------------------------------------------------------------

CARD_W = 120
CARD_H = 140
CARD_PAD = 8
CARD_GAP = 6
GRID_ORIGIN_X = 10
GRID_ORIGIN_Y = 10
PREVIEW_H = 80
LIST_CARD_H = 40
BUTTON_H = 20
BUTTON_PAD = 2


# Backward-compatible module-level constants — used by tests and any code
# that references ``grid_list.COLOR_*`` directly.  These match the fallback
# theme so existing tests continue passing.
_fb = ThemeColors.fallback()
COLOR_CARD_BG = _fb.panel_bg
COLOR_CARD_HOVER = _fb.widget_bg_hover
COLOR_CARD_SELECTED = _fb.selection_bg
COLOR_CARD_BORDER = _fb.border
COLOR_GRID_BG = (0.12, 0.12, 0.12, 0.90)
COLOR_PREVIEW_BG = _fb.input_bg
COLOR_TEXT_PRIMARY = _fb.text_primary
COLOR_TEXT_SECONDARY = _fb.text_secondary
COLOR_BUTTON_BG = _fb.button_bg
COLOR_BUTTON_HOVER = _fb.button_bg_hover
COLOR_BUTTON_TEXT = _fb.button_text
del _fb

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

# Button rect cache — same shape as _card_rects.
_button_rects: list[tuple[float, float, float, float, str]] = []


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
    get_preview_texture=None,
    hovered_button_index: int = -1,
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
    get_preview_texture:
        Optional callback ``(item_dict) -> gpu_texture | None``.  Called
        once per visible card.  When it returns a texture, the preview
        area shows the texture; otherwise a placeholder rect is drawn.
    hovered_button_index:
        Flat index (into the *visible* slice) of the hovered button, or
        ``-1`` for none.

    Returns
    -------
    int
        Total pixel height consumed by the grid area (including padding).
    """
    global _card_rects, _button_rects
    _card_rects = []
    _button_rects = []

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

    is_list = cols == 1

    cw_base = round(CARD_W * scale)
    ch = round((LIST_CARD_H if is_list else CARD_H) * scale)
    cp = round(CARD_PAD * scale)
    cg = round(CARD_GAP * scale)
    ox = round(GRID_ORIGIN_X * scale)
    oy = round(GRID_ORIGIN_Y * scale)
    fsp = round(FONT_SIZE_PRIMARY * scale)
    fss = round(FONT_SIZE_SECONDARY * scale)
    ph = round(PREVIEW_H * scale)
    bh = round(BUTTON_H * scale)
    bp = round(BUTTON_PAD * scale)

    # In list mode the card spans the full grid-panel width.
    grid_cols_for_width = cols if not is_list else 3
    cw = grid_cols_for_width * (cw_base + cg) - cg if is_list else cw_base

    region_h = region.height
    actual_rows = math.ceil(len(visible_items) / cols)

    # Background panel dimensions.
    bg_x = offset_x + ox
    bg_y = region_h - offset_y - oy - actual_rows * (ch + cg)
    bg_w = cw + ox * 2 if is_list else cols * (cw_base + cg) - cg + ox * 2
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

        if item["id"] == selected_id:
            bg = COLOR_CARD_SELECTED
        elif slot_idx == hovered_index:
            bg = COLOR_CARD_HOVER
        else:
            bg = COLOR_CARD_BG
        draw_rect(x, y, cw, ch, bg)
        draw_rect_outline(x, y, cw, ch, COLOR_CARD_BORDER)

        gap = round(4 * scale)

        if is_list:
            # List mode — compact single row: [preview] name  type
            thumb_size = ch - 2 * cp
            preview_x = x + cp
            preview_y = y + cp

            texture = None
            if get_preview_texture is not None:
                texture = get_preview_texture(item)
            if texture is not None:
                draw_texture(texture, preview_x, preview_y, thumb_size, thumb_size)
            else:
                draw_rect(preview_x, preview_y, thumb_size, thumb_size, COLOR_PREVIEW_BG)

            text_x = preview_x + thumb_size + gap
            text_y = y + (ch - fsp) // 2

            blf.size(FONT_ID, fsp)
            blf.color(FONT_ID, *COLOR_TEXT_PRIMARY)
            blf.position(FONT_ID, text_x, text_y, 0)
            blf.draw(FONT_ID, item["name"])

            type_label = _TYPE_LABELS.get(item["type"], item["type"])
            blf.size(FONT_ID, fss)
            blf.color(FONT_ID, *COLOR_TEXT_SECONDARY)
            blf.position(FONT_ID, cw + x - cp - round(60 * scale), text_y, 0)
            blf.draw(FONT_ID, type_label)
        else:
            # Grid mode — stacked: preview on top, name + type below.
            pw = cw - 2 * cp
            preview_x = x + cp
            preview_y = y + ch - cp - ph

            texture = None
            if get_preview_texture is not None:
                texture = get_preview_texture(item)
            if texture is not None:
                draw_texture(texture, preview_x, preview_y, pw, ph)
            else:
                draw_rect(preview_x, preview_y, pw, ph, COLOR_PREVIEW_BG)

            blf.size(FONT_ID, fsp)
            blf.color(FONT_ID, *COLOR_TEXT_PRIMARY)
            blf.position(FONT_ID, x + cp, preview_y - gap - fsp, 0)
            blf.draw(FONT_ID, item["name"])

            type_label = _TYPE_LABELS.get(item["type"], item["type"])
            blf.size(FONT_ID, fss)
            blf.color(FONT_ID, *COLOR_TEXT_SECONDARY)
            blf.position(
                FONT_ID,
                x + cp,
                preview_y - gap - fsp - gap - fss,
                0,
            )
            blf.draw(FONT_ID, type_label)

        # Load button — bottom of card in both modes.
        btn_w = cw - 2 * cp
        btn_x = x + cp
        btn_y = y + bp
        btn_bg = COLOR_BUTTON_HOVER if slot_idx == hovered_button_index else COLOR_BUTTON_BG
        draw_rect(btn_x, btn_y, btn_w, bh, btn_bg)
        _button_rects.append((btn_x, btn_y, btn_w, bh, item["id"]))

        btn_label = "Load"
        blf.size(FONT_ID, fss)
        blf.color(FONT_ID, *COLOR_BUTTON_TEXT)
        blf.position(FONT_ID, btn_x + (btn_w - len(btn_label) * fss * 0.6) / 2, btn_y + bp + 1, 0)
        blf.draw(FONT_ID, btn_label)

    gpu.state.blend_set('NONE')

    return actual_rows * (ch + cg) + oy * 2


# ---------------------------------------------------------------------------
# Scroll helpers
# ---------------------------------------------------------------------------

def compute_max_offset(item_count: int, cols: int, rows_visible: int) -> int:
    """Return the maximum valid ``scroll_offset`` for the given item count.

    The result is clamped to a minimum of 0 so callers never need to
    guard against negative values.
    """
    if item_count <= 0 or cols <= 0 or rows_visible <= 0:
        return 0
    total_rows = math.ceil(item_count / cols)
    return max(0, total_rows - rows_visible)


# ---------------------------------------------------------------------------
# Hit testing
# ---------------------------------------------------------------------------

def hit_test(mx: float, my: float) -> tuple[str, int] | None:
    """Return ``(item_id, slot_index)`` for the card under (*mx*, *my*).

    Coordinates are **region-local** pixels (same space as the card rects
    written by :func:`draw_grid`).  Returns ``None`` if no card is hit.
    """
    for slot_idx, (x, y, w, h, item_id) in enumerate(_card_rects):
        if x <= mx <= x + w and y <= my <= y + h:
            return (item_id, slot_idx)
    return None


def is_over_grid(mx: float, my: float) -> bool:
    """Return ``True`` if region-local (*mx*, *my*) is within the grid bbox."""
    if not _card_rects:
        return False
    gx = min(r[0] for r in _card_rects)
    gy = min(r[1] for r in _card_rects)
    gx2 = max(r[0] + r[2] for r in _card_rects)
    gy2 = max(r[1] + r[3] for r in _card_rects)
    return gx <= mx <= gx2 and gy <= my <= gy2


def button_hit_test(mx: float, my: float) -> tuple[str, int] | None:
    """Return ``(item_id, slot_index)`` for the button under (*mx*, *my*).

    Same contract as :func:`hit_test` but checks ``_button_rects``.
    """
    for slot_idx, (x, y, w, h, item_id) in enumerate(_button_rects):
        if x <= mx <= x + w and y <= my <= y + h:
            return (item_id, slot_idx)
    return None


# ---------------------------------------------------------------------------
# PropertyGroup — transient scroll / selection state
# ---------------------------------------------------------------------------

class MelvilGridScrollProps(bpy.types.PropertyGroup):
    """Scroll, selection, and hover state for the GPU card grid."""

    scroll_offset: IntProperty(
        name="Scroll Offset",
        description="Current scroll position in rows",
        default=0,
        min=0,
        options={"HIDDEN", "SKIP_SAVE"},
    )
    selected_id: StringProperty(
        name="Selected ID",
        description="UUID of the currently selected item",
        default="",
        options={"HIDDEN", "SKIP_SAVE"},
    )
    hovered_index: IntProperty(
        name="Hovered Index",
        description="Flat index of the hovered card in the visible slice, or -1",
        default=-1,
        options={"HIDDEN", "SKIP_SAVE"},
    )
    hovered_button_index: IntProperty(
        name="Hovered Button Index",
        description="Flat index of the hovered button in the visible slice, or -1",
        default=-1,
        options={"HIDDEN", "SKIP_SAVE"},
    )
    display_mode: EnumProperty(
        name="Display Mode",
        description="Grid or list layout for the asset card view",
        items=[
            ("GRID", "Grid", "Multi-column card grid", 'VIEW3D', 0),
            ("LIST", "List", "Single-column list", 'COLLAPSEMENU', 1),
        ],
        default="GRID",
        options={"HIDDEN", "SKIP_SAVE"},
    )


# ---------------------------------------------------------------------------
# Scroll nav operator
# ---------------------------------------------------------------------------

class MELVIL_OT_grid_scroll_nav(bpy.types.Operator):
    """Scroll the grid up or down by one row"""

    bl_idname = "melvil.grid_scroll_nav"
    bl_label = "Scroll Grid"
    bl_options = {"REGISTER", "INTERNAL"}

    direction: IntProperty(
        name="Direction",
        description="+1 to scroll down, -1 to scroll up",
        default=0,
    )

    # These are set externally by the caller before execute().
    item_count: IntProperty(default=0)
    cols: IntProperty(default=3)
    rows_visible: IntProperty(default=4)

    def execute(self, context):
        props = context.window_manager.melvil_grid_scroll
        max_off = compute_max_offset(self.item_count, self.cols, self.rows_visible)
        props.scroll_offset = max(0, min(props.scroll_offset + self.direction, max_off))
        if context.area is not None:
            context.area.tag_redraw()
        return {"FINISHED"}
