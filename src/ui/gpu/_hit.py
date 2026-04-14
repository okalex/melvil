"""Hit-testing and event-result dataclasses for the GPU UI toolkit.

These are defined in their own module so that widgets can import them
without a circular dependency on :mod:`.panel`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class HitResult:
    """Describes the interactive widget found by :meth:`GpuPanel.hit_test`."""

    widget_type: str  # "operator", "prop", "list_row", "button", "text_field"
    id: str
    kwargs: dict[str, Any]
    rect: tuple[float, float, float, float]  # (x, y, w, h)


@dataclass
class EventResult:
    """Structured return value from :meth:`GpuPanel.handle_event`.

    ``consumed``
        ``True`` when the panel handled the event and the caller should
        return ``RUNNING_MODAL``.
    ``cancelled``
        ``True`` when the user dismissed the panel (ESC, RMB, or click
        outside).  The caller should clean up and return ``CANCELLED``.
    ``redraw``
        ``True`` when the panel needs a visual update.
    """

    consumed: bool = False
    cancelled: bool = False
    redraw: bool = False
