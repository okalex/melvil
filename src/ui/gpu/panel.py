"""Top-level panel and hit-testing for the GPU UI toolkit."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable

import bpy
import gpu

from .constants import get_ui_scale, scaled, PANEL_PAD
from .drawing import draw_rect_outline, draw_rect_rounded
from .layout import GpuLayout
from .theme import get_theme
from ._logger import _logger


# ---------------------------------------------------------------------------
# Hit testing
# ---------------------------------------------------------------------------


@dataclass
class HitResult:
    """Describes the interactive widget found by :meth:`GpuPanel.hit_test`."""

    widget_type: str  # "operator", "prop", "list_row", "button", "text_field"
    id: str
    kwargs: dict[str, Any]
    rect: tuple[float, float, float, float]  # (x, y, w, h)


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

        # Text field focus state.
        self.active_text_field: str | None = None
        self.text_cursor_pos: int = 0
        self._text_selection_start: int | None = None
        self._text_original_value: str = ""
        self._text_buffer: str | None = None
        self._text_blink_base: float = 0.0
        self._active_text_data: object | None = None
        self._text_field_order: list[str] = []
        self._text_field_data: dict[str, object] = {}
        self._textedit_update_fields: set[str] = set()

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
        self._deactivate_text_field()
        self._text_field_order.clear()
        self._text_field_data.clear()
        self._textedit_update_fields.clear()

    def update_mouse(self, mx: float, my: float) -> None:
        """Store the latest mouse position for hover detection."""
        self._mouse_pos = (mx, my)

    # -- Frame cycle ---------------------------------------------------------

    def begin_frame(self) -> GpuLayout:
        """Clear the widget tree, reset hit rects, return the root layout."""
        self._ui_scale = get_ui_scale()
        self._hit_rects.clear()
        self._text_field_order.clear()
        self._text_field_data.clear()
        self._textedit_update_fields.clear()
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

    # -- Hit testing ---------------------------------------------------------

    def hit_test(self, mx: int, my: int) -> HitResult | None:
        """Return the topmost interactive widget at region-local *(mx, my)*."""
        for hr in reversed(self._hit_rects):
            rx, ry, rw, rh = hr.rect
            if rx <= mx <= rx + rw and ry <= my <= ry + rh:
                return hr
        return None

    def is_inside(self, mx: int, my: int) -> bool:
        """Return ``True`` if *(mx, my)* is within the panel bounding box."""
        if self._panel_rect is None:
            return False
        px, py, pw, ph = self._panel_rect
        return px <= mx <= px + pw and py <= my <= py + ph

    # -- Text field editing --------------------------------------------------

    def activate_text_field(self, property_name: str, data: object) -> None:
        """Activate a text field for editing (cursor at end, select all)."""
        if self.active_text_field is not None:
            self.confirm_text_field()
        self.active_text_field = property_name
        self._active_text_data = data
        current = str(getattr(data, property_name, ""))
        self._text_original_value = current
        self._text_buffer = current
        self.text_cursor_pos = len(current)
        self._text_selection_start = 0  # Select all.
        self._text_blink_base = time.monotonic()

    def confirm_text_field(self) -> None:
        """Confirm and deactivate the current text field."""
        if self.active_text_field is None:
            return
        # For non-TEXTEDIT_UPDATE fields, write the final value now.
        if (self._active_text_data is not None
                and self._text_buffer is not None
                and self.active_text_field not in self._textedit_update_fields):
            try:
                setattr(
                    self._active_text_data,
                    self.active_text_field,
                    self._text_buffer,
                )
            except Exception:  # noqa: BLE001
                pass
        self._deactivate_text_field()

    def cancel_text_field(self) -> None:
        """Restore original value and deactivate."""
        if self.active_text_field is not None and self._active_text_data is not None:
            try:
                setattr(
                    self._active_text_data,
                    self.active_text_field,
                    self._text_original_value,
                )
            except Exception:  # noqa: BLE001
                pass
        self._deactivate_text_field()

    def tab_text_field(self) -> None:
        """Confirm current field and activate the next one (cyclic)."""
        if not self._text_field_order:
            self.confirm_text_field()
            return
        current = self.active_text_field
        self.confirm_text_field()
        if current in self._text_field_order:
            idx = self._text_field_order.index(current)
            next_idx = (idx + 1) % len(self._text_field_order)
        else:
            next_idx = 0
        next_name = self._text_field_order[next_idx]
        next_data = self._text_field_data.get(next_name)
        if next_data is not None:
            self.activate_text_field(next_name, next_data)

    def handle_text_event(self, event: Any) -> bool:
        """Process a keyboard event for the active text field.

        Returns ``True`` if the event was consumed.
        """
        if self.active_text_field is None or self._text_buffer is None:
            return False
        if event.value != "PRESS":
            return False

        text = self._text_buffer

        # --- Confirm / cancel / tab -----------------------------------------
        if event.type in {"RET", "NUMPAD_ENTER"}:
            self.confirm_text_field()
            return True
        if event.type == "ESC":
            self.cancel_text_field()
            return True
        if event.type == "TAB":
            self.tab_text_field()
            return True

        # --- Ctrl shortcuts -------------------------------------------------
        ctrl = getattr(event, "ctrl", False)
        if ctrl:
            if event.type == "V":
                self._paste_clipboard()
                return True
            if event.type == "A":
                self._text_selection_start = 0
                self.text_cursor_pos = len(text)
                return True
            return True  # Consume all Ctrl+key to prevent shortcuts.

        # --- Deletion -------------------------------------------------------
        if event.type == "BACK_SPACE":
            self._handle_delete_back()
            return True
        if event.type == "DEL":
            self._handle_delete_forward()
            return True

        # --- Cursor movement ------------------------------------------------
        if event.type == "LEFT_ARROW":
            self._text_selection_start = None
            if self.text_cursor_pos > 0:
                self.text_cursor_pos -= 1
            self._reset_blink()
            return True
        if event.type == "RIGHT_ARROW":
            self._text_selection_start = None
            if self.text_cursor_pos < len(text):
                self.text_cursor_pos += 1
            self._reset_blink()
            return True
        if event.type == "HOME":
            self._text_selection_start = None
            self.text_cursor_pos = 0
            self._reset_blink()
            return True
        if event.type == "END":
            self._text_selection_start = None
            self.text_cursor_pos = len(text)
            self._reset_blink()
            return True

        # --- Printable character --------------------------------------------
        unicode_char = getattr(event, "unicode", "")
        if unicode_char and unicode_char.isprintable():
            self._insert_text(unicode_char)
            return True

        return False

    # -- Text field helpers (private) ----------------------------------------

    def _deactivate_text_field(self) -> None:
        self.active_text_field = None
        self._active_text_data = None
        self._text_buffer = None
        self._text_selection_start = None

    def _delete_selection(self) -> str | None:
        """Delete selected text and return the new string, or ``None``."""
        if self._text_selection_start is None or self._text_buffer is None:
            return None
        sel_start = min(self._text_selection_start, self.text_cursor_pos)
        sel_end = max(self._text_selection_start, self.text_cursor_pos)
        if sel_start == sel_end:
            self._text_selection_start = None
            return None
        new_text = self._text_buffer[:sel_start] + self._text_buffer[sel_end:]
        self.text_cursor_pos = sel_start
        self._text_selection_start = None
        return new_text

    def _insert_text(self, chars: str) -> None:
        if self._text_buffer is None:
            return
        result = self._delete_selection()
        text = result if result is not None else self._text_buffer
        new_text = text[:self.text_cursor_pos] + chars + text[self.text_cursor_pos:]
        self.text_cursor_pos += len(chars)
        self._apply_text(new_text)

    def _handle_delete_back(self) -> None:
        if self._text_buffer is None:
            return
        result = self._delete_selection()
        if result is not None:
            self._apply_text(result)
        elif self.text_cursor_pos > 0:
            new = (self._text_buffer[:self.text_cursor_pos - 1]
                   + self._text_buffer[self.text_cursor_pos:])
            self.text_cursor_pos -= 1
            self._apply_text(new)

    def _handle_delete_forward(self) -> None:
        if self._text_buffer is None:
            return
        result = self._delete_selection()
        if result is not None:
            self._apply_text(result)
        elif self.text_cursor_pos < len(self._text_buffer):
            new = (self._text_buffer[:self.text_cursor_pos]
                   + self._text_buffer[self.text_cursor_pos + 1:])
            self._apply_text(new)

    def _paste_clipboard(self) -> None:
        try:
            clipboard = bpy.context.window_manager.clipboard
        except Exception:  # noqa: BLE001
            return
        if clipboard:
            # Single-line field — strip newlines.
            clipboard = clipboard.replace("\n", "").replace("\r", "")
            self._insert_text(clipboard)

    def _apply_text(self, new_text: str) -> None:
        """Update the text buffer and optionally the property."""
        self._text_buffer = new_text
        self._reset_blink()
        if (self.active_text_field in self._textedit_update_fields
                and self._active_text_data is not None):
            try:
                setattr(
                    self._active_text_data,
                    self.active_text_field,
                    new_text,
                )
            except Exception:  # noqa: BLE001
                pass

    def _reset_blink(self) -> None:
        self._text_blink_base = time.monotonic()

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
