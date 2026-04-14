"""Text field widget for the GPU UI toolkit."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .constants import (
    FONT_SIZE_PRIMARY,
    WIDGET_HEIGHT,
    WIDGET_PAD_X,
    scaled,
)
from .drawing import (
    draw_rect,
    draw_rect_outline,
    draw_rect_rounded,
    draw_text,
    measure_text,
)
from .theme import get_theme
from .widget import GpuWidget, draw_text_in_rect

if TYPE_CHECKING:
    from .panel import GpuPanel

_CURSOR_BLINK_PERIOD = 1.06  # seconds (530 ms on, 530 ms off)


@dataclass
class GpuTextField(GpuWidget):
    """Editable single-line text field bound to a ``StringProperty``.

    Rendering is split into two states:

    * **Inactive** — rounded-rect background, 1 px border, clipped text.
    * **Active** — highlighted border, blinking cursor, optional selection
      highlight.

    The active-field state is owned by :class:`GpuPanel`; this widget
    reads ``panel.active_text_field`` to decide which state to draw.
    """

    data: Any = None
    property_name: str = ""
    prefix_text: str = ""
    textedit_update: bool = False

    def measure_height(self, s: float) -> float:
        return scaled(WIDGET_HEIGHT, s)

    def draw(self, s: float, parent_enabled: bool, panel: GpuPanel) -> None:
        if self.rect is None:
            return

        x, y, w, h = self.rect
        theme = get_theme()
        is_enabled = self.enabled and parent_enabled
        is_active = panel._text_edit.active_field == self.property_name

        pad = scaled(WIDGET_PAD_X, s)
        font_size = scaled(FONT_SIZE_PRIMARY, s)
        r = scaled(4.0, s)

        # -- Prefix label (if any) -------------------------------------------
        field_x, field_w = x, w
        if self.prefix_text:
            label_w = measure_text(self.prefix_text, font_size)[0] + pad * 2
            label_w = min(label_w, w * 0.4)
            label_rect = (x, y, label_w, h)
            label_color = self._resolve_text_color(
                parent_enabled, theme.text_primary,
            )
            draw_text_in_rect(
                self.prefix_text, label_rect, s, label_color, align="LEFT",
            )
            field_x = x + label_w
            field_w = w - label_w

        field_rect = (field_x, y, field_w, h)

        # -- Field background ------------------------------------------------
        draw_rect_rounded(field_x, y, field_w, h, r, theme.input_bg)

        # -- Border ----------------------------------------------------------
        if is_active:
            draw_rect_outline(
                field_x, y, field_w, h, theme.selection_bg, thickness=1,
            )
        else:
            draw_rect_outline(
                field_x, y, field_w, h, theme.input_border, thickness=1,
            )

        # -- Text content ----------------------------------------------------
        if is_active and panel._text_edit.buffer is not None:
            current_text = panel._text_edit.buffer
        else:
            current_text = str(getattr(self.data, self.property_name, ""))

        text_color = self._resolve_text_color(
            parent_enabled, theme.input_text,
        )
        text_x = field_x + pad
        margin = scaled(2.0, s)

        # Selection highlight (drawn behind text).
        if is_active and panel._text_edit.selection_start is not None:
            sel_start = min(panel._text_edit.selection_start, panel._text_edit.cursor_pos)
            sel_end = max(panel._text_edit.selection_start, panel._text_edit.cursor_pos)
            if sel_start != sel_end and current_text:
                pre_w = (measure_text(current_text[:sel_start], font_size)[0]
                         if sel_start > 0 else 0.0)
                sel_w = measure_text(
                    current_text[sel_start:sel_end], font_size,
                )[0]
                draw_rect_rounded(
                    text_x + pre_w, y + margin,
                    sel_w, h - margin * 2,
                    scaled(2.0, s), theme.selection_bg,
                )

        # Draw the text itself.  Use a fixed reference height so the
        # baseline stays stable regardless of which glyphs are present
        # (e.g. "aeco" vs "aleco" would otherwise shift vertically).
        _, ref_h = measure_text("Ag", font_size)
        if current_text:
            text_y = y + (h - ref_h) / 2
            draw_text(current_text, text_x, text_y, font_size, text_color)

        # -- Blinking cursor -------------------------------------------------
        if is_active:
            elapsed = time.monotonic() - panel._text_edit.blink_base
            if (elapsed % _CURSOR_BLINK_PERIOD) < _CURSOR_BLINK_PERIOD / 2:
                pre_cursor = current_text[:panel._text_edit.cursor_pos]
                cursor_x_off = (measure_text(pre_cursor, font_size)[0]
                                if pre_cursor else 0.0)
                cursor_w = max(scaled(1.0, s), 1.0)
                draw_rect(
                    text_x + cursor_x_off, y + margin,
                    cursor_w, h - margin * 2,
                    theme.input_text,
                )

        # -- Hit-rect registration -------------------------------------------
        if is_enabled:
            from .panel import HitResult  # Deferred to avoid circular import.

            panel._hit_rects.append(HitResult(
                widget_type="text_field",
                id=self.property_name,
                kwargs={"data": self.data},
                rect=field_rect,
            ))

        # Register for tab cycling and TEXTEDIT_UPDATE tracking.
        if self.property_name not in panel._text_edit.field_order:
            panel._text_edit.field_order.append(self.property_name)
        panel._text_edit.field_data[self.property_name] = self.data
        if self.textedit_update:
            panel._text_edit.textedit_update_fields.add(self.property_name)
