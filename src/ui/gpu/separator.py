"""Separator widget for the GPU UI toolkit."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .constants import SEPARATOR_HEIGHT, scaled
from .widget import GpuWidget

if TYPE_CHECKING:
    from .ui_context import UiContext


@dataclass
class GpuSeparator(GpuWidget):
    """Vertical (or horizontal) whitespace separator."""

    factor: float = 1.0

    @property
    def is_separator(self) -> bool:
        return True

    def measure_height(self, s: float) -> float:
        return scaled(SEPARATOR_HEIGHT * self.factor, s)

    def draw(self, s: float, parent_enabled: bool, ui_context: UiContext) -> None:
        """Separators are pure whitespace — nothing to draw."""
