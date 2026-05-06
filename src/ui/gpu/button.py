"""Button (operator) widget for the GPU UI toolkit."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .constants import WIDGET_HEIGHT, scaled
from .drawing import draw_rect_outline, draw_rect_rounded
from ._hit import HitResult
from .theme import get_theme
from .widget import GpuWidget, draw_disabled_overlay, draw_icon_centered, point_in_rect

if TYPE_CHECKING:
    from .ui_context import UiContext


# ---------------------------------------------------------------------------
# Operator property bag
# ---------------------------------------------------------------------------


class GpuOperatorProps:
    """Attribute-style container for operator keyword arguments.

    Returned by :meth:`GpuLayout.operator` so callers can set operator
    properties exactly like Blender's ``layout.operator()``::

        op = layout.operator("blammo.load_asset", text="Load")
        op.asset_id = "abc"
    """

    def __init__(self) -> None:
        self._props: dict[str, Any] = {}

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_"):
            super().__setattr__(name, value)
        else:
            self._props[name] = value

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)
        return self._props.get(name)


# ---------------------------------------------------------------------------
# Button widget
# ---------------------------------------------------------------------------


@dataclass
class GpuButton(GpuWidget):
    """Clickable button that invokes an operator via hit-test dispatch."""

    operator_id: str = ""
    operator_props: GpuOperatorProps = field(default_factory=GpuOperatorProps)
    emboss: bool = True
    depress: bool = False

    def measure_height(self, s: float) -> float:
        return scaled(WIDGET_HEIGHT, s)

    def draw(self, s: float, parent_enabled: bool, ui_context: UiContext) -> None:
        if self.rect is None:
            return

        x, y, w, h = self.rect
        theme = get_theme()
        is_enabled = self.enabled and parent_enabled
        hovered = is_enabled and point_in_rect(ui_context.get_mouse_pos(), self.rect)
        r = scaled(4.0, s)

        # -- Background ------------------------------------------------------
        if self.emboss:
            if self.depress:
                bg = theme.widget_bg_active
            elif hovered:
                bg = theme.button_bg_hover
            else:
                bg = theme.button_bg
            draw_rect_rounded(x, y, w, h, r, bg)
            draw_rect_outline(x, y, w, h, theme.border, thickness=1)
        elif hovered:
            hover_color = (
                theme.widget_bg_hover[0],
                theme.widget_bg_hover[1],
                theme.widget_bg_hover[2],
                theme.widget_bg_hover[3] * 0.5,
            )
            draw_rect_rounded(x, y, w, h, r, hover_color)

        # -- Text + icon ------------------------------------------------------
        text_color = self._resolve_text_color(parent_enabled, theme.button_text)
        if not self.text and self.icon != "NONE":
            # Icon-only: centre the icon within the button.
            draw_icon_centered(self.icon, self.rect, s, ui_context)
            if not is_enabled:
                draw_disabled_overlay(self.rect)
        else:
            self._draw_text_content(s, text_color, ui_context=ui_context)

        # -- Hit-rect registration -------------------------------------------
        if is_enabled:
            ui_context.register_hit(HitResult(
                widget_type="operator",
                id=self.operator_id,
                kwargs=dict(self.operator_props._props),
                rect=self.rect,
            ))
