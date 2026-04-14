"""Icon-only button widget for the GPU UI toolkit.

Used inside list row ``draw_fn`` callbacks to provide per-row actions
(e.g. a rename pencil icon).  The widget is only visible when the
parent :class:`GpuLayout` has ``_list_context`` indicating the row is
hovered or selected.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .constants import ICON_SIZE, WIDGET_HEIGHT, WIDGET_PAD_X, scaled
from .drawing import draw_rect_rounded
from ._hit import HitResult
from .theme import get_theme
from .widget import GpuWidget, draw_disabled_overlay, draw_icon, point_in_rect

if TYPE_CHECKING:
    from .ui_context import UiContext


@dataclass
class GpuIconButton(GpuWidget):
    """Clickable icon that registers its own hit rect.

    The icon is only drawn when the containing list row is hovered or
    selected (determined by :attr:`GpuLayout._list_context`).  Outside
    of a list context the icon is always drawn.

    Parameters
    ----------
    button_id:
        Identifier passed through the :class:`HitResult` so the click
        handler knows which action was triggered.
    show_only_on_hover:
        When ``True`` (default), the icon is hidden unless the row is
        hovered or selected.
    """

    button_id: str = ""
    show_only_on_hover: bool = True
    style: str = "DEFAULT"

    # Row context injected by GpuLayout.icon_button() from _list_context.
    _list_context: dict[str, Any] = field(default_factory=dict)

    def measure_height(self, s: float) -> float:
        return scaled(WIDGET_HEIGHT, s)

    def draw(self, s: float, parent_enabled: bool, ui_context: UiContext) -> None:
        if self.rect is None:
            return

        ctx = self._list_context
        is_row_visible = not self.show_only_on_hover or (
            ctx.get("is_hovered", False) or ctx.get("is_active", False)
        )
        if not is_row_visible:
            return

        theme = get_theme()
        x, y, w, h = self.rect
        is_enabled = self.enabled and parent_enabled
        hovered = is_enabled and point_in_rect(ui_context.get_mouse_pos(), self.rect)

        # Subtle hover highlight behind the icon (skipped for GHOST style).
        if hovered and self.style != "GHOST":
            r = scaled(3.0, s)
            draw_rect_rounded(x, y, w, h, r, theme.widget_bg_hover)

        # Draw the icon centred in the rect.
        if self.icon != "NONE":
            draw_icon(self.icon, self.rect, s, ui_context)
            if not is_enabled:
                draw_disabled_overlay(self.rect)

        # Register hit rect so clicks land on this button, not the row.
        if is_enabled:
            ui_context.register_hit(HitResult(
                widget_type="icon_button",
                id=self.button_id,
                kwargs={**ctx},
                rect=self.rect,
            ))
