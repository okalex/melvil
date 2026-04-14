"""Label widget for the GPU UI toolkit."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .constants import WIDGET_HEIGHT, scaled
from .theme import get_theme
from .widget import GpuWidget

if TYPE_CHECKING:
    from .ui_context import UiContext


@dataclass
class GpuLabel(GpuWidget):
    """Non-interactive text label."""

    def measure_height(self, s: float) -> float:
        return scaled(WIDGET_HEIGHT, s)

    def draw(self, s: float, parent_enabled: bool, ui_context: UiContext) -> None:
        theme = get_theme()
        color = self._resolve_text_color(parent_enabled, theme.text_primary)
        self._draw_text_content(s, color, align="LEFT", ui_context=ui_context)
