"""GPU drawing primitives for the GPU UI toolkit."""

from __future__ import annotations

import math

import gpu
import blf
from gpu_extras.batch import batch_for_shader

from .constants import FONT_ID


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
# Shape primitives
# ---------------------------------------------------------------------------

def draw_rect(x: float, y: float, w: float, h: float, color: tuple) -> None:
    """Draw a filled rectangle at (*x*, *y*) with size *w* x *h*."""
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
    """Draw a rectangular outline at (*x*, *y*) with size *w* x *h*."""
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
        (x + r,     y + r),      # BL — angles pi to 3pi/2
        (x + w - r, y + r),      # BR — angles 3pi/2 to 2pi
        (x + w - r, y + h - r),  # TR — angles 0 to pi/2
        (x + r,     y + h - r),  # TL — angles pi/2 to pi
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
    """Draw a GPU texture at (*x*, *y*) with size *w* x *h*."""
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
