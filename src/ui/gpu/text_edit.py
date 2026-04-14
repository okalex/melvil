"""Text field editing state for the GPU UI toolkit.

Extracted from :class:`UiContext` so that the panel class stays focused on
layout, rendering, and event routing.  The panel owns a single
:class:`TextEditState` instance and delegates text-editing work to it.
"""

from __future__ import annotations

import time
from typing import Any

import bpy

from .constants import FONT_SIZE_PRIMARY, WIDGET_PAD_X, get_ui_scale, scaled
from .drawing import measure_text


class TextEditState:
    """Manages all text field editing state and operations.

    State attributes are public so that :class:`GpuTextField` can read
    them during its draw pass (e.g. ``buffer``, ``cursor_pos``,
    ``selection_start``, ``blink_base``).
    """

    def __init__(self) -> None:
        # Active field identity.
        self.active_field: str | None = None
        self.data: object | None = None

        # Editing buffer and cursor.
        self.cursor_pos: int = 0
        self.selection_start: int | None = None
        self.original_value: str = ""
        self.buffer: str | None = None
        self.blink_base: float = 0.0

        # Per-frame registration (populated during draw, cleared each frame).
        self.field_order: list[str] = []
        self.field_data: dict[str, object] = {}
        self.textedit_update_fields: set[str] = set()

        # Drag selection state.
        self.dragging: bool = False
        self.drag_field_rect: tuple[float, float, float, float] | None = None

    # -- Activation / deactivation ------------------------------------------

    def activate(self, property_name: str, data: object) -> None:
        """Activate a text field for editing (cursor at end, select all)."""
        if self.active_field is not None:
            self.confirm()
        self.active_field = property_name
        self.data = data
        current = str(getattr(data, property_name, ""))
        self.original_value = current
        self.buffer = current
        self.cursor_pos = len(current)
        self.selection_start = 0  # Select all.
        self.blink_base = time.monotonic()

    def deactivate(self) -> None:
        """Clear all editing state."""
        self.active_field = None
        self.data = None
        self.buffer = None
        self.selection_start = None

    def confirm(self) -> None:
        """Confirm and deactivate the current text field."""
        if self.active_field is None:
            return
        # For non-TEXTEDIT_UPDATE fields, write the final value now.
        if (self.data is not None
                and self.buffer is not None
                and self.active_field not in self.textedit_update_fields):
            try:
                setattr(self.data, self.active_field, self.buffer)
            except Exception:  # noqa: BLE001
                pass
        self.deactivate()

    def cancel(self) -> None:
        """Restore original value and deactivate."""
        if self.active_field is not None and self.data is not None:
            try:
                setattr(self.data, self.active_field, self.original_value)
            except Exception:  # noqa: BLE001
                pass
        self.deactivate()

    def tab(self) -> None:
        """Confirm current field and activate the next one (cyclic)."""
        if not self.field_order:
            self.confirm()
            return
        current = self.active_field
        self.confirm()
        if current in self.field_order:
            idx = self.field_order.index(current)
            next_idx = (idx + 1) % len(self.field_order)
        else:
            next_idx = 0
        next_name = self.field_order[next_idx]
        next_data = self.field_data.get(next_name)
        if next_data is not None:
            self.activate(next_name, next_data)

    # -- Cursor / drag selection --------------------------------------------

    def place_cursor_from_click(
        self, mouse_x: float, field_rect: tuple[float, float, float, float],
    ) -> None:
        """Move the cursor to the character closest to *mouse_x*."""
        if self.buffer is None:
            return
        idx = self._cursor_index_from_x(mouse_x, field_rect)
        self.cursor_pos = idx
        self.selection_start = None
        self.blink_base = time.monotonic()

    def begin_drag(
        self, mouse_x: float, field_rect: tuple[float, float, float, float],
    ) -> None:
        """Start a drag selection at the character closest to *mouse_x*."""
        if self.buffer is None:
            return
        idx = self._cursor_index_from_x(mouse_x, field_rect)
        self.cursor_pos = idx
        self.selection_start = idx
        self.dragging = True
        self.drag_field_rect = field_rect
        self.blink_base = time.monotonic()

    def update_drag(self, mouse_x: float) -> None:
        """Extend the drag selection to the character closest to *mouse_x*."""
        if not self.dragging or self.drag_field_rect is None:
            return
        if self.buffer is None:
            return
        idx = self._cursor_index_from_x(mouse_x, self.drag_field_rect)
        self.cursor_pos = idx
        self.blink_base = time.monotonic()

    def end_drag(self) -> None:
        """Finish a drag selection."""
        self.dragging = False
        self.drag_field_rect = None
        if self.selection_start == self.cursor_pos:
            self.selection_start = None

    def _cursor_index_from_x(
        self, mouse_x: float, field_rect: tuple[float, float, float, float],
    ) -> int:
        """Return the character index closest to *mouse_x*."""
        s = get_ui_scale()
        pad = scaled(WIDGET_PAD_X, s)
        font_size = scaled(FONT_SIZE_PRIMARY, s)
        text = self.buffer or ""
        fx = field_rect[0] + pad
        rel_x = mouse_x - fx

        best_idx = 0
        for i in range(1, len(text) + 1):
            char_x = measure_text(text[:i], font_size)[0]
            if char_x <= rel_x:
                best_idx = i
            else:
                prev_x = measure_text(text[:i - 1], font_size)[0] if i > 1 else 0.0
                if rel_x - prev_x > char_x - rel_x:
                    best_idx = i
                break
        return best_idx

    # -- Keyboard handling --------------------------------------------------

    def handle_keystroke(self, event: Any) -> bool:
        """Process a keyboard event for the active text field.

        Returns ``True`` if the event was consumed.
        """
        if self.active_field is None or self.buffer is None:
            return False
        if event.value != "PRESS":
            return False

        text = self.buffer

        # --- Confirm / cancel / tab -----------------------------------------
        if event.type in {"RET", "NUMPAD_ENTER"}:
            self.confirm()
            return True
        if event.type == "ESC":
            self.cancel()
            return True
        if event.type == "TAB":
            self.tab()
            return True

        # --- Ctrl shortcuts -------------------------------------------------
        ctrl = getattr(event, "ctrl", False)
        if ctrl:
            if event.type == "V":
                self._paste_clipboard()
                return True
            if event.type == "A":
                self.selection_start = 0
                self.cursor_pos = len(text)
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
            self.selection_start = None
            if self.cursor_pos > 0:
                self.cursor_pos -= 1
            self._reset_blink()
            return True
        if event.type == "RIGHT_ARROW":
            self.selection_start = None
            if self.cursor_pos < len(text):
                self.cursor_pos += 1
            self._reset_blink()
            return True
        if event.type == "HOME":
            self.selection_start = None
            self.cursor_pos = 0
            self._reset_blink()
            return True
        if event.type == "END":
            self.selection_start = None
            self.cursor_pos = len(text)
            self._reset_blink()
            return True

        # --- Printable character --------------------------------------------
        unicode_char = getattr(event, "unicode", "")
        if unicode_char and unicode_char.isprintable():
            self._insert_text(unicode_char)
            return True

        return False

    # -- Private helpers ----------------------------------------------------

    def _delete_selection(self) -> str | None:
        """Delete selected text and return the new string, or ``None``."""
        if self.selection_start is None or self.buffer is None:
            return None
        sel_start = min(self.selection_start, self.cursor_pos)
        sel_end = max(self.selection_start, self.cursor_pos)
        if sel_start == sel_end:
            self.selection_start = None
            return None
        new_text = self.buffer[:sel_start] + self.buffer[sel_end:]
        self.cursor_pos = sel_start
        self.selection_start = None
        return new_text

    def _insert_text(self, chars: str) -> None:
        if self.buffer is None:
            return
        result = self._delete_selection()
        text = result if result is not None else self.buffer
        new_text = text[:self.cursor_pos] + chars + text[self.cursor_pos:]
        self.cursor_pos += len(chars)
        self._apply_text(new_text)

    def _handle_delete_back(self) -> None:
        if self.buffer is None:
            return
        result = self._delete_selection()
        if result is not None:
            self._apply_text(result)
        elif self.cursor_pos > 0:
            new = (self.buffer[:self.cursor_pos - 1]
                   + self.buffer[self.cursor_pos:])
            self.cursor_pos -= 1
            self._apply_text(new)

    def _handle_delete_forward(self) -> None:
        if self.buffer is None:
            return
        result = self._delete_selection()
        if result is not None:
            self._apply_text(result)
        elif self.cursor_pos < len(self.buffer):
            new = (self.buffer[:self.cursor_pos]
                   + self.buffer[self.cursor_pos + 1:])
            self._apply_text(new)

    def _paste_clipboard(self) -> None:
        try:
            clipboard = bpy.context.window_manager.clipboard
        except Exception:  # noqa: BLE001
            return
        if clipboard:
            clipboard = clipboard.replace("\n", "").replace("\r", "")
            self._insert_text(clipboard)

    def _apply_text(self, new_text: str) -> None:
        """Update the text buffer and optionally the property."""
        self.buffer = new_text
        self._reset_blink()
        if (self.active_field in self.textedit_update_fields
                and self.data is not None):
            try:
                setattr(self.data, self.active_field, new_text)
            except Exception:  # noqa: BLE001
                pass

    def _reset_blink(self) -> None:
        self.blink_base = time.monotonic()

    # -- Frame lifecycle ----------------------------------------------------

    def reset_frame(self) -> None:
        """Clear per-frame registration state (called at begin_frame)."""
        self.field_order.clear()
        self.field_data.clear()
        self.textedit_update_fields.clear()

    def reset(self) -> None:
        """Full reset — deactivate and clear all registrations."""
        self.deactivate()
        self.field_order.clear()
        self.field_data.clear()
        self.textedit_update_fields.clear()
