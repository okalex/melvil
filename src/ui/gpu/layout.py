"""Layout container for the GPU UI toolkit."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .constants import (
    BOX_PAD,
    WIDGET_GAP,
    WIDGET_GAP_ALIGNED,
    scaled,
)
from .drawing import draw_rect_outline, draw_rect_rounded
from .button import GpuButton, GpuOperatorProps
from .enum_buttons import GpuEnumButtons
from .grid_list import GpuGridList
from .icon_button import GpuIconButton
from .label import GpuLabel
from .separator import GpuSeparator
from .text_field import GpuTextField
from .template_icon import GpuTemplateIcon
from .theme import get_theme
from .widget import GpuWidget
from ._logger import _logger

if TYPE_CHECKING:
    from .panel import GpuPanel


def _resolve_dynamic_enum(
    data: object, property: str,
) -> list[tuple[str, str, str, str]]:
    """Resolve items for a dynamic-callback EnumProperty.

    Blender's ``_PropertyDeferred`` stores the keyword arguments passed to
    ``EnumProperty()``.  If ``items`` is a callable we invoke it with
    ``(data, context)`` to retrieve the current item list.
    """
    try:
        import bpy  # noqa: delayed – only needed at runtime in Blender

        ann = getattr(type(data), "__annotations__", {}).get(property)
        if ann is None:
            return []
        # _PropertyDeferred exposes .keywords (the kwargs dict).
        kw = getattr(ann, "keywords", None)
        if kw is None:
            return []
        items_src = kw.get("items")
        if items_src is None:
            return []
        if callable(items_src):
            raw = items_src(data, bpy.context)
        else:
            raw = items_src
        # Items may be 4-tuples or 5-tuples (with a numeric value).
        result = []
        for entry in raw:
            if len(entry) >= 5:
                result.append((entry[0], entry[1], entry[2], entry[3]))
            elif len(entry) >= 4:
                result.append((entry[0], entry[1], entry[2], entry[3]))
            else:
                result.append((entry[0], entry[1], "", "NONE"))
        return result
    except Exception as exc:
        _logger.log(f"_resolve_dynamic_enum({property!r}): {exc}")
        return []


def _has_textedit_update(data: object, property: str) -> bool:
    """Return ``True`` if the property annotation has ``TEXTEDIT_UPDATE``."""
    try:
        ann = getattr(type(data), "__annotations__", {}).get(property)
        if ann is None:
            return False
        kw = getattr(ann, "keywords", None)
        if kw is None:
            return False
        return "TEXTEDIT_UPDATE" in kw.get("options", set())
    except Exception:  # noqa: BLE001
        return False


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
        self._children: list[GpuLayout | GpuWidget] = []
        self._rect: tuple[float, float, float, float] | None = None

        # Public properties (matching UILayout).
        self.enabled: bool = True
        self.alert: bool = False
        self.alignment: str = "EXPAND"
        self.scale_x: float = 1.0
        self.scale_y: float = 1.0

        # Row context set by GpuGridList for per-cell layouts.
        # Contains list_id, index, is_hovered, is_active when inside a list.
        self._list_context: dict[str, object] = {}

    # -- Container methods ---------------------------------------------------

    def row(self, align: bool = False) -> GpuLayout:
        child = GpuLayout(self._panel, direction="ROW", align=align)
        child._list_context = self._list_context
        self._children.append(child)
        return child

    def column(self, align: bool = False) -> GpuLayout:
        child = GpuLayout(self._panel, direction="COLUMN", align=align)
        child._list_context = self._list_context
        self._children.append(child)
        return child

    def split(self, *, factor: float = 0.5, align: bool = False) -> GpuLayout:
        child = GpuLayout(
            self._panel, direction="SPLIT", align=align, split_factor=factor,
        )
        child._list_context = self._list_context
        self._children.append(child)
        return child

    def box(self) -> GpuLayout:
        child = GpuLayout(self._panel, direction="COLUMN", is_box=True)
        child._list_context = self._list_context
        self._children.append(child)
        return child

    def separator(self, *, factor: float = 1.0) -> None:
        self._children.append(GpuSeparator(factor=factor))

    def label(self, *, text: str = "", icon: str = "NONE") -> None:
        """Append a non-interactive text label."""
        self._children.append(GpuLabel(
            text=text, icon=icon,
            enabled=self.enabled, alert=self.alert,
        ))

    def icon_button(
        self,
        *,
        icon: str = "NONE",
        button_id: str = "",
        show_only_on_hover: bool = True,
        style: str = "DEFAULT",
    ) -> None:
        """Append a clickable icon button.

        Inside a list row ``draw_fn``, the button inherits the row's
        ``_list_context`` so it can be shown only on hover/selection and
        its :class:`HitResult` carries the row index and list ID.
        """
        self._children.append(GpuIconButton(
            icon=icon,
            button_id=button_id,
            show_only_on_hover=show_only_on_hover,
            style=style,
            enabled=self.enabled,
            _list_context=dict(self._list_context),
        ))

    def operator(
        self,
        operator: str,
        *,
        text: str = "",
        icon: str = "NONE",
        emboss: bool = True,
        depress: bool = False,
    ) -> GpuOperatorProps:
        """Append a button that invokes *operator* and return its props."""
        props = GpuOperatorProps()
        self._children.append(GpuButton(
            text=text,
            icon=icon,
            enabled=self.enabled,
            alert=self.alert,
            operator_id=operator,
            operator_props=props,
            emboss=emboss,
            depress=depress,
        ))
        return props

    def prop(
        self,
        data: object,
        property: str,
        *,
        text: str | None = None,
        expand: bool = False,
    ) -> None:
        """Append a property widget.

        Currently only ``ENUM`` properties with ``expand=True`` are
        implemented.  Other property types are rendered as a stub label.
        """
        try:
            prop_rna = None
            # Strategy 1: direct bl_rna.properties (works for PropertyGroup,
            # AddonPreferences, etc.)
            cls = type(data)
            bl_rna = getattr(cls, "bl_rna", None)
            if bl_rna is not None:
                props_coll = getattr(bl_rna, "properties", None)
                if props_coll is not None and property in props_coll:
                    prop_rna = props_coll[property]

            # Strategy 2: operator .properties sub-struct
            if prop_rna is None and hasattr(data, "properties"):
                op_props = data.properties
                op_bl_rna = getattr(type(op_props), "bl_rna", None)
                if op_bl_rna is None:
                    op_bl_rna = getattr(op_props, "bl_rna", None)
                if op_bl_rna is not None:
                    op_props_coll = getattr(op_bl_rna, "properties", None)
                    if op_props_coll is not None and property in op_props_coll:
                        prop_rna = op_props_coll[property]

            if prop_rna is None:
                label_text = text if text is not None else property
                self.label(text=label_text)
                return

            prop_type = prop_rna.type
        except Exception as exc:
            _logger.log(
                f"prop() bl_rna lookup failed for {property!r} on "
                f"{type(data).__name__}: {exc}",
            )
            label_text = text if text is not None else property
            self.label(text=label_text)
            return

        if prop_type == "ENUM" and expand:
            try:
                items = [
                    (item.identifier, item.name, item.description, item.icon)
                    for item in prop_rna.enum_items
                ]
            except Exception:  # noqa: BLE001
                items = []

            # Dynamic enum callbacks (items=func) are not pre-populated
            # in prop_rna.enum_items — resolve them from the annotation.
            if not items:
                items = _resolve_dynamic_enum(data, property)

            if not items:
                label_text = text if text is not None else property
                self.label(text=label_text)
                return
            active_value = getattr(data, property, "")
            self._children.append(GpuEnumButtons(
                items=items,
                active_value=active_value,
                data=data,
                property_name=property,
                enabled=self.enabled,
                alert=self.alert,
            ))
        elif prop_type == "STRING":
            if text is None:
                prefix = getattr(prop_rna, "name", property)
            else:
                prefix = text
            self._children.append(GpuTextField(
                data=data,
                property_name=property,
                prefix_text=prefix,
                textedit_update=_has_textedit_update(data, property),
                enabled=self.enabled,
                alert=self.alert,
            ))
        else:
            # Unsupported property type — render a stub label.
            label_text = text if text is not None else property
            self.label(text=label_text)

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

    def template_icon(
        self,
        *,
        icon_value: int = 0,
        scale: float = 1.0,
    ) -> None:
        """Add a large preview image.

        Mirrors ``UILayout.template_icon(icon_value=..., scale=...)``.
        The *icon_value* is an integer preview-collection icon ID that
        the panel resolves to a GPU texture.
        """
        self._children.append(GpuTemplateIcon(
            icon_value=icon_value,
            scale=scale,
        ))

    def template_list(
        self,
        listtype_name: str,
        list_id: str,
        dataptr: object,
        propname: str,
        active_dataptr: object,
        active_propname: str,
        *,
        rows: int = 5,
        maxrows: int = 5,
        cols: int = 1,
        cell_height: int | None = None,
        **kwargs: object,
    ) -> None:
        """Append a scrollable list/grid drawn by a registered callback.

        Mirrors ``UILayout.template_list()``.  The *listtype_name* must
        have been registered via :meth:`GpuPanel.register_list_drawer`
        before the build function runs.

        Parameters
        ----------
        cols:
            Number of columns.  ``1`` (default) gives a single-column
            scrollable list.  Values > 1 produce a card grid.
        cell_height:
            Per-cell height in base (unscaled) pixels.  Defaults to
            ``WIDGET_HEIGHT`` for single-column lists.
        """
        from .constants import WIDGET_HEIGHT

        draw_fn = self._panel._list_drawers.get(listtype_name)
        if draw_fn is None:
            _logger.log(
                f"template_list: no drawer registered for {listtype_name!r}",
            )
        effective_height = cell_height if cell_height is not None else WIDGET_HEIGHT
        self._children.append(GpuGridList(
            list_id=list_id,
            cols=cols,
            rows_visible=rows,
            cell_height=effective_height,
            dataptr=dataptr,
            propname=propname,
            active_dataptr=active_dataptr,
            active_propname=active_propname,
            draw_fn=draw_fn,
        ))

    # -- Measure pass (bottom-up) -------------------------------------------

    def _child_height(self, child: GpuLayout | GpuWidget, s: float) -> float:
        """Return the measured height of a single child."""
        if isinstance(child, GpuWidget):
            return child.measure_height(s)
        return child._measure_height(s) * child.scale_y

    @staticmethod
    def _is_separator(child: GpuLayout | GpuWidget) -> bool:
        """Return ``True`` if *child* acts as a separator for gap logic."""
        if isinstance(child, GpuWidget):
            return child.is_separator
        return False

    @staticmethod
    def _gap_before(
        children: list[GpuLayout | GpuWidget], index: int,
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
            if isinstance(child, GpuWidget) and child.is_separator:
                sep_w += child.measure_height(s)
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

            if isinstance(child, GpuWidget) and child.is_separator:
                cursor_x += child.measure_height(s)
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
    ) -> list[list[GpuLayout | GpuWidget]]:
        """Partition children into rows of *cols* items each."""
        rows: list[list[GpuLayout | GpuWidget]] = []
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
                if child.rect is not None:
                    child.draw(s, self.enabled, self._panel)

    # -- Event handling ------------------------------------------------------

    def handle_event(self, event_type: str, panel: object, **kwargs) -> bool:
        """Handle a dispatched event.  Return ``True`` if consumed.

        Layouts do not consume events by default.  Subclasses or future
        container widgets may override this.
        """
        return False
