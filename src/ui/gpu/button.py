"""Button (operator) widget for the GPU UI toolkit."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .constants import WIDGET_HEIGHT, scaled
from .drawing import draw_rect_outline, draw_rect_rounded
from .theme import get_theme
from .widget import GpuWidget

if TYPE_CHECKING:
    from .panel import GpuPanel


# ---------------------------------------------------------------------------
# Operator property bag
# ---------------------------------------------------------------------------


class GpuOperatorProps:
    """Attribute-style container for operator keyword arguments.

    Returned by :meth:`GpuLayout.operator` so callers can set operator
    properties exactly like Blender's ``layout.operator()``::

        op = layout.operator("melvil.load_asset", text="Load")
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

    def draw(self, s: float, parent_enabled: bool, panel: GpuPanel) -> None:
        if self.rect is None:
            return

        x, y, w, h = self.rect
        theme = get_theme()
        is_enabled = self.enabled and parent_enabled
        hovered = is_enabled and _point_in_rect(panel._mouse_pos, self.rect)
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

        # -- Text -------------------------------------------------------------
        text_color = self._resolve_text_color(parent_enabled, theme.button_text)
        self._draw_text_content(s, text_color)

        # -- Hit-rect registration -------------------------------------------
        if is_enabled:
            from .panel import HitResult  # Deferred to avoid circular import.

            panel._hit_rects.append(HitResult(
                widget_type="operator",
                id=self.operator_id,
                kwargs=dict(self.operator_props._props),
                rect=self.rect,
            ))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _point_in_rect(
    pos: tuple[float, float] | None,
    rect: tuple[float, float, float, float],
) -> bool:
    """Return ``True`` if *pos* lies inside *rect*."""
    if pos is None:
        return False
    mx, my = pos
    x, y, w, h = rect
    return x <= mx <= x + w and y <= my <= y + h
