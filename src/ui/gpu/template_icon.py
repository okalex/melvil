"""Large preview image widget for the GPU UI toolkit."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .constants import ICON_SIZE, scaled
from .drawing import draw_texture
from .widget import GpuWidget

if TYPE_CHECKING:
    from .panel import GpuPanel


@dataclass
class GpuTemplateIcon(GpuWidget):
    """Displays a large preview image identified by *icon_value*.

    Mirrors ``UILayout.template_icon(icon_value=..., scale=...)``.
    The *icon_value* is an integer preview-collection icon ID.  The panel
    resolves it to a GPU texture via its preview path registry
    (:meth:`GpuPanel.register_preview` / :meth:`GpuPanel.get_preview_texture`).
    """

    icon_value: int = 0
    scale: float = 1.0

    def measure_height(self, s: float) -> float:
        return scaled(ICON_SIZE, s) * self.scale

    def draw(self, s: float, parent_enabled: bool, panel: GpuPanel) -> None:
        if self.rect is None or self.icon_value == 0:
            return

        x, y, w, h = self.rect
        texture = panel.get_preview_texture(self.icon_value)
        if texture is None:
            return

        # Draw centred within the allocated rect, maintaining square aspect.
        size = min(w, h)
        draw_x = x + (w - size) / 2
        draw_y = y + (h - size) / 2
        draw_texture(texture, draw_x, draw_y, size, size)
