"""
GPU UI toolkit — foundational drawing primitives, theme colors, and DPI helpers.

This module provides the rendering foundation for the GPU-drawn browser UI.
All drawing functions use Blender's ``gpu`` and ``blf`` modules to render
directly into a ``SpaceView3D`` ``POST_PIXEL`` draw handler.

See projects/006-gpu-ui.md for the full design spec.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import bpy
import gpu
import blf
from gpu_extras.batch import batch_for_shader


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
            return (float(color[0]), float(color[1]),
                    float(color[2]), float(color[3]))

        text_primary = _rgba(ui.wcol_regular.text)
        panel_bg = _rgba(ui.wcol_regular.inner)
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
        except Exception:
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
