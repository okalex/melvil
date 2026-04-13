"""
GPU UI toolkit — foundational drawing primitives, theme colors, and DPI helpers.

This module provides the rendering foundation for the GPU-drawn browser UI.
All drawing functions use Blender's ``gpu`` and ``blf`` modules to render
directly into a ``SpaceView3D`` ``POST_PIXEL`` draw handler.

See projects/006-gpu-ui.md for the full design spec.
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable

import bpy
import gpu
import blf
from gpu_extras.batch import batch_for_shader

if TYPE_CHECKING:
    pass


class GpuUiLogger:
    """Conditional logger controlled by the ``GPU_UI_LOG`` env var."""

    def __init__(self) -> None:
        val = os.environ.get("GPU_UI_LOG", "0")
        self._enabled = val not in ("", "0")

    def log(self, msg: str) -> None:
        if self._enabled:
            print(f"[gpu_ui] {msg}")


_logger = GpuUiLogger()


# ---------------------------------------------------------------------------
# Shader cache
# ---------------------------------------------------------------------------

_uniform_shader = None
_image_shader = None


def _get_uniform_shader():
    """Return a cached ``UNIFORM_COLOR`` shader."""
    global _uniform_shader
    if _uniform_shader is None:
        _uniform_shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    return _uniform_shader


def _get_image_shader():
    """Return a cached ``IMAGE`` shader."""
    global _image_shader
    if _image_shader is None:
        _image_shader = gpu.shader.from_builtin('IMAGE')
    return _image_shader


# ---------------------------------------------------------------------------
# Layout constants (base values at ui_scale 1.0)
# ---------------------------------------------------------------------------

WIDGET_HEIGHT = 20
WIDGET_GAP = 4
WIDGET_GAP_ALIGNED = 1
WIDGET_PAD_X = 6
BOX_PAD = 8
SEPARATOR_HEIGHT = 8

FONT_ID = 0
FONT_SIZE_PRIMARY = 11
FONT_SIZE_SECONDARY = 10
ICON_SIZE = 16

SCROLLBAR_WIDTH = 8
SCROLLBAR_MIN_HEIGHT = 20


# ---------------------------------------------------------------------------
# DPI helpers
# ---------------------------------------------------------------------------

def get_ui_scale() -> float:
    """Return Blender's current UI scale factor.

    Returns 1.0 when ``bpy.context`` is unavailable (test environments).
    """
    try:
        return bpy.context.preferences.system.ui_scale
    except Exception:
        return 1.0


def scaled(px: float, ui_scale: float) -> float:
    """Scale a pixel value by the given UI scale factor."""
    return px * ui_scale


# ---------------------------------------------------------------------------
# Theme colors
# ---------------------------------------------------------------------------

def _color_with_alpha(color, alpha: float) -> tuple[float, float, float, float]:
    """Return *color* with its alpha channel replaced by *alpha*."""
    return (color[0], color[1], color[2], alpha)


@dataclass(frozen=True)
class ThemeColors:
    """Snapshot of theme colors needed by the GPU UI toolkit.

    Use :meth:`from_blender` to read the current theme, or :meth:`fallback`
    for test environments where ``bpy.context`` is unavailable.
    """

    # Panel
    panel_bg: tuple[float, float, float, float]
    panel_header_bg: tuple[float, float, float, float]

    # Text
    text_primary: tuple[float, float, float, float]
    text_secondary: tuple[float, float, float, float]
    text_disabled: tuple[float, float, float, float]

    # Widget backgrounds
    widget_bg: tuple[float, float, float, float]
    widget_bg_hover: tuple[float, float, float, float]
    widget_bg_active: tuple[float, float, float, float]

    # Input fields
    input_bg: tuple[float, float, float, float]
    input_border: tuple[float, float, float, float]
    input_text: tuple[float, float, float, float]

    # Buttons
    button_bg: tuple[float, float, float, float]
    button_bg_hover: tuple[float, float, float, float]
    button_text: tuple[float, float, float, float]

    # Selection & highlights
    selection_bg: tuple[float, float, float, float]
    selection_text: tuple[float, float, float, float]

    # Alerts & accents
    alert: tuple[float, float, float, float]

    # Borders
    border: tuple[float, float, float, float]
    border_intense: tuple[float, float, float, float]

    # Scrollbar
    scrollbar_bg: tuple[float, float, float, float]
    scrollbar_handle: tuple[float, float, float, float]

    @classmethod
    def from_blender(cls) -> ThemeColors:
        """Read colors from the active Blender theme.

        Widget color attributes (``inner``, ``inner_sel``, ``text``,
        ``outline``, etc.) on ``ThemeWidgetColors`` are float RGBA arrays
        in the ``[0, 1]`` range in Blender's Python API, so no byte-to-float
        conversion is needed.
        """
        ui = bpy.context.preferences.themes[0].user_interface

        def _rgba(color) -> tuple[float, float, float, float]:
            r, g, b = float(color[0]), float(color[1]), float(color[2])
            try:
                a = float(color[3])
            except (IndexError, KeyError):
                a = 1.0
            return (r, g, b, a)

        text_primary = _rgba(ui.wcol_regular.text)
        menu_back = _rgba(ui.wcol_menu_back.inner)
        # Force full opacity — native popups render opaque regardless of
        # the theme alpha channel.
        panel_bg = (menu_back[0], menu_back[1], menu_back[2], 1.0)
        box_inner = _rgba(ui.wcol_box.inner)
        panel_header_bg = (box_inner[0], box_inner[1], box_inner[2],
                           min(1.0, box_inner[3] + 0.1))

        return cls(
            panel_bg=panel_bg,
            panel_header_bg=panel_header_bg,
            text_primary=text_primary,
            text_secondary=_color_with_alpha(text_primary, 0.6),
            text_disabled=_color_with_alpha(text_primary, 0.3),
            widget_bg=_rgba(ui.wcol_tool.inner),
            widget_bg_hover=_rgba(ui.wcol_tool.inner_sel),
            widget_bg_active=_rgba(ui.wcol_option.inner_sel),
            input_bg=_rgba(ui.wcol_text.inner),
            input_border=_rgba(ui.wcol_text.outline),
            input_text=_rgba(ui.wcol_text.text),
            button_bg=_rgba(ui.wcol_tool.inner),
            button_bg_hover=_rgba(ui.wcol_tool.inner_sel),
            button_text=_rgba(ui.wcol_tool.text),
            selection_bg=_rgba(ui.wcol_list_item.inner_sel),
            selection_text=_rgba(ui.wcol_list_item.text_sel),
            alert=(1.0, 0.2, 0.2, 1.0),
            border=_rgba(ui.wcol_regular.outline),
            border_intense=(min(1.0, panel_bg[0] + 0.25),
                            min(1.0, panel_bg[1] + 0.25),
                            min(1.0, panel_bg[2] + 0.25),
                            1.0),
            scrollbar_bg=_rgba(ui.wcol_scroll.inner),
            scrollbar_handle=_rgba(ui.wcol_scroll.item),
        )

    @classmethod
    def fallback(cls) -> ThemeColors:
        """Return sensible dark-theme defaults for test environments."""
        return cls(
            panel_bg=(0.18, 0.18, 0.18, 1.0),
            panel_header_bg=(0.22, 0.22, 0.22, 1.0),
            text_primary=(0.90, 0.90, 0.90, 1.0),
            text_secondary=(0.90, 0.90, 0.90, 0.6),
            text_disabled=(0.90, 0.90, 0.90, 0.3),
            widget_bg=(0.25, 0.25, 0.25, 1.0),
            widget_bg_hover=(0.35, 0.35, 0.35, 1.0),
            widget_bg_active=(0.20, 0.45, 0.75, 1.0),
            input_bg=(0.15, 0.15, 0.15, 1.0),
            input_border=(0.40, 0.40, 0.40, 1.0),
            input_text=(0.90, 0.90, 0.90, 1.0),
            button_bg=(0.25, 0.25, 0.25, 1.0),
            button_bg_hover=(0.35, 0.35, 0.35, 1.0),
            button_text=(0.85, 0.85, 0.85, 1.0),
            selection_bg=(0.20, 0.45, 0.75, 1.0),
            selection_text=(1.0, 1.0, 1.0, 1.0),
            alert=(1.0, 0.2, 0.2, 1.0),
            border=(0.35, 0.35, 0.35, 1.0),
            border_intense=(0.50, 0.50, 0.50, 1.0),
            scrollbar_bg=(0.12, 0.12, 0.12, 0.9),
            scrollbar_handle=(0.40, 0.40, 0.40, 1.0),
        )


# ---------------------------------------------------------------------------
# Shared theme instance (lazy-loaded)
# ---------------------------------------------------------------------------

_theme: ThemeColors | None = None


def get_theme() -> ThemeColors:
    """Return the cached :class:`ThemeColors` for the active Blender theme.

    The theme is read lazily on first access so that ``bpy.context`` is
    available (it isn't at module import time).  Falls back to
    :meth:`ThemeColors.fallback` when running outside Blender.
    """
    global _theme
    if _theme is None:
        try:
            _theme = ThemeColors.from_blender()
        except Exception as exc:
            _logger.log(f"from_blender() failed: {exc}")
            _theme = ThemeColors.fallback()
    return _theme


def reset_theme() -> None:
    """Force a theme re-read on next :func:`get_theme` call.

    Call this after the user changes Blender's theme so that all GPU UI
    components pick up the new colors.
    """
    global _theme
    _theme = None


# ---------------------------------------------------------------------------
# Drawing primitives
# ---------------------------------------------------------------------------

def draw_rect(x: float, y: float, w: float, h: float, color: tuple) -> None:
    """Draw a filled rectangle at (*x*, *y*) with size *w* × *h*."""
    shader = _get_uniform_shader()
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
    shader = _get_uniform_shader()
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


def draw_rect_rounded(
    x: float, y: float, w: float, h: float, radius: float, color: tuple,
    *,
    segments: int = 6,
) -> None:
    """Draw a filled rounded rectangle.

    Each corner is drawn as a triangle-fan arc with *segments* triangles,
    matching Blender's native widget shape.  When *radius* is 0, this
    falls back to a plain rectangle.
    """
    if radius <= 0:
        draw_rect(x, y, w, h, color)
        return

    # Clamp radius so it doesn't exceed half the shortest side.
    r = min(radius, w / 2, h / 2)
    seg = max(1, segments)

    # Corner centres (bottom-left, bottom-right, top-right, top-left).
    corners = [
        (x + r,     y + r),      # BL — angles π to 3π/2
        (x + w - r, y + r),      # BR — angles 3π/2 to 2π
        (x + w - r, y + h - r),  # TR — angles 0 to π/2
        (x + r,     y + h - r),  # TL — angles π/2 to π
    ]
    start_angles = [math.pi, 3 * math.pi / 2, 0.0, math.pi / 2]

    verts: list[tuple[float, float]] = []
    indices: list[tuple[int, int, int]] = []

    # Centre point for the whole shape (used for triangle fans).
    cx, cy = x + w / 2, y + h / 2
    center_idx = 0
    verts.append((cx, cy))

    # Build perimeter vertices going around the rectangle.
    for ci in range(4):
        ccx, ccy = corners[ci]
        sa = start_angles[ci]
        for s in range(seg + 1):
            angle = sa + (math.pi / 2) * s / seg
            vx = ccx + r * math.cos(angle)
            vy = ccy + r * math.sin(angle)
            verts.append((vx, vy))

    # Fan triangles from centre to each consecutive perimeter pair.
    perimeter_count = len(verts) - 1  # exclude centre
    for i in range(perimeter_count):
        i0 = 1 + i
        i1 = 1 + (i + 1) % perimeter_count
        indices.append((center_idx, i0, i1))

    shader = _get_uniform_shader()
    batch = batch_for_shader(shader, 'TRIS', {"pos": verts}, indices=indices)
    shader.bind()
    shader.uniform_float("color", color)
    batch.draw(shader)


def draw_texture(texture, x: float, y: float, w: float, h: float) -> None:
    """Draw a GPU texture at (*x*, *y*) with size *w* × *h*."""
    shader = _get_image_shader()
    verts = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
    uvs = [(0, 0), (1, 0), (1, 1), (0, 1)]
    indices = [(0, 1, 2), (0, 2, 3)]
    batch = batch_for_shader(
        shader, 'TRIS',
        {"pos": verts, "texCoord": uvs},
        indices=indices,
    )
    shader.bind()
    shader.uniform_sampler("image", texture)
    batch.draw(shader)


# ---------------------------------------------------------------------------
# Text drawing
# ---------------------------------------------------------------------------

def draw_text(
    text: str,
    x: float,
    y: float,
    size: float,
    color: tuple[float, float, float, float],
) -> float:
    """Draw *text* at (*x*, *y*) and return its measured pixel width.

    Uses ``blf`` for rendering.  *size* is the font pixel size (pre-scaled
    by the caller if DPI-awareness is desired).
    """
    blf.size(FONT_ID, size)
    blf.color(FONT_ID, *color)
    blf.position(FONT_ID, x, y, 0)
    blf.draw(FONT_ID, text)
    w, _ = blf.dimensions(FONT_ID, text)
    return w


def measure_text(text: str, size: float) -> tuple[float, float]:
    """Return ``(width, height)`` of *text* at *size* without drawing it."""
    blf.size(FONT_ID, size)
    return blf.dimensions(FONT_ID, text)


# ---------------------------------------------------------------------------
# Hit testing
# ---------------------------------------------------------------------------


@dataclass
class HitResult:
    """Describes the interactive widget found by :meth:`GpuPanel.hit_test`."""

    widget_type: str  # "operator", "prop", "list_row", "button", "text_field"
    id: str
    kwargs: dict[str, Any]
    rect: tuple[float, float, float, float]  # (x, y, w, h)


# ---------------------------------------------------------------------------
# Layout-tree leaf nodes
# ---------------------------------------------------------------------------


@dataclass
class _Separator:
    """Vertical (or horizontal) spacer inserted by :meth:`GpuLayout.separator`."""

    factor: float = 1.0


# ---------------------------------------------------------------------------
# GpuLayout
# ---------------------------------------------------------------------------


class GpuLayout:
    """Immediate-mode layout container mirroring ``bpy.types.UILayout``.

    Callers build a widget tree each frame by calling container methods
    (``row``, ``column``, ``split``, ``box``, ``separator``).  The tree is
    then walked in a **measure** pass (bottom-up heights), a **position**
    pass (top-down coordinate assignment), and a **draw** pass.
    """

    def __init__(
        self,
        panel: GpuPanel,
        *,
        direction: str = "COLUMN",
        align: bool = False,
        is_box: bool = False,
        split_factor: float = 0.5,
    ) -> None:
        self._panel = panel
        self._direction = direction
        self._align = align
        self._is_box = is_box
        self._split_factor = split_factor
        self._children: list[GpuLayout | _Separator] = []
        self._rect: tuple[float, float, float, float] | None = None

        # Public properties (matching UILayout).
        self.enabled: bool = True
        self.alert: bool = False
        self.alignment: str = "EXPAND"
        self.scale_x: float = 1.0
        self.scale_y: float = 1.0

    # -- Container methods ---------------------------------------------------

    def row(self, align: bool = False) -> GpuLayout:
        child = GpuLayout(self._panel, direction="ROW", align=align)
        self._children.append(child)
        return child

    def column(self, align: bool = False) -> GpuLayout:
        child = GpuLayout(self._panel, direction="COLUMN", align=align)
        self._children.append(child)
        return child

    def split(self, *, factor: float = 0.5, align: bool = False) -> GpuLayout:
        child = GpuLayout(
            self._panel, direction="SPLIT", align=align, split_factor=factor,
        )
        self._children.append(child)
        return child

    def box(self) -> GpuLayout:
        child = GpuLayout(self._panel, direction="COLUMN", is_box=True)
        self._children.append(child)
        return child

    def separator(self, *, factor: float = 1.0) -> None:
        self._children.append(_Separator(factor=factor))

    def grid_flow(
        self,
        row_major: bool = True,
        columns: int = 0,
        even_columns: bool = True,
        even_rows: bool = True,
        align: bool = False,
    ) -> GpuLayout:
        child = GpuLayout(self._panel, direction="GRID_FLOW", align=align)
        child._grid_columns = columns
        child._grid_row_major = row_major
        child._grid_even_columns = even_columns
        child._grid_even_rows = even_rows
        self._children.append(child)
        return child

    # -- Measure pass (bottom-up) -------------------------------------------

    def _child_height(self, child: GpuLayout | _Separator, s: float) -> float:
        """Return the measured height of a single child."""
        if isinstance(child, _Separator):
            return scaled(SEPARATOR_HEIGHT * child.factor, s)
        return child._measure_height(s) * child.scale_y

    @staticmethod
    def _gap_before(
        children: list[GpuLayout | _Separator], index: int,
    ) -> bool:
        """Return ``True`` if a gap should be inserted before *index*.

        Gaps appear between consecutive non-separator children.  Separators
        provide their own spacing so no extra gap is added adjacent to them.
        """
        if index == 0:
            return False
        return (
            not isinstance(children[index], _Separator)
            and not isinstance(children[index - 1], _Separator)
        )

    def _measure_height(self, s: float) -> float:
        """Compute the natural height of this node (children sum/max)."""
        if not self._children:
            return 0.0

        gap = scaled(
            WIDGET_GAP_ALIGNED if self._align else WIDGET_GAP, s,
        )

        if self._direction in ("COLUMN", "GRID_FLOW"):
            total = 0.0
            if self._direction == "GRID_FLOW":
                cols = max(1, getattr(self, "_grid_columns", 1) or 1)
                rows_of_items = self._grid_flow_rows(cols)
                for row_items in rows_of_items:
                    row_h = max(
                        (self._child_height(c, s) for c in row_items),
                        default=0.0,
                    )
                    if total > 0:
                        total += gap
                    total += row_h
            else:
                for i, child in enumerate(self._children):
                    if self._gap_before(self._children, i):
                        total += gap
                    total += self._child_height(child, s)
        else:
            # ROW / SPLIT: height = max of children.
            total = max(
                (self._child_height(c, s) for c in self._children),
                default=0.0,
            )

        if self._is_box:
            total += scaled(BOX_PAD * 2, s)

        return total

    # -- Position pass (top-down) -------------------------------------------

    def _position(
        self, x: float, y: float, w: float, h: float, s: float,
    ) -> None:
        """Assign ``(x, y, w, h)`` to self and all descendants."""
        self._rect = (x, y, w, h)

        inner_x, inner_y, inner_w, inner_h = x, y, w, h
        if self._is_box:
            pad = scaled(BOX_PAD, s)
            inner_x += pad
            inner_y += pad
            inner_w -= pad * 2
            inner_h -= pad * 2

        if self._direction == "COLUMN":
            self._position_column(inner_x, inner_y, inner_w, inner_h, s)
        elif self._direction == "ROW":
            self._position_row(inner_x, inner_y, inner_w, inner_h, s)
        elif self._direction == "SPLIT":
            self._position_split(inner_x, inner_y, inner_w, inner_h, s)
        elif self._direction == "GRID_FLOW":
            self._position_grid_flow(inner_x, inner_y, inner_w, inner_h, s)

    def _position_column(
        self, x: float, y: float, w: float, h: float, s: float,
    ) -> None:
        gap = scaled(
            WIDGET_GAP_ALIGNED if self._align else WIDGET_GAP, s,
        )
        cursor_y = y + h  # start at top

        for i, child in enumerate(self._children):
            child_h = self._child_height(child, s)
            if self._gap_before(self._children, i):
                cursor_y -= gap
            cursor_y -= child_h

            if isinstance(child, GpuLayout):
                child._position(x, cursor_y, w, child_h, s)

    def _position_row(
        self, x: float, y: float, w: float, h: float, s: float,
    ) -> None:
        if not self._children:
            return

        gap = scaled(
            WIDGET_GAP_ALIGNED if self._align else WIDGET_GAP, s,
        )

        # Tally separator widths and gaps between non-sep children.
        sep_w = 0.0
        n_gaps = 0
        nonsep: list[GpuLayout] = []
        for i, child in enumerate(self._children):
            if isinstance(child, _Separator):
                sep_w += scaled(SEPARATOR_HEIGHT * child.factor, s)
            else:
                nonsep.append(child)
                if self._gap_before(self._children, i):
                    n_gaps += 1

        available = w - sep_w - n_gaps * gap
        total_sx = sum(c.scale_x for c in nonsep) if nonsep else 1.0

        cursor_x = x
        for i, child in enumerate(self._children):
            if self._gap_before(self._children, i):
                cursor_x += gap

            if isinstance(child, _Separator):
                cursor_x += scaled(SEPARATOR_HEIGHT * child.factor, s)
            elif isinstance(child, GpuLayout):
                cw = (
                    available * (child.scale_x / total_sx)
                    if total_sx > 0
                    else 0.0
                )
                child._position(cursor_x, y, cw, h, s)
                cursor_x += cw

    def _position_split(
        self, x: float, y: float, w: float, h: float, s: float,
    ) -> None:
        layouts = [c for c in self._children if isinstance(c, GpuLayout)]
        if len(layouts) >= 2:
            left_w = w * self._split_factor
            right_w = w * (1.0 - self._split_factor)
            layouts[0]._position(x, y, left_w, h, s)
            layouts[1]._position(x + left_w, y, right_w, h, s)
        elif len(layouts) == 1:
            layouts[0]._position(x, y, w, h, s)

    def _position_grid_flow(
        self, x: float, y: float, w: float, h: float, s: float,
    ) -> None:
        cols = max(1, getattr(self, "_grid_columns", 1) or 1)
        gap = scaled(
            WIDGET_GAP_ALIGNED if self._align else WIDGET_GAP, s,
        )
        col_w = w / cols

        rows = self._grid_flow_rows(cols)
        cursor_y = y + h
        for row_items in rows:
            row_h = max(
                (self._child_height(c, s) for c in row_items),
                default=0.0,
            )
            if cursor_y < y + h:
                cursor_y -= gap
            cursor_y -= row_h

            for ci, child in enumerate(row_items):
                cx = x + ci * col_w
                if isinstance(child, GpuLayout):
                    child._position(cx, cursor_y, col_w, row_h, s)

    def _grid_flow_rows(
        self, cols: int,
    ) -> list[list[GpuLayout | _Separator]]:
        """Partition children into rows of *cols* items each."""
        rows: list[list[GpuLayout | _Separator]] = []
        for i in range(0, len(self._children), cols):
            rows.append(self._children[i : i + cols])
        return rows

    # -- Draw pass -----------------------------------------------------------

    def _draw(self, s: float) -> None:
        """Recursively draw this node and its descendants."""
        if self._rect is None:
            return

        if self._is_box:
            bx, by, bw, bh = self._rect
            theme = get_theme()
            r = scaled(4.0, s)
            draw_rect_rounded(bx, by, bw, bh, r, theme.widget_bg)
            draw_rect_outline(bx, by, bw, bh, theme.border, thickness=1)

        for child in self._children:
            if isinstance(child, GpuLayout):
                child._draw(s)


# ---------------------------------------------------------------------------
# Region helpers
# ---------------------------------------------------------------------------


def get_region_offsets(area: Any) -> tuple[int, int]:
    """Return ``(offset_x, offset_y)`` to clear toolbar and header overlays.

    The 3D viewport's TOOLS, HEADER, and TOOL_HEADER regions overlay the
    WINDOW region, so ``POST_PIXEL`` drawing at ``(0, 0)`` sits behind
    them.  This helper inspects the area's regions and returns pixel
    offsets that push content past those overlays.
    """
    offset_x = 0
    offset_y = 0
    for r in area.regions:
        if r.type == "TOOLS":
            offset_x = max(offset_x, r.width)
        elif r.type in {"HEADER", "TOOL_HEADER"}:
            offset_y += r.height
    return offset_x, offset_y


# ---------------------------------------------------------------------------
# GpuPanel
# ---------------------------------------------------------------------------


class GpuPanel:
    """Top-level owner of a GPU-drawn UI surface.

    Manages the ``POST_PIXEL`` draw handler lifecycle, drives the
    per-frame build → layout → draw pipeline, and owns the hit-test
    registry and texture cache.
    """

    def __init__(
        self,
        width: int,
        anchor: tuple[int, int] | Callable[[], tuple[int, int]] | None = None,
        build_fn: Callable[[GpuLayout], None] | None = None,
    ) -> None:
        self._width = width
        self._anchor = anchor
        self._build_fn = build_fn

        self._root: GpuLayout | None = None
        self._hit_rects: list[HitResult] = []
        self._handle: object | None = None
        self._area: object | None = None
        self._texture_cache: dict[str, object] = {}
        self._ui_scale: float = 1.0
        self._panel_rect: tuple[float, float, float, float] | None = None

    # -- Lifecycle -----------------------------------------------------------

    def attach(self, area: Any) -> None:
        """Register the ``POST_PIXEL`` draw handler on *area*'s WINDOW region."""
        self._area = area
        self._handle = bpy.types.SpaceView3D.draw_handler_add(
            self._draw_callback, (), "WINDOW", "POST_PIXEL",
        )

    def detach(self) -> None:
        """Remove the draw handler and release all resources."""
        if self._handle is not None:
            bpy.types.SpaceView3D.draw_handler_remove(
                self._handle, "WINDOW",
            )
            self._handle = None
        self._area = None
        self._root = None
        self._hit_rects.clear()
        self._texture_cache.clear()
        self._panel_rect = None

    # -- Frame cycle ---------------------------------------------------------

    def begin_frame(self) -> GpuLayout:
        """Clear the widget tree, reset hit rects, return the root layout."""
        self._ui_scale = get_ui_scale()
        self._hit_rects.clear()
        self._root = GpuLayout(self, direction="COLUMN")
        return self._root

    def end_frame(self) -> None:
        """Run the layout pass then the draw pass."""
        if self._root is None:
            return

        s = self._ui_scale
        w = scaled(self._width, s)
        h = self._root._measure_height(s)

        # Determine anchor (top-left of panel in region pixels).
        anchor = self._anchor
        if callable(anchor):
            anchor = anchor()
        if anchor is not None:
            ax = float(anchor[0])
            ay = float(anchor[1])
        else:
            try:
                region = bpy.context.region
                ax = (region.width - w) / 2
                ay = (region.height + h) / 2
            except Exception:
                ax, ay = 0.0, h

        # Panel rect: (x, y) is bottom-left.
        panel_x = ax
        panel_y = ay - h
        self._panel_rect = (panel_x, panel_y, w, h)

        # Position pass then draw pass.
        self._root._position(panel_x, panel_y, w, h, s)

        # Panel background.
        theme = get_theme()
        r = scaled(6.0, s)
        draw_rect_rounded(panel_x, panel_y, w, h, r, theme.panel_bg)
        draw_rect_outline(panel_x, panel_y, w, h, theme.border, thickness=1)

        self._root._draw(s)

    # -- Internal draw handler -----------------------------------------------

    def _draw_callback(self) -> None:
        """Entry point called by Blender's draw-handler machinery."""
        gpu.state.blend_set("ALPHA")
        try:
            root = self.begin_frame()
            if self._build_fn is not None:
                self._build_fn(root)
            self.end_frame()
        finally:
            gpu.state.blend_set("NONE")

    # -- Hit testing ---------------------------------------------------------

    def hit_test(self, mx: int, my: int) -> HitResult | None:
        """Return the topmost interactive widget at region-local *(mx, my)*."""
        for hr in reversed(self._hit_rects):
            rx, ry, rw, rh = hr.rect
            if rx <= mx <= rx + rw and ry <= my <= ry + rh:
                return hr
        return None

    def is_inside(self, mx: int, my: int) -> bool:
        """Return ``True`` if *(mx, my)* is within the panel bounding box."""
        if self._panel_rect is None:
            return False
        px, py, pw, ph = self._panel_rect
        return px <= mx <= px + pw and py <= my <= py + ph

    # -- Texture cache -------------------------------------------------------

    def get_texture(self, path: str) -> Any | None:
        """Load, cache, and return a GPU texture from *path*."""
        if path in self._texture_cache:
            return self._texture_cache[path]
        try:
            img = bpy.data.images.load(path, check_existing=True)
            texture = gpu.texture.from_image(img)
            self._texture_cache[path] = texture
            return texture
        except Exception:
            self._texture_cache[path] = None
            return None
