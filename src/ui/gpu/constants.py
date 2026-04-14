"""Layout constants and DPI helpers for the GPU UI toolkit."""

from __future__ import annotations

import bpy


# ---------------------------------------------------------------------------
# Layout constants (base values at ui_scale 1.0)
# ---------------------------------------------------------------------------

WIDGET_HEIGHT = 20
WIDGET_GAP = 4
WIDGET_GAP_ALIGNED = 1
WIDGET_PAD_X = 6
BOX_PAD = 8
PANEL_PAD = 8
SEPARATOR_HEIGHT = 8

FONT_ID = 0
FONT_SIZE_PRIMARY = 11
FONT_SIZE_SECONDARY = 10
ICON_SIZE = 12

SCROLLBAR_WIDTH = 8
SCROLLBAR_MIN_HEIGHT = 20


# ---------------------------------------------------------------------------
# DPI helpers
# ---------------------------------------------------------------------------

def get_ui_scale() -> float:
    """Return Blender's current UI scale factor.

    Returns 1.0 when ``bpy.context`` is unavailable (test environments).
    """
    try:
        return bpy.context.preferences.system.ui_scale
    except Exception as exc:  # noqa: F841 — logged only when GPU_UI_LOG=1
        return 1.0


def scaled(px: float, ui_scale: float) -> float:
    """Scale a pixel value by the given UI scale factor."""
    return px * ui_scale
