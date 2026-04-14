"""Dropdown widget for the GPU UI toolkit.

Provides :class:`GpuDropdown`, the trigger button that appears in the
widget tree, and :class:`DropdownState`, the transient overlay state
held by :class:`GpuPanel` while the dropdown is open.

The dropdown supports two modes:

- **prop** — selecting an item sets a property value (used by
  ``layout.prop(data, prop, expand=False)`` for enum properties).
- **operator** — selecting an item invokes an operator with the
  chosen enum value (used by ``layout.operator_menu_enum()``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .constants import (
    WIDGET_GAP_ALIGNED,
    WIDGET_HEIGHT,
    WIDGET_PAD_X,
    scaled,
)
from .drawing import draw_rect_outline, draw_rect_rounded, draw_rect_rounded_outline
from .theme import get_theme
from .widget import (
    GpuWidget,
    draw_icon,
    draw_text_in_rect,
    point_in_rect,
)

if TYPE_CHECKING:
    from .panel import GpuPanel


# ---------------------------------------------------------------------------
# Dropdown overlay state
# ---------------------------------------------------------------------------


@dataclass
class DropdownState:
    """Transient state for an open dropdown overlay.

    Created when a :class:`GpuDropdown` trigger button is clicked and
    stored on :attr:`GpuPanel.active_dropdown`.  Cleared when the user
    selects an item, clicks outside, or presses Escape.
    """

    items: list[tuple[str, str, str, str]]
    """``(identifier, name, description, icon)`` per enum value."""

    anchor_rect: tuple[float, float, float, float]
    """Rect of the trigger button (used for positioning)."""

    hovered_index: int = -1

    # -- Action on selection ------------------------------------------------

    mode: str = "prop"
    """``"prop"`` to set a property, ``"operator"`` to invoke an operator."""

    # For "prop" mode:
    data: Any = None
    property_name: str = ""

    # For "operator" mode:
    operator_id: str = ""
    operator_props: dict[str, Any] = field(default_factory=dict)

    # -- Computed geometry (set by compute_rect) ----------------------------

    rect: tuple[float, float, float, float] | None = None
    """The bounding rect of the entire dropdown overlay."""

    item_rects: list[tuple[float, float, float, float]] = field(
        default_factory=list,
    )
    """Per-item rects, populated by :meth:`draw`."""

    # -- Geometry -----------------------------------------------------------

    def compute_rect(self, s: float) -> tuple[float, float, float, float]:
        """Compute and cache the dropdown overlay rect."""
        ax, ay, aw, _ah = self.anchor_rect
        pad = scaled(WIDGET_PAD_X, s)
        item_h = scaled(WIDGET_HEIGHT, s)
        gap = scaled(WIDGET_GAP_ALIGNED, s)
        n = len(self.items)
        content_h = n * item_h + max(0, n - 1) * gap if n > 0 else item_h
        total_h = content_h + 2 * pad

        dd_x = ax
        dd_y = ay - total_h
        dd_w = aw
        dd_h = total_h
        self.rect = (dd_x, dd_y, dd_w, dd_h)
        return self.rect

    # -- Drawing ------------------------------------------------------------

    def draw(self, s: float, panel: GpuPanel) -> None:
        """Draw the dropdown overlay and populate :attr:`item_rects`."""
        if self.rect is None:
            self.compute_rect(s)

        theme = get_theme()
        dd_x, dd_y, dd_w, dd_h = self.rect  # type: ignore[misc]
        pad = scaled(WIDGET_PAD_X, s)
        item_h = scaled(WIDGET_HEIGHT, s)
        gap = scaled(WIDGET_GAP_ALIGNED, s)
        r = scaled(4.0, s)

        # Background + border.
        draw_rect_rounded(dd_x, dd_y, dd_w, dd_h, r, theme.panel_bg)
        draw_rect_rounded_outline(dd_x, dd_y, dd_w, dd_h, r, theme.border_intense)

        # Items.
        self.item_rects.clear()
        cursor_y = dd_y + dd_h - pad
        for i, (identifier, name, _desc, item_icon) in enumerate(self.items):
            cursor_y -= item_h
            if i > 0:
                cursor_y -= gap

            item_rect = (dd_x + pad, cursor_y, dd_w - 2 * pad, item_h)
            self.item_rects.append(item_rect)

            # Hover highlight.
            if i == self.hovered_index:
                ir = scaled(3.0, s)
                draw_rect_rounded(
                    item_rect[0], item_rect[1],
                    item_rect[2], item_rect[3],
                    ir, theme.selection_bg,
                )

            # Icon + text.
            text_color = (
                theme.selection_text
                if i == self.hovered_index
                else theme.text_primary
            )
            icon_offset = draw_icon(item_icon, item_rect, s, panel)
            if icon_offset > 0:
                ix, iy, iw, ih = item_rect
                text_rect = (ix + icon_offset, iy, iw - icon_offset, ih)
            else:
                text_rect = item_rect
            draw_text_in_rect(name, text_rect, s, text_color, align="LEFT")

    # -- Hit testing --------------------------------------------------------

    def hit_test(
        self, mx: float, my: float,
    ) -> int:
        """Return the item index under *(mx, my)*, or ``-1``."""
        for i, ir in enumerate(self.item_rects):
            if point_in_rect((mx, my), ir):
                return i
        return -1

    def is_inside(self, mx: float, my: float) -> bool:
        """Return ``True`` if *(mx, my)* is within the dropdown rect."""
        if self.rect is None:
            return False
        return point_in_rect((mx, my), self.rect)


# ---------------------------------------------------------------------------
# Trigger button widget
# ---------------------------------------------------------------------------


@dataclass
class GpuDropdown(GpuWidget):
    """Trigger button that opens a dropdown overlay when clicked.

    Renders as a button showing the current value (prop mode) or
    custom text (operator mode) with a dropdown arrow indicator.
    """

    dropdown_id: str = ""
    items: list[tuple[str, str, str, str]] = field(default_factory=list)
    """``(identifier, name, description, icon)`` per enum value."""

    # -- Action mode --------------------------------------------------------

    mode: str = "prop"
    """``"prop"`` to set a property, ``"operator"`` to invoke an operator."""

    # For "prop" mode:
    data: Any = None
    property_name: str = ""

    # For "operator" mode:
    operator_id: str = ""
    operator_props: dict[str, Any] = field(default_factory=dict)

    # -----------------------------------------------------------------------
    # GpuWidget interface
    # -----------------------------------------------------------------------

    def measure_height(self, s: float) -> float:
        return scaled(WIDGET_HEIGHT, s)

    def draw(self, s: float, parent_enabled: bool, panel: GpuPanel) -> None:
        if self.rect is None:
            return

        from .panel import HitResult

        x, y, w, h = self.rect
        theme = get_theme()
        is_enabled = self.enabled and parent_enabled
        hovered = is_enabled and point_in_rect(panel._mouse_pos, self.rect)
        r = scaled(4.0, s)

        # -- Background
        if hovered:
            bg = theme.button_bg_hover
        else:
            bg = theme.button_bg
        draw_rect_rounded(x, y, w, h, r, bg)
        draw_rect_outline(x, y, w, h, theme.border, thickness=1)

        # -- Display text
        display_text = self._display_text()
        text_color = self._resolve_text_color(parent_enabled, theme.button_text)

        # Reserve space for the dropdown arrow on the right.
        pad = scaled(WIDGET_PAD_X, s)
        arrow_icon_w = scaled(10.0, s)
        arrow_space = pad + arrow_icon_w + pad  # left gap + icon + right gap

        # Icon + text in the remaining area.
        content_rect = (x, y, w - arrow_space, h)
        icon_offset = draw_icon(self.icon, content_rect, s, panel)
        if icon_offset > 0:
            cx, cy, cw, ch = content_rect
            text_rect = (cx + icon_offset, cy, cw - icon_offset, ch)
        else:
            text_rect = content_rect
        draw_text_in_rect(display_text, text_rect, s, text_color, align="LEFT")

        # Dropdown arrow (centered in the reserved region).
        from .widget import draw_icon_centered
        draw_icon_centered(
            "DOWNARROW_HLT",
            (x + w - arrow_space, y, arrow_space, h),
            s, panel,
        )

        # -- Hit rect
        if is_enabled:
            panel._hit_rects.append(HitResult(
                widget_type="dropdown",
                id=self.dropdown_id,
                kwargs={
                    "items": self.items,
                    "mode": self.mode,
                    "data": self.data,
                    "property_name": self.property_name,
                    "operator_id": self.operator_id,
                    "operator_props": dict(self.operator_props),
                },
                rect=self.rect,
            ))

    # -----------------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------------

    def _display_text(self) -> str:
        """Return the text shown on the trigger button."""
        if self.text:
            return self.text
        if self.mode == "prop" and self.data is not None:
            current = getattr(self.data, self.property_name, "")
            for identifier, name, _desc, _icon in self.items:
                if identifier == current:
                    return name
        return ""
