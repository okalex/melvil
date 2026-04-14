"""Scrollable grid/list widget for the GPU UI toolkit.

Supports both multi-column grid mode and single-column list mode.
Cells are drawn by a user-provided callback via :class:`GpuLayout`.

For ``template_list`` usage (single-column tag lists, etc.), this widget
is created automatically by :meth:`GpuLayout.template_list`.

For asset card grids, callers can instantiate :class:`GpuGridList` directly
with ``cols > 1`` and an appropriate ``cell_height``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable

import gpu

from .constants import (
    LIST_BORDER_PAD,
    LIST_BORDER_RADIUS,
    SCROLLBAR_MIN_HEIGHT,
    SCROLLBAR_WIDTH,
    WIDGET_GAP,
    WIDGET_HEIGHT,
    scaled,
)
from .drawing import draw_rect_rounded, draw_rect_rounded_outline
from .theme import get_theme
from .widget import GpuWidget, point_in_rect

if TYPE_CHECKING:
    from .panel import GpuPanel


# ---------------------------------------------------------------------------
# Scroll state
# ---------------------------------------------------------------------------


@dataclass
class ScrollState:
    """Per-list scroll state stored on :class:`GpuPanel`."""

    offset: int = 0
    max_visible: int = 5
    total_items: int = 0


# ---------------------------------------------------------------------------
# GpuGridList widget
# ---------------------------------------------------------------------------


@dataclass
class GpuGridList(GpuWidget):
    """Scrollable grid/list widget.

    In **list mode** (``cols=1``): draws a single-column scrollable list
    where each row is drawn by *draw_fn* using :class:`GpuLayout` calls.

    In **grid mode** (``cols > 1``): draws a multi-column grid of cells,
    each drawn by *draw_fn*.

    Scroll state is stored on the parent :class:`GpuPanel`, keyed by
    *list_id*, so it persists across frame rebuilds.
    """

    # --- Configuration ---
    list_id: str = ""
    cols: int = 1
    rows_visible: int = 5
    cell_height: int = WIDGET_HEIGHT

    # --- Data source (PropertyGroup collection) ---
    dataptr: Any = None
    propname: str = ""
    active_dataptr: Any = None
    active_propname: str = ""

    # --- Behaviour ---
    allow_deselect: bool = False

    # --- Drawing callback ---
    # Signature: draw_fn(layout: GpuLayout, item, index: int, is_active: bool)
    draw_fn: Callable[..., None] | None = None

    # -----------------------------------------------------------------------
    # GpuWidget interface
    # -----------------------------------------------------------------------

    def measure_height(self, s: float) -> float:
        """Return the pixel height for the visible row/grid area."""
        ch = scaled(self.cell_height, s)
        gap = scaled(WIDGET_GAP, s)
        pad = scaled(LIST_BORDER_PAD, s)
        visible_rows = self.rows_visible
        return visible_rows * ch + max(0, visible_rows - 1) * gap + 2 * pad

    def draw(self, s: float, parent_enabled: bool, panel: GpuPanel) -> None:
        """Draw the grid/list, scrollbar, and register hit rects."""
        if self.rect is None or self.draw_fn is None:
            return

        # Deferred import to avoid circular dependency.
        from .layout import GpuLayout
        from .panel import HitResult

        x, y, w, h = self.rect
        theme = get_theme()

        # --- Resolve data ---
        collection = getattr(self.dataptr, self.propname, [])
        total = len(collection)

        # Visual selection is tracked on the panel separately from the
        # data-model active index so that property update callbacks
        # (which may reset the index) don't clear the highlight.
        selected_index = panel._list_selections.get(self.list_id, -1)

        # --- Scroll state ---
        scroll = panel._get_scroll_state(self.list_id)
        scroll.total_items = total
        scroll.max_visible = self.rows_visible
        max_visible_cells = self.rows_visible * self.cols
        total_rows = math.ceil(total / self.cols) if self.cols > 0 else 0
        max_offset = max(0, total_rows - self.rows_visible)
        scroll.offset = max(0, min(scroll.offset, max_offset))

        # --- Dimensions ---
        ch = scaled(self.cell_height, s)
        gap = scaled(WIDGET_GAP, s)
        pad = scaled(LIST_BORDER_PAD, s)
        has_scrollbar = total_rows > self.rows_visible
        sb_w = scaled(SCROLLBAR_WIDTH, s) if has_scrollbar else 0
        content_w = w - sb_w
        cell_w = (content_w - 2 * pad) / self.cols if self.cols > 0 else (content_w - 2 * pad)

        # --- Border ---
        br = scaled(LIST_BORDER_RADIUS, s)
        draw_rect_rounded_outline(x, y, w, h, br, theme.border)

        # --- Scissor clipping (inside the padding) ---
        inner_x = x + pad
        inner_y = y + pad
        inner_w = content_w - 2 * pad
        inner_h = h - 2 * pad
        gpu.state.scissor_test_set(True)
        gpu.state.scissor_set(int(inner_x), int(inner_y), int(inner_w), int(inner_h))

        # --- Draw cells ---
        start_row = scroll.offset
        cursor_y = y + h - pad
        for row_i in range(self.rows_visible):
            actual_row = start_row + row_i
            if actual_row >= total_rows:
                break

            cursor_y -= ch
            if row_i > 0:
                cursor_y -= gap

            for col_i in range(self.cols):
                idx = actual_row * self.cols + col_i
                if idx >= total:
                    break

                item = collection[idx]
                is_active = idx == selected_index

                cell_x = inner_x + col_i * cell_w
                cell_rect = (cell_x, cursor_y, cell_w, ch)

                # Row background: active (selected) or hovered.
                r = scaled(3.0, s)
                if is_active:
                    draw_rect_rounded(
                        cell_x, cursor_y, cell_w, ch, r, theme.selection_bg,
                    )
                elif point_in_rect(panel._mouse_pos, cell_rect):
                    draw_rect_rounded(
                        cell_x, cursor_y, cell_w, ch, r, theme.list_item_bg,
                    )

                # Draw cell content via callback.
                row_layout = GpuLayout(panel, direction="ROW")
                is_hovered = point_in_rect(panel._mouse_pos, cell_rect)
                row_layout._list_context = {
                    "list_id": self.list_id,
                    "index": idx,
                    "is_hovered": is_hovered,
                    "is_active": is_active,
                }
                self.draw_fn(row_layout, item, idx, is_active)
                row_layout._position(cell_x, cursor_y, cell_w, ch, s)
                row_layout._draw(s)

                # Register hit rect for the cell.
                panel._hit_rects.append(HitResult(
                    widget_type="list_row",
                    id=self.propname,
                    kwargs={
                        "index": idx,
                        "list_id": self.list_id,
                        "active_dataptr": self.active_dataptr,
                        "active_propname": self.active_propname,
                        "allow_deselect": self.allow_deselect,
                    },
                    rect=cell_rect,
                ))

        # --- End scissor ---
        gpu.state.scissor_test_set(False)

        # --- Scrollbar ---
        if has_scrollbar and sb_w > 0:
            self._draw_scrollbar(
                x + content_w, y + pad, sb_w, h - 2 * pad, scroll, s, theme,
            )

    # -----------------------------------------------------------------------
    # Event handling
    # -----------------------------------------------------------------------

    def handle_event(
        self, event_type: str, panel: GpuPanel, **kwargs: Any,
    ) -> bool:
        """Handle scroll events.  Returns ``True`` if consumed."""
        scroll = panel._get_scroll_state(self.list_id)
        collection = getattr(self.dataptr, self.propname, [])
        total = len(collection)
        total_rows = math.ceil(total / self.cols) if self.cols > 0 else 0
        max_offset = max(0, total_rows - self.rows_visible)

        if event_type == "SCROLL_UP":
            if scroll.offset > 0:
                scroll.offset -= 1
                return True
            return False

        if event_type == "SCROLL_DOWN":
            if scroll.offset < max_offset:
                scroll.offset += 1
                return True
            return False

        return False

    # -----------------------------------------------------------------------
    # Scrollbar
    # -----------------------------------------------------------------------

    def _draw_scrollbar(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        scroll: ScrollState,
        s: float,
        theme: Any,
    ) -> None:
        """Draw the vertical scrollbar track and handle."""
        r = w / 2

        # Track.
        draw_rect_rounded(x, y, w, h, r, theme.scrollbar_bg)

        if scroll.total_items <= 0:
            return

        total_rows = math.ceil(scroll.total_items / self.cols) if self.cols > 0 else 0
        if total_rows <= scroll.max_visible:
            return

        # Handle height proportional to visible/total ratio.
        ratio = scroll.max_visible / total_rows
        handle_h = max(scaled(SCROLLBAR_MIN_HEIGHT, s), h * ratio)

        # Handle position proportional to scroll offset.
        max_offset = max(1, total_rows - scroll.max_visible)
        travel = h - handle_h
        fraction = scroll.offset / max_offset if max_offset > 0 else 0.0
        handle_y = y + h - handle_h - fraction * travel

        draw_rect_rounded(x, handle_y, w, handle_h, r, theme.scrollbar_handle)
