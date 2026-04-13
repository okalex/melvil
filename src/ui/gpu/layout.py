"""Layout container for the GPU UI toolkit."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .constants import (
    BOX_PAD,
    SEPARATOR_HEIGHT,
    WIDGET_GAP,
    WIDGET_GAP_ALIGNED,
    scaled,
)
from .drawing import draw_rect_outline, draw_rect_rounded
from .theme import get_theme
from .widget import GpuWidget, _Separator, _draw_widget, _widget_height

if TYPE_CHECKING:
    from .panel import GpuPanel


class GpuLayout:
    """Immediate-mode layout container mirroring ``bpy.types.UILayout``.

    Callers build a widget tree each frame by calling container methods
    (``row``, ``column``, ``split``, ``box``, ``separator``).  The tree is
    then walked in a **measure** pass (bottom-up heights), a **position**
    pass (top-down coordinate assignment), and a **draw** pass.
    """

    def __init__(
        self,
        panel: GpuPanel,
        *,
        direction: str = "COLUMN",
        align: bool = False,
        is_box: bool = False,
        split_factor: float = 0.5,
    ) -> None:
        self._panel = panel
        self._direction = direction
        self._align = align
        self._is_box = is_box
        self._split_factor = split_factor
        self._children: list[GpuLayout | _Separator | GpuWidget] = []
        self._rect: tuple[float, float, float, float] | None = None

        # Public properties (matching UILayout).
        self.enabled: bool = True
        self.alert: bool = False
        self.alignment: str = "EXPAND"
        self.scale_x: float = 1.0
        self.scale_y: float = 1.0

    # -- Container methods ---------------------------------------------------

    def row(self, align: bool = False) -> GpuLayout:
        child = GpuLayout(self._panel, direction="ROW", align=align)
        self._children.append(child)
        return child

    def column(self, align: bool = False) -> GpuLayout:
        child = GpuLayout(self._panel, direction="COLUMN", align=align)
        self._children.append(child)
        return child

    def split(self, *, factor: float = 0.5, align: bool = False) -> GpuLayout:
        child = GpuLayout(
            self._panel, direction="SPLIT", align=align, split_factor=factor,
        )
        self._children.append(child)
        return child

    def box(self) -> GpuLayout:
        child = GpuLayout(self._panel, direction="COLUMN", is_box=True)
        self._children.append(child)
        return child

    def separator(self, *, factor: float = 1.0) -> None:
        self._children.append(_Separator(factor=factor))

    def label(self, *, text: str = "", icon: str = "NONE") -> None:
        """Append a non-interactive text label."""
        self._children.append(GpuWidget(
            kind="label", text=text, icon=icon,
            enabled=self.enabled, alert=self.alert,
        ))

    def grid_flow(
        self,
        row_major: bool = True,
        columns: int = 0,
        even_columns: bool = True,
        even_rows: bool = True,
        align: bool = False,
    ) -> GpuLayout:
        child = GpuLayout(self._panel, direction="GRID_FLOW", align=align)
        child._grid_columns = columns
        child._grid_row_major = row_major
        child._grid_even_columns = even_columns
        child._grid_even_rows = even_rows
        self._children.append(child)
        return child

    # -- Measure pass (bottom-up) -------------------------------------------

    def _child_height(self, child: GpuLayout | _Separator | GpuWidget, s: float) -> float:
        """Return the measured height of a single child."""
        if isinstance(child, _Separator):
            return scaled(SEPARATOR_HEIGHT * child.factor, s)
        if isinstance(child, GpuWidget):
            return _widget_height(child, s)
        return child._measure_height(s) * child.scale_y

    @staticmethod
    def _is_separator(child: GpuLayout | _Separator | GpuWidget) -> bool:
        """Return ``True`` if *child* acts as a separator for gap logic."""
        if isinstance(child, _Separator):
            return True
        if isinstance(child, GpuWidget) and child.kind == "separator":
            return True
        return False

    @staticmethod
    def _gap_before(
        children: list[GpuLayout | _Separator | GpuWidget], index: int,
    ) -> bool:
        """Return ``True`` if a gap should be inserted before *index*.

        Gaps appear between consecutive non-separator children.  Separators
        provide their own spacing so no extra gap is added adjacent to them.
        """
        if index == 0:
            return False
        return (
            not GpuLayout._is_separator(children[index])
            and not GpuLayout._is_separator(children[index - 1])
        )

    def _measure_height(self, s: float) -> float:
        """Compute the natural height of this node (children sum/max)."""
        if not self._children:
            return 0.0

        gap = scaled(
            WIDGET_GAP_ALIGNED if self._align else WIDGET_GAP, s,
        )

        if self._direction in ("COLUMN", "GRID_FLOW"):
            total = 0.0
            if self._direction == "GRID_FLOW":
                cols = max(1, getattr(self, "_grid_columns", 1) or 1)
                rows_of_items = self._grid_flow_rows(cols)
                for row_items in rows_of_items:
                    row_h = max(
                        (self._child_height(c, s) for c in row_items),
                        default=0.0,
                    )
                    if total > 0:
                        total += gap
                    total += row_h
            else:
                for i, child in enumerate(self._children):
                    if self._gap_before(self._children, i):
                        total += gap
                    total += self._child_height(child, s)
        else:
            # ROW / SPLIT: height = max of children.
            total = max(
                (self._child_height(c, s) for c in self._children),
                default=0.0,
            )

        if self._is_box:
            total += scaled(BOX_PAD * 2, s)

        return total

    # -- Position pass (top-down) -------------------------------------------

    def _position(
        self, x: float, y: float, w: float, h: float, s: float,
    ) -> None:
        """Assign ``(x, y, w, h)`` to self and all descendants."""
        self._rect = (x, y, w, h)

        inner_x, inner_y, inner_w, inner_h = x, y, w, h
        if self._is_box:
            pad = scaled(BOX_PAD, s)
            inner_x += pad
            inner_y += pad
            inner_w -= pad * 2
            inner_h -= pad * 2

        if self._direction == "COLUMN":
            self._position_column(inner_x, inner_y, inner_w, inner_h, s)
        elif self._direction == "ROW":
            self._position_row(inner_x, inner_y, inner_w, inner_h, s)
        elif self._direction == "SPLIT":
            self._position_split(inner_x, inner_y, inner_w, inner_h, s)
        elif self._direction == "GRID_FLOW":
            self._position_grid_flow(inner_x, inner_y, inner_w, inner_h, s)

    def _position_column(
        self, x: float, y: float, w: float, h: float, s: float,
    ) -> None:
        gap = scaled(
            WIDGET_GAP_ALIGNED if self._align else WIDGET_GAP, s,
        )
        cursor_y = y + h  # start at top

        for i, child in enumerate(self._children):
            child_h = self._child_height(child, s)
            if self._gap_before(self._children, i):
                cursor_y -= gap
            cursor_y -= child_h

            if isinstance(child, GpuLayout):
                child._position(x, cursor_y, w, child_h, s)
            elif isinstance(child, GpuWidget):
                child.rect = (x, cursor_y, w, child_h)

    def _position_row(
        self, x: float, y: float, w: float, h: float, s: float,
    ) -> None:
        if not self._children:
            return

        gap = scaled(
            WIDGET_GAP_ALIGNED if self._align else WIDGET_GAP, s,
        )

        # Tally separator widths and gaps between non-sep children.
        sep_w = 0.0
        n_gaps = 0
        nonsep: list[GpuLayout | GpuWidget] = []
        for i, child in enumerate(self._children):
            if isinstance(child, _Separator):
                sep_w += scaled(SEPARATOR_HEIGHT * child.factor, s)
            elif isinstance(child, GpuWidget) and child.kind == "separator":
                sep_w += _widget_height(child, s)
            else:
                nonsep.append(child)
                if self._gap_before(self._children, i):
                    n_gaps += 1

        available = w - sep_w - n_gaps * gap
        total_sx = sum(
            c.scale_x if isinstance(c, GpuLayout) else 1.0
            for c in nonsep
        ) if nonsep else 1.0

        cursor_x = x
        for i, child in enumerate(self._children):
            if self._gap_before(self._children, i):
                cursor_x += gap

            if isinstance(child, _Separator):
                cursor_x += scaled(SEPARATOR_HEIGHT * child.factor, s)
            elif isinstance(child, GpuWidget) and child.kind == "separator":
                cursor_x += _widget_height(child, s)
            elif isinstance(child, GpuWidget):
                sx = 1.0
                cw = available * (sx / total_sx) if total_sx > 0 else 0.0
                child.rect = (cursor_x, y, cw, h)
                cursor_x += cw
            elif isinstance(child, GpuLayout):
                cw = (
                    available * (child.scale_x / total_sx)
                    if total_sx > 0
                    else 0.0
                )
                child._position(cursor_x, y, cw, h, s)
                cursor_x += cw

    def _position_split(
        self, x: float, y: float, w: float, h: float, s: float,
    ) -> None:
        layouts = [c for c in self._children if isinstance(c, GpuLayout)]
        if len(layouts) >= 2:
            left_w = w * self._split_factor
            right_w = w * (1.0 - self._split_factor)
            layouts[0]._position(x, y, left_w, h, s)
            layouts[1]._position(x + left_w, y, right_w, h, s)
        elif len(layouts) == 1:
            layouts[0]._position(x, y, w, h, s)

    def _position_grid_flow(
        self, x: float, y: float, w: float, h: float, s: float,
    ) -> None:
        cols = max(1, getattr(self, "_grid_columns", 1) or 1)
        gap = scaled(
            WIDGET_GAP_ALIGNED if self._align else WIDGET_GAP, s,
        )
        col_w = w / cols

        rows = self._grid_flow_rows(cols)
        cursor_y = y + h
        for row_items in rows:
            row_h = max(
                (self._child_height(c, s) for c in row_items),
                default=0.0,
            )
            if cursor_y < y + h:
                cursor_y -= gap
            cursor_y -= row_h

            for ci, child in enumerate(row_items):
                cx = x + ci * col_w
                if isinstance(child, GpuLayout):
                    child._position(cx, cursor_y, col_w, row_h, s)
                elif isinstance(child, GpuWidget):
                    child.rect = (cx, cursor_y, col_w, row_h)

    def _grid_flow_rows(
        self, cols: int,
    ) -> list[list[GpuLayout | _Separator | GpuWidget]]:
        """Partition children into rows of *cols* items each."""
        rows: list[list[GpuLayout | _Separator | GpuWidget]] = []
        for i in range(0, len(self._children), cols):
            rows.append(self._children[i : i + cols])
        return rows

    # -- Draw pass -----------------------------------------------------------

    def _draw(self, s: float) -> None:
        """Recursively draw this node and its descendants."""
        if self._rect is None:
            return

        if self._is_box:
            bx, by, bw, bh = self._rect
            theme = get_theme()
            r = scaled(4.0, s)
            draw_rect_rounded(bx, by, bw, bh, r, theme.widget_bg)
            draw_rect_outline(bx, by, bw, bh, theme.border, thickness=1)

        for child in self._children:
            if isinstance(child, GpuLayout):
                child._draw(s)
            elif isinstance(child, GpuWidget):
                _draw_widget(child, s, self.enabled)
