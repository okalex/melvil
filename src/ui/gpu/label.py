"""Label widget for the GPU UI toolkit."""

from __future__ import annotations

from dataclasses import dataclass

from .constants import FONT_SIZE_PRIMARY, WIDGET_HEIGHT, WIDGET_PAD_X, scaled
from .drawing import draw_text, measure_text
from .theme import get_theme
from .widget import GpuWidget


@dataclass
class GpuLabel(GpuWidget):
    """Non-interactive text label."""

    def measure_height(self, s: float) -> float:
        return scaled(WIDGET_HEIGHT, s)

    def draw(self, s: float, parent_enabled: bool) -> None:
        if self.rect is None:
            return
        x, y, w, h = self.rect
        theme = get_theme()

        if self.alert:
            color = theme.alert
        elif not self.enabled or not parent_enabled:
            color = theme.text_disabled
        else:
            color = theme.text_primary

        if self.text:
            font_size = scaled(FONT_SIZE_PRIMARY, s)
            pad = scaled(WIDGET_PAD_X, s)
            _, text_h = measure_text(self.text, font_size)
            text_y = y + (h - text_h) / 2
            draw_text(self.text, x + pad, text_y, font_size, color)
