"""Base widget class for the GPU UI toolkit."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .constants import FONT_SIZE_PRIMARY, WIDGET_PAD_X, scaled
from .drawing import draw_text, measure_text
from .theme import get_theme

if TYPE_CHECKING:
    from .panel import GpuPanel


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
    ) -> None:
        """Draw :attr:`text` within :attr:`rect` with vertical centering.

        *align* controls horizontal placement: ``"LEFT"`` (with padding),
        ``"CENTER"``, or ``"RIGHT"`` (with padding).
        """
        if self.rect is None or not self.text:
            return
        x, y, w, h = self.rect
        font_size = scaled(FONT_SIZE_PRIMARY, s)
        pad = scaled(WIDGET_PAD_X, s)
        text_w, text_h = measure_text(self.text, font_size)
        text_y = y + (h - text_h) / 2

        if align == "CENTER":
            text_x = x + (w - text_w) / 2
        elif align == "RIGHT":
            text_x = x + w - pad - text_w
        else:  # LEFT
            text_x = x + pad

        draw_text(self.text, text_x, text_y, font_size, color)
