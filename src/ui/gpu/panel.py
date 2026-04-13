"""Top-level panel and hit-testing for the GPU UI toolkit."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import bpy
import gpu

from .constants import get_ui_scale, scaled
from .drawing import draw_rect_outline, draw_rect_rounded
from .layout import GpuLayout
from .theme import get_theme


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
    per-frame build -> layout -> draw pipeline, and owns the hit-test
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
        self._mouse_pos: tuple[float, float] | None = None

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
        self._mouse_pos = None

    def update_mouse(self, mx: float, my: float) -> None:
        """Store the latest mouse position for hover detection."""
        self._mouse_pos = (mx, my)

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
