"""Widget leaf nodes and draw dispatch for the GPU UI toolkit."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .constants import (
    FONT_SIZE_PRIMARY,
    SEPARATOR_HEIGHT,
    WIDGET_HEIGHT,
    WIDGET_PAD_X,
    scaled,
)
from .drawing import draw_text, measure_text
from .theme import get_theme


# ---------------------------------------------------------------------------
# Layout-tree leaf nodes
# ---------------------------------------------------------------------------


@dataclass
class _Separator:
    """Vertical (or horizontal) spacer inserted by :meth:`GpuLayout.separator`."""

    factor: float = 1.0


# ---------------------------------------------------------------------------
# Widget leaf nodes
# ---------------------------------------------------------------------------


@dataclass
class GpuWidget:
    """Leaf widget stored as a child of :class:`GpuLayout`.

    The ``kind`` field acts as a discriminator — the draw pass dispatches
    to a kind-specific draw function.  Additional kind-specific fields are
    added as future phases introduce new widget types.
    """

    kind: str  # "label", "separator", "button", ...
    text: str = ""
    icon: str = "NONE"
    enabled: bool = True
    alert: bool = False
    # Separator-specific
    scale_y: float = 1.0

    # Assigned during the position pass.
    rect: tuple[float, float, float, float] | None = None


# -- Widget measurement / drawing ------------------------------------------

def _widget_height(widget: GpuWidget, s: float) -> float:
    """Return the height of *widget* at UI scale *s*."""
    if widget.kind == "separator":
        return scaled(SEPARATOR_HEIGHT * widget.scale_y, s)
    if widget.kind == "label":
        return scaled(WIDGET_HEIGHT, s)
    return scaled(WIDGET_HEIGHT, s)


def _draw_widget(widget: GpuWidget, s: float, parent_enabled: bool) -> None:
    """Dispatch drawing for *widget* based on its ``kind``."""
    if widget.rect is None:
        return
    drawer = _WIDGET_DRAWERS.get(widget.kind)
    if drawer is not None:
        drawer(widget, s, parent_enabled)


def _draw_label(widget: GpuWidget, s: float, parent_enabled: bool) -> None:
    """Draw a label widget — non-interactive text."""
    x, y, w, h = widget.rect
    theme = get_theme()

    if widget.alert:
        color = theme.alert
    elif not widget.enabled or not parent_enabled:
        color = theme.text_disabled
    else:
        color = theme.text_primary

    if widget.text:
        font_size = scaled(FONT_SIZE_PRIMARY, s)
        pad = scaled(WIDGET_PAD_X, s)
        _, text_h = measure_text(widget.text, font_size)
        text_y = y + (h - text_h) / 2
        draw_text(widget.text, x + pad, text_y, font_size, color)


def _draw_separator(widget: GpuWidget, s: float, parent_enabled: bool) -> None:
    """Separators are pure whitespace — nothing to draw."""
    pass


_WIDGET_DRAWERS: dict[str, Callable] = {
    "label": _draw_label,
    "separator": _draw_separator,
}
