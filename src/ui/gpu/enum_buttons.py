"""Enum toggle-button group for the GPU UI toolkit."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .constants import WIDGET_GAP_ALIGNED, WIDGET_HEIGHT, scaled
from .drawing import draw_rect_outline, draw_rect_rounded
from .theme import get_theme
from .widget import GpuWidget, draw_text_in_rect, point_in_rect

if TYPE_CHECKING:
    from .panel import GpuPanel


@dataclass
class GpuEnumButtons(GpuWidget):
    """Column of toggle buttons for an expanded ``EnumProperty``.

    Each enum item is drawn as a button.  The item whose *identifier*
    matches :attr:`active_value` renders with the active/selected
    background.  Clicking a non-active item registers a ``"prop"``
    :class:`HitResult` so the modal operator can update the property.
    """

    items: list[tuple[str, str, str, str]] = field(default_factory=list)
    """``(identifier, name, description, icon)`` per enum value."""

    active_value: str = ""
    data: Any = None
    property_name: str = ""

    def measure_height(self, s: float) -> float:
        n = len(self.items)
        if n == 0:
            return 0.0
        btn_h = scaled(WIDGET_HEIGHT, s)
        gap = scaled(WIDGET_GAP_ALIGNED, s)
        return n * btn_h + max(0, n - 1) * gap

    def draw(self, s: float, parent_enabled: bool, panel: GpuPanel) -> None:
        if self.rect is None or not self.items:
            return

        x, y, w, h = self.rect
        theme = get_theme()
        is_enabled = self.enabled and parent_enabled
        btn_h = scaled(WIDGET_HEIGHT, s)
        gap = scaled(WIDGET_GAP_ALIGNED, s)
        r = scaled(4.0, s)

        cursor_y = y + h  # start at top, draw downward

        for identifier, name, _desc, _icon in self.items:
            cursor_y -= btn_h
            btn_rect = (x, cursor_y, w, btn_h)
            is_active = identifier == self.active_value
            hovered = is_enabled and point_in_rect(panel._mouse_pos, btn_rect)

            # -- Background ---------------------------------------------------
            if is_active:
                bg = theme.widget_bg_active
            elif hovered:
                bg = theme.button_bg_hover
            else:
                bg = theme.button_bg
            draw_rect_rounded(x, cursor_y, w, btn_h, r, bg)
            draw_rect_outline(x, cursor_y, w, btn_h, theme.border, thickness=1)

            # -- Text ---------------------------------------------------------
            if is_active:
                text_color = self._resolve_text_color(
                    parent_enabled, theme.selection_text,
                )
            else:
                text_color = self._resolve_text_color(
                    parent_enabled, theme.button_text,
                )
            draw_text_in_rect(name, btn_rect, s, text_color)

            # -- Hit-rect registration ----------------------------------------
            if is_enabled:
                from .panel import HitResult  # Deferred to avoid circular import.

                panel._hit_rects.append(HitResult(
                    widget_type="prop",
                    id=self.property_name,
                    kwargs={"data": self.data, "value": identifier},
                    rect=btn_rect,
                ))

            cursor_y -= gap
