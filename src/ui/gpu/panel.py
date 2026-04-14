"""Top-level panel and hit-testing for the GPU UI toolkit."""

from __future__ import annotations

from typing import Any, Callable

import bpy
import gpu

from .constants import get_ui_scale, scaled, PANEL_PAD
from .drawing import draw_rect_outline, draw_rect_rounded
from .dropdown import DropdownState
from .grid_list import ScrollState
from ._hit import EventResult, HitResult
from .text_edit import TextEditState
from .icons import IconProvider
from .layout import GpuLayout
from .theme import get_theme
from ._logger import _logger


# ---------------------------------------------------------------------------
# Region helpers
# ---------------------------------------------------------------------------


def get_region_offsets(area: Any) -> tuple[int, int]:
    """Return ``(offset_x, offset_y)`` to clear toolbar and header overlays.

    The 3D viewport's TOOLS, HEADER, and TOOL_HEADER regions overlay the
    WINDOW region, so ``POST_PIXEL`` drawing at ``(0, 0)`` sits behind
    them.  This helper inspects the area's regions and returns pixel
    offsets that push content past those overlays.
    """
    offset_x = 0
    offset_y = 0
    for r in area.regions:
        if r.type == "TOOLS":
            offset_x = max(offset_x, r.width)
        elif r.type in {"HEADER", "TOOL_HEADER"}:
            offset_y += r.height
    return offset_x, offset_y


# ---------------------------------------------------------------------------
# GpuPanel
# ---------------------------------------------------------------------------


class GpuPanel:
    """Top-level owner of a GPU-drawn UI surface.

    Manages the ``POST_PIXEL`` draw handler lifecycle, drives the
    per-frame build -> layout -> draw pipeline, and owns the hit-test
    registry and texture cache.
    """

    def __init__(
        self,
        width: int,
        anchor: tuple[int, int] | Callable[[], tuple[int, int]] | None = None,
        build_fn: Callable[[GpuLayout], None] | None = None,
    ) -> None:
        self._width = width
        self._anchor = anchor
        self._build_fn = build_fn

        self._root: GpuLayout | None = None
        self._hit_rects: list[HitResult] = []
        self._handle: object | None = None
        self._area: object | None = None
        self._texture_cache: dict[str, object] = {}
        self._ui_scale: float = 1.0
        self._panel_rect: tuple[float, float, float, float] | None = None
        self._mouse_pos: tuple[float, float] | None = None

        # Text field editing state (cursor, selection, clipboard, etc.).
        self._text_edit = TextEditState()

        # Icon provider (lazy-loaded atlas of built-in Blender icons).
        self._icon_provider: IconProvider = IconProvider()

        # Preview path registry: icon_value → image file path.
        self._preview_paths: dict[int, str] = {}

        # List drawer registry: listtype_name → draw callback.
        self._list_drawers: dict[str, Callable] = {}

        # Scroll state per list widget, keyed by list_id.
        self._scroll_states: dict[str, ScrollState] = {}

        # Visual selection per list widget, keyed by list_id.
        # Separate from the data-model index so that property update
        # callbacks (which may reset the index) don't clear the highlight.
        self._list_selections: dict[str, int] = {}

        # Dropdown overlay state (like active_text_field for text fields).
        self.active_dropdown: DropdownState | None = None

        # Widget-type click handlers.  ``operator``, ``prop``, and
        # ``list_row`` are pre-registered; callers may override or add
        # more via :meth:`register_widget_handler`.
        self._widget_handlers: dict[str, Callable[[HitResult], EventResult]] = {
            "operator": self._handle_operator_hit,
            "prop": self._handle_prop_hit,
            "list_row": self._dispatch_list_row,
        }

    # -- Lifecycle -----------------------------------------------------------

    def attach(self, area: Any) -> None:
        """Register the ``POST_PIXEL`` draw handler on *area*'s WINDOW region."""
        self._area = area
        self._handle = bpy.types.SpaceView3D.draw_handler_add(
            self._draw_callback, (), "WINDOW", "POST_PIXEL",
        )

    def detach(self) -> None:
        """Remove the draw handler and release all resources."""
        if self._handle is not None:
            bpy.types.SpaceView3D.draw_handler_remove(
                self._handle, "WINDOW",
            )
            self._handle = None
        self._area = None
        self._root = None
        self._hit_rects.clear()
        self._texture_cache.clear()
        self._panel_rect = None
        self._mouse_pos = None
        self._text_edit.reset()
        self._scroll_states.clear()
        self.active_dropdown = None

    def update_mouse(self, mx: float, my: float) -> None:
        """Store the latest mouse position for hover detection."""
        self._mouse_pos = (mx, my)

    # -- Frame cycle ---------------------------------------------------------

    def begin_frame(self) -> GpuLayout:
        """Clear the widget tree, reset hit rects, return the root layout."""
        self._ui_scale = get_ui_scale()
        self._hit_rects.clear()
        self._text_edit.reset_frame()
        self._root = GpuLayout(self, direction="COLUMN")
        return self._root

    def end_frame(self) -> None:
        """Run the layout pass then the draw pass."""
        if self._root is None:
            return

        s = self._ui_scale
        pad = scaled(PANEL_PAD, s)
        w = scaled(self._width, s)
        h = self._root._measure_height(s) + pad * 2

        # Determine anchor (top-left of panel in region pixels).
        anchor = self._anchor
        if callable(anchor):
            anchor = anchor()
        if anchor is not None:
            ax = float(anchor[0])
            ay = float(anchor[1])
        else:
            try:
                region = bpy.context.region
                ax = (region.width - w) / 2
                ay = (region.height + h) / 2
            except Exception as exc:
                _logger.log(f"region fallback anchor failed: {exc}")
                ax, ay = 0.0, h

        # Panel rect: (x, y) is bottom-left.
        panel_x = ax
        panel_y = ay - h
        self._panel_rect = (panel_x, panel_y, w, h)

        # Position pass then draw pass.
        self._root._position(
            panel_x + pad, panel_y + pad, w - pad * 2, h - pad * 2, s,
        )

        # Panel background.
        theme = get_theme()
        r = scaled(6.0, s)
        draw_rect_rounded(panel_x, panel_y, w, h, r, theme.panel_bg)
        draw_rect_outline(panel_x, panel_y, w, h, theme.border, thickness=1)

        self._root._draw(s)

        # Dropdown overlay — drawn last so it renders on top of everything.
        if self.active_dropdown is not None:
            self.active_dropdown.draw(s, self)

    # -- Internal draw handler -----------------------------------------------

    def _draw_callback(self) -> None:
        """Entry point called by Blender's draw-handler machinery."""
        gpu.state.blend_set("ALPHA")
        try:
            root = self.begin_frame()
            if self._build_fn is not None:
                self._build_fn(root)
            self.end_frame()
        finally:
            gpu.state.blend_set("NONE")

    # -- Public widget accessors ---------------------------------------------

    def get_mouse_pos(self) -> tuple[float, float] | None:
        """Return the current mouse position, or ``None`` if unknown."""
        return self._mouse_pos

    def get_list_selection(self, list_id: str) -> int:
        """Return the selected index for *list_id*, or ``-1``."""
        return self._list_selections.get(list_id, -1)

    # -- Hit testing ---------------------------------------------------------

    def register_hit(self, hit: HitResult) -> None:
        """Register a clickable region for hit testing."""
        self._hit_rects.append(hit)

    def hit_test(self, mx: int, my: int) -> HitResult | None:
        """Return the most specific interactive widget at *(mx, my)*.

        When multiple hit rects overlap (e.g. an icon button inside a
        list row), the smallest one wins so that child widgets take
        priority over their parent containers.  Among equal-size rects
        the last registered one wins (topmost / latest).
        """
        best: HitResult | None = None
        best_area = float("inf")
        for hr in self._hit_rects:
            rx, ry, rw, rh = hr.rect
            if rx <= mx <= rx + rw and ry <= my <= ry + rh:
                area = rw * rh
                if area <= best_area:
                    best = hr
                    best_area = area
        return best

    def is_inside(self, mx: int, my: int) -> bool:
        """Return ``True`` if *(mx, my)* is within the panel bounding box."""
        if self._panel_rect is None:
            return False
        px, py, pw, ph = self._panel_rect
        return px <= mx <= px + pw and py <= my <= py + ph

    # -- Text field editing (delegated to TextEditState) ---------------------

    def activate_text_field(self, property_name: str, data: object) -> None:
        """Activate a text field for editing (cursor at end, select all)."""
        self._text_edit.activate(property_name, data)

    def confirm_text_field(self) -> None:
        """Confirm and deactivate the current text field."""
        self._text_edit.confirm()

    def cancel_text_field(self) -> None:
        """Restore original value and deactivate."""
        self._text_edit.cancel()

    def tab_text_field(self) -> None:
        """Confirm current field and activate the next one (cyclic)."""
        self._text_edit.tab()

    # -- Dropdown overlay ----------------------------------------------------

    def open_dropdown(self, state: DropdownState) -> None:
        """Open a dropdown overlay."""
        self.active_dropdown = state

    def close_dropdown(self) -> None:
        """Close the active dropdown overlay."""
        self.active_dropdown = None

    # -- Widget handler registry ---------------------------------------------

    def register_widget_handler(
        self,
        widget_type: str,
        handler: Callable[[HitResult], EventResult],
    ) -> None:
        """Register or override a handler for clicks on *widget_type*.

        ``"operator"``, ``"prop"``, and ``"list_row"`` have default
        handlers registered at construction time.  Call this to override
        them or to add handlers for custom widget types (e.g.
        ``"icon_button"``).
        """
        self._widget_handlers[widget_type] = handler

    # -- High-level event dispatch -------------------------------------------

    def handle_event(self, event: Any) -> EventResult:
        """Process a Blender modal event and return an :class:`EventResult`.

        This is the single entry point that modal operators should call
        from their ``modal()`` method.  It implements a three-state machine:

        1. **Dropdown active** — routes events to the open dropdown overlay.
        2. **Text field active** — routes events to the editing text field.
        3. **Normal** — handles scroll, ESC/RMB dismiss, and LMB
           widget dispatch.
        """
        self.update_mouse(
            getattr(event, "mouse_region_x", 0),
            getattr(event, "mouse_region_y", 0),
        )

        if self.active_dropdown is not None:
            return self._handle_dropdown_event(event)

        if self._text_edit.active_field is not None:
            return self._handle_text_event_mode(event)

        return self._handle_normal_event(event)

    # -- Dropdown mode -------------------------------------------------------

    def _handle_dropdown_event(self, event: Any) -> EventResult:
        dd = self.active_dropdown

        if event.type == "MOUSEMOVE":
            dd.hovered_index = dd.hit_test(
                event.mouse_region_x, event.mouse_region_y,
            )
            return EventResult(consumed=True, redraw=True)

        if event.type in {"ESC", "RIGHTMOUSE"} and event.value == "PRESS":
            self.close_dropdown()
            return EventResult(consumed=True, redraw=True)

        if event.type == "LEFTMOUSE" and event.value == "PRESS":
            idx = dd.hit_test(
                event.mouse_region_x, event.mouse_region_y,
            )
            if idx >= 0:
                dd.apply_selection(idx)
            self.close_dropdown()
            return EventResult(consumed=True, redraw=True)

        return EventResult(consumed=True)

    # -- Text field editing mode ---------------------------------------------

    def _handle_text_event_mode(self, event: Any) -> EventResult:
        te = self._text_edit
        # Drag selection: update on MOUSEMOVE, end on RELEASE.
        if te.dragging:
            if event.type == "MOUSEMOVE":
                te.update_drag(event.mouse_region_x)
                return EventResult(consumed=True, redraw=True)
            if event.type == "LEFTMOUSE" and event.value == "RELEASE":
                te.end_drag()
                return EventResult(consumed=True, redraw=True)

        # ESC / RMB cancel the text edit (not the panel).
        if event.type in {"ESC", "RIGHTMOUSE"} and event.value == "PRESS":
            te.cancel()
            return EventResult(consumed=True, redraw=True)

        # LMB: re-click on same field starts drag; otherwise confirm
        # the current field and fall through to normal click handling.
        if event.type == "LEFTMOUSE" and event.value == "PRESS":
            hit = self.hit_test(event.mouse_region_x, event.mouse_region_y)
            if (
                hit is not None
                and hit.widget_type == "text_field"
                and hit.id == te.active_field
            ):
                te.begin_drag(event.mouse_region_x, hit.rect)
                return EventResult(consumed=True, redraw=True)
            te.confirm()
            # Fall through to normal LMB handling.
            return self._handle_normal_event(event)

        # All other PRESS events are routed to the keystroke handler.
        if event.value == "PRESS":
            te.handle_keystroke(event)
            return EventResult(consumed=True, redraw=True)

        return EventResult(consumed=True)

    # -- Normal mode ---------------------------------------------------------

    def _handle_normal_event(self, event: Any) -> EventResult:
        # ESC / RMB dismiss the panel.
        if event.type in {"ESC", "RIGHTMOUSE"} and event.value == "PRESS":
            return EventResult(cancelled=True, redraw=True)

        # Scroll events → dispatch through widget tree.
        if (
            event.type in {"WHEELUPMOUSE", "WHEELDOWNMOUSE"}
            and event.value == "PRESS"
        ):
            ev = "SCROLL_UP" if event.type == "WHEELUPMOUSE" else "SCROLL_DOWN"
            self.dispatch_event(
                ev, event.mouse_region_x, event.mouse_region_y,
            )
            return EventResult(consumed=True, redraw=True)

        # LEFTMOUSE click — hit test and dispatch.
        if event.type == "LEFTMOUSE" and event.value == "PRESS":
            if not self.is_inside(
                event.mouse_region_x, event.mouse_region_y,
            ):
                return EventResult(cancelled=True, redraw=True)

            hit = self.hit_test(
                event.mouse_region_x, event.mouse_region_y,
            )
            if hit is None:
                return EventResult(consumed=True, redraw=True)

            return self._dispatch_hit(hit)

        # Unhandled events — still consumed to keep the modal alive.
        return EventResult(consumed=True, redraw=True)

    def _handle_operator_hit(self, hit: HitResult) -> EventResult:
        """Default handler: invoke a Blender operator from a hit."""
        try:
            parts = hit.id.split(".", 1)
            op_fn = getattr(bpy.ops, parts[0])
            op_fn = getattr(op_fn, parts[1])
            op_fn("INVOKE_DEFAULT", **hit.kwargs)
        except Exception:  # noqa: BLE001
            pass
        return EventResult(consumed=True)

    def _handle_prop_hit(self, hit: HitResult) -> EventResult:
        """Default handler: set a Blender property from a hit."""
        data = hit.kwargs.get("data")
        value = hit.kwargs.get("value")
        if data is not None and value is not None:
            try:
                setattr(data, hit.id, value)
            except Exception:  # noqa: BLE001
                pass
        return EventResult(consumed=True)

    def _dispatch_hit(self, hit: HitResult) -> EventResult:
        """Route a LEFTMOUSE hit to the appropriate handler.

        ``text_field`` and ``dropdown`` are handled inline because they
        transition the panel's modal state machine.  All other widget
        types are dispatched through :attr:`_widget_handlers`.
        """
        wt = hit.widget_type

        if wt == "text_field":
            self._text_edit.activate(hit.id, hit.kwargs["data"])
            return EventResult(consumed=True, redraw=True)

        if wt == "dropdown":
            state = DropdownState.from_hit(hit, self._ui_scale)
            self.open_dropdown(state)
            return EventResult(consumed=True, redraw=True)

        handler = self._widget_handlers.get(wt)
        if handler is not None:
            return handler(hit)

        return EventResult(consumed=True)

    def _dispatch_list_row(self, hit: HitResult) -> EventResult:
        """Handle a list_row click — set index with optional deselect toggle."""
        data = hit.kwargs.get("active_dataptr")
        prop = hit.kwargs.get("active_propname")
        idx = hit.kwargs.get("index")
        list_id = hit.kwargs.get("list_id")
        allow_deselect = hit.kwargs.get("allow_deselect", False)

        if (
            allow_deselect
            and list_id is not None
            and self._list_selections.get(list_id) == idx
        ):
            self._list_selections[list_id] = -1
            if data is not None and prop is not None:
                try:
                    setattr(data, prop, idx)
                except Exception:  # noqa: BLE001
                    pass
        else:
            if data is not None and prop is not None and idx is not None:
                try:
                    setattr(data, prop, idx)
                except Exception:  # noqa: BLE001
                    pass
            if list_id is not None and idx is not None:
                self._list_selections[list_id] = idx

        return EventResult(consumed=True, redraw=True)

    # -- Texture cache -------------------------------------------------------

    def get_texture(self, path: str) -> Any | None:
        """Load, cache, and return a GPU texture from *path*."""
        if path in self._texture_cache:
            return self._texture_cache[path]
        try:
            img = bpy.data.images.load(path, check_existing=True)
            texture = gpu.texture.from_image(img)
            self._texture_cache[path] = texture
            return texture
        except Exception as exc:
            _logger.log(f"get_texture() failed for {path!r}: {exc}")
            self._texture_cache[path] = None
            return None

    # -- Preview image support -----------------------------------------------

    def register_preview(self, icon_value: int, path: str) -> None:
        """Associate a preview *icon_value* with an image file *path*.

        Call this during the build function for every preview that will be
        referenced by :meth:`GpuLayout.template_icon`.  The path is loaded
        as a GPU texture on first use and cached for future frames.
        """
        self._preview_paths[icon_value] = path

    def get_preview_texture(self, icon_value: int) -> Any | None:
        """Return the GPU texture for *icon_value*, or ``None``."""
        path = self._preview_paths.get(icon_value)
        if path is None:
            return None
        return self.get_texture(path)

    # -- List drawer registry ------------------------------------------------

    def register_list_drawer(
        self, listtype_name: str, draw_fn: Callable,
    ) -> None:
        """Register a list-item draw callback for *listtype_name*.

        The callback signature is::

            draw_fn(layout: GpuLayout, item, index: int, is_active: bool)

        This mirrors how ``UIList.draw_item()`` works but uses
        :class:`GpuLayout` instead of ``UILayout``.
        """
        self._list_drawers[listtype_name] = draw_fn

    # -- Scroll state --------------------------------------------------------

    def get_scroll_state(self, list_id: str) -> ScrollState:
        """Return the :class:`ScrollState` for *list_id*, creating if needed."""
        if list_id not in self._scroll_states:
            self._scroll_states[list_id] = ScrollState()
        return self._scroll_states[list_id]

    # -- Event dispatching (bubbling) ----------------------------------------

    def dispatch_event(
        self,
        event_type: str,
        mx: float,
        my: float,
        **kwargs: Any,
    ) -> bool:
        """Dispatch *event_type* through the widget tree with bubbling.

        Finds the deepest widget under ``(mx, my)`` and propagates the
        event upward through parent layouts until a handler consumes it
        (returns ``True``) or the root is reached.

        Returns ``True`` if the event was consumed.
        """
        if self._root is None:
            return False
        path: list[Any] = []
        self._build_hit_path(self._root, mx, my, path)
        for node in reversed(path):
            handler = getattr(node, "handle_event", None)
            if handler is not None and handler(event_type, panel=self, **kwargs):
                return True
        return False

    def _build_hit_path(
        self,
        node: Any,
        mx: float,
        my: float,
        path: list[Any],
    ) -> bool:
        """Recursively build the ancestor path to the deepest node at *(mx, my)*.

        Appends nodes from root toward leaves; callers reverse for bubbling.
        Returns ``True`` if *node* contains the point.
        """
        from .widget import GpuWidget

        if isinstance(node, GpuLayout):
            rect = node._rect
        elif isinstance(node, GpuWidget):
            rect = node.rect
        else:
            return False

        if rect is None:
            return False

        x, y, w, h = rect
        if not (x <= mx <= x + w and y <= my <= y + h):
            return False

        path.append(node)

        # Descend into layout children (reverse order = front-to-back).
        if isinstance(node, GpuLayout):
            for child in reversed(node._children):
                if self._build_hit_path(child, mx, my, path):
                    break  # Found the deepest child on this branch.

        return True
