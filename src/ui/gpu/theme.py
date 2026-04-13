"""Theme color management for the GPU UI toolkit."""

from __future__ import annotations

from dataclasses import dataclass

import bpy

from ._logger import _logger


# ---------------------------------------------------------------------------
# Theme colors
# ---------------------------------------------------------------------------

def _color_with_alpha(color, alpha: float) -> tuple[float, float, float, float]:
    """Return *color* with its alpha channel replaced by *alpha*."""
    return (color[0], color[1], color[2], alpha)


@dataclass(frozen=True)
class ThemeColors:
    """Snapshot of theme colors needed by the GPU UI toolkit.

    Use :meth:`from_blender` to read the current theme, or :meth:`fallback`
    for test environments where ``bpy.context`` is unavailable.
    """

    # Panel
    panel_bg: tuple[float, float, float, float]
    panel_header_bg: tuple[float, float, float, float]

    # Text
    text_primary: tuple[float, float, float, float]
    text_secondary: tuple[float, float, float, float]
    text_disabled: tuple[float, float, float, float]

    # Widget backgrounds
    widget_bg: tuple[float, float, float, float]
    widget_bg_hover: tuple[float, float, float, float]
    widget_bg_active: tuple[float, float, float, float]

    # Input fields
    input_bg: tuple[float, float, float, float]
    input_border: tuple[float, float, float, float]
    input_text: tuple[float, float, float, float]

    # Buttons
    button_bg: tuple[float, float, float, float]
    button_bg_hover: tuple[float, float, float, float]
    button_text: tuple[float, float, float, float]

    # List items
    list_item_bg: tuple[float, float, float, float]

    # Selection & highlights
    selection_bg: tuple[float, float, float, float]
    selection_text: tuple[float, float, float, float]

    # Alerts & accents
    alert: tuple[float, float, float, float]

    # Borders
    border: tuple[float, float, float, float]
    border_intense: tuple[float, float, float, float]

    # Scrollbar
    scrollbar_bg: tuple[float, float, float, float]
    scrollbar_handle: tuple[float, float, float, float]

    @classmethod
    def from_blender(cls) -> ThemeColors:
        """Read colors from the active Blender theme.

        Widget color attributes (``inner``, ``inner_sel``, ``text``,
        ``outline``, etc.) on ``ThemeWidgetColors`` are float RGBA arrays
        in the ``[0, 1]`` range in Blender's Python API, so no byte-to-float
        conversion is needed.
        """
        ui = bpy.context.preferences.themes[0].user_interface

        def _rgba(color) -> tuple[float, float, float, float]:
            r, g, b = float(color[0]), float(color[1]), float(color[2])
            try:
                a = float(color[3])
            except (IndexError, KeyError):
                a = 1.0
            return (r, g, b, a)

        text_primary = _rgba(ui.wcol_regular.text)
        menu_back = _rgba(ui.wcol_menu_back.inner)
        # Force full opacity — native popups render opaque regardless of
        # the theme alpha channel.
        panel_bg = (menu_back[0], menu_back[1], menu_back[2], 1.0)
        box_inner = _rgba(ui.wcol_box.inner)
        panel_header_bg = (box_inner[0], box_inner[1], box_inner[2],
                           min(1.0, box_inner[3] + 0.1))

        return cls(
            panel_bg=panel_bg,
            panel_header_bg=panel_header_bg,
            text_primary=text_primary,
            text_secondary=_color_with_alpha(text_primary, 0.6),
            text_disabled=_color_with_alpha(text_primary, 0.3),
            widget_bg=_rgba(ui.wcol_tool.inner),
            widget_bg_hover=_rgba(ui.wcol_tool.inner_sel),
            widget_bg_active=_rgba(ui.wcol_option.inner_sel),
            input_bg=_rgba(ui.wcol_text.inner),
            input_border=_rgba(ui.wcol_text.outline),
            input_text=_rgba(ui.wcol_text.text),
            button_bg=_rgba(ui.wcol_tool.inner),
            button_bg_hover=_rgba(ui.wcol_tool.inner_sel),
            button_text=_rgba(ui.wcol_tool.text),
            list_item_bg=(min(1.0, panel_bg[0] + 0.05),
                          min(1.0, panel_bg[1] + 0.05),
                          min(1.0, panel_bg[2] + 0.05),
                          1.0),
            selection_bg=_rgba(ui.wcol_list_item.inner_sel),
            selection_text=_rgba(ui.wcol_list_item.text_sel),
            alert=(1.0, 0.2, 0.2, 1.0),
            border=_rgba(ui.wcol_regular.outline),
            border_intense=(min(1.0, panel_bg[0] + 0.25),
                            min(1.0, panel_bg[1] + 0.25),
                            min(1.0, panel_bg[2] + 0.25),
                            1.0),
            scrollbar_bg=_rgba(ui.wcol_scroll.inner),
            scrollbar_handle=_rgba(ui.wcol_scroll.item),
        )

    @classmethod
    def fallback(cls) -> ThemeColors:
        """Return sensible dark-theme defaults for test environments."""
        return cls(
            panel_bg=(0.18, 0.18, 0.18, 1.0),
            panel_header_bg=(0.22, 0.22, 0.22, 1.0),
            text_primary=(0.90, 0.90, 0.90, 1.0),
            text_secondary=(0.90, 0.90, 0.90, 0.6),
            text_disabled=(0.90, 0.90, 0.90, 0.3),
            widget_bg=(0.25, 0.25, 0.25, 1.0),
            widget_bg_hover=(0.35, 0.35, 0.35, 1.0),
            widget_bg_active=(0.20, 0.45, 0.75, 1.0),
            input_bg=(0.15, 0.15, 0.15, 1.0),
            input_border=(0.40, 0.40, 0.40, 1.0),
            input_text=(0.90, 0.90, 0.90, 1.0),
            button_bg=(0.25, 0.25, 0.25, 1.0),
            button_bg_hover=(0.35, 0.35, 0.35, 1.0),
            button_text=(0.85, 0.85, 0.85, 1.0),
            list_item_bg=(0.23, 0.23, 0.23, 1.0),
            selection_bg=(0.20, 0.45, 0.75, 1.0),
            selection_text=(1.0, 1.0, 1.0, 1.0),
            alert=(1.0, 0.2, 0.2, 1.0),
            border=(0.35, 0.35, 0.35, 1.0),
            border_intense=(0.50, 0.50, 0.50, 1.0),
            scrollbar_bg=(0.12, 0.12, 0.12, 0.9),
            scrollbar_handle=(0.40, 0.40, 0.40, 1.0),
        )


# ---------------------------------------------------------------------------
# Shared theme instance (lazy-loaded)
# ---------------------------------------------------------------------------

_theme: ThemeColors | None = None


def get_theme() -> ThemeColors:
    """Return the cached :class:`ThemeColors` for the active Blender theme.

    The theme is read lazily on first access so that ``bpy.context`` is
    available (it isn't at module import time).  Falls back to
    :meth:`ThemeColors.fallback` when running outside Blender.
    """
    global _theme
    if _theme is None:
        try:
            _theme = ThemeColors.from_blender()
        except Exception as exc:
            _logger.log(f"from_blender() failed: {exc}")
            _theme = ThemeColors.fallback()
    return _theme


def reset_theme() -> None:
    """Force a theme re-read on next :func:`get_theme` call.

    Call this after the user changes Blender's theme so that all GPU UI
    components pick up the new colors.
    """
    global _theme
    _theme = None
