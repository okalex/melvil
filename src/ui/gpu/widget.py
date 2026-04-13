"""Base widget class for the GPU UI toolkit."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .constants import FONT_SIZE_PRIMARY, ICON_SIZE, WIDGET_PAD_X, scaled
from .drawing import draw_text, draw_texture, measure_text
from .theme import get_theme

if TYPE_CHECKING:
    from .panel import GpuPanel


# ---------------------------------------------------------------------------
# Shared geometry / drawing helpers
# ---------------------------------------------------------------------------


def point_in_rect(
    pos: tuple[float, float] | None,
    rect: tuple[float, float, float, float],
) -> bool:
    """Return ``True`` if *pos* lies inside *rect*."""
    if pos is None:
        return False
    mx, my = pos
    x, y, w, h = rect
    return x <= mx <= x + w and y <= my <= y + h


def draw_icon(
    icon: str,
    rect: tuple[float, float, float, float],
    s: float,
    panel: GpuPanel,
) -> float:
    """Draw a built-in Blender icon at the left edge of *rect*.

    Returns the horizontal offset consumed (padding + icon width) or
    ``0.0`` if the icon is ``"NONE"`` or unavailable.
    """
    if icon == "NONE":
        return 0.0
    provider = panel._icon_provider
    if provider is None:
        return 0.0
    atlas = provider.atlas
    if atlas is None:
        return 0.0
    uv = provider.get_icon_uv(icon)
    if uv is None:
        return 0.0

    icon_size = scaled(ICON_SIZE, s)
    pad = scaled(WIDGET_PAD_X, s)
    x, y, _w, h = rect
    icon_x = x + pad
    icon_y = y + (h - icon_size) / 2
    draw_texture(atlas, icon_x, icon_y, icon_size, icon_size, uv_rect=uv)
    return pad + icon_size


def draw_text_in_rect(
    text: str,
    rect: tuple[float, float, float, float],
    s: float,
    color: tuple[float, float, float, float],
    *,
    align: str = "CENTER",
) -> None:
    """Draw *text* within *rect* with vertical centering.

    *align* controls horizontal placement: ``"LEFT"`` (with padding),
    ``"CENTER"``, or ``"RIGHT"`` (with padding).
    """
    if not text:
        return
    x, y, w, h = rect
    font_size = scaled(FONT_SIZE_PRIMARY, s)
    pad = scaled(WIDGET_PAD_X, s)
    text_w, text_h = measure_text(text, font_size)
    text_y = y + (h - text_h) / 2

    if align == "CENTER":
        text_x = x + (w - text_w) / 2
    elif align == "RIGHT":
        text_x = x + w - pad - text_w
    else:  # LEFT
        text_x = x + pad

    draw_text(text, text_x, text_y, font_size, color)


# ---------------------------------------------------------------------------
# Base widget
# ---------------------------------------------------------------------------


@dataclass
class GpuWidget:
    """Base class for leaf widgets stored as children of :class:`GpuLayout`.

    Subclasses implement :meth:`measure_height` and :meth:`draw` to define
    their own measurement and rendering behaviour.
    """

    text: str = ""
    icon: str = "NONE"
    enabled: bool = True
    alert: bool = False

    # Assigned during the position pass.
    rect: tuple[float, float, float, float] | None = None

    def measure_height(self, s: float) -> float:
        """Return the height of this widget at UI scale *s*."""
        raise NotImplementedError

    def draw(self, s: float, parent_enabled: bool, panel: GpuPanel) -> None:
        """Draw this widget.  Called during the draw pass."""
        raise NotImplementedError

    @property
    def is_separator(self) -> bool:
        """Return ``True`` if this widget acts as a separator for gap logic."""
        return False

    # -- Shared helpers for subclasses --------------------------------------

    def _resolve_text_color(
        self, parent_enabled: bool, default: tuple[float, float, float, float],
    ) -> tuple[float, float, float, float]:
        """Pick the text color based on *enabled* / *alert* state."""
        theme = get_theme()
        if self.alert:
            return theme.alert
        if not self.enabled or not parent_enabled:
            return theme.text_disabled
        return default

    def _draw_text_content(
        self,
        s: float,
        color: tuple[float, float, float, float],
        *,
        align: str = "CENTER",
        panel: GpuPanel | None = None,
    ) -> None:
        """Draw :attr:`text` within :attr:`rect` with vertical centering.

        *align* controls horizontal placement: ``"LEFT"`` (with padding),
        ``"CENTER"``, or ``"RIGHT"`` (with padding).

        When *panel* is provided and :attr:`icon` is set, the icon is
        drawn at the left edge and text is offset accordingly.
        """
        if self.rect is None:
            return
        rect = self.rect
        if panel is not None and self.icon != "NONE":
            icon_offset = draw_icon(self.icon, rect, s, panel)
            if icon_offset > 0:
                x, y, w, h = rect
                rect = (x + icon_offset, y, w - icon_offset, h)
        if self.text:
            draw_text_in_rect(self.text, rect, s, color, align=align)
