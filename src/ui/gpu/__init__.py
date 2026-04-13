"""
GPU UI toolkit — foundational drawing primitives, theme colors, and DPI helpers.

This package provides the rendering foundation for GPU-drawn browser UIs
in Blender.  All drawing functions use Blender's ``gpu`` and ``blf``
modules to render directly into a ``SpaceView3D`` ``POST_PIXEL`` draw
handler.

The package has **no dependencies** on the rest of the Melvil addon and
can be extracted into a standalone library.

See projects/006-gpu-ui.md for the full design spec.
"""

from .constants import (
    BOX_PAD,
    FONT_ID,
    FONT_SIZE_PRIMARY,
    FONT_SIZE_SECONDARY,
    ICON_SIZE,
    PANEL_PAD,
    SCROLLBAR_MIN_HEIGHT,
    SCROLLBAR_WIDTH,
    SEPARATOR_HEIGHT,
    WIDGET_GAP,
    WIDGET_GAP_ALIGNED,
    WIDGET_HEIGHT,
    WIDGET_PAD_X,
    get_ui_scale,
    scaled,
)
from .drawing import (
    draw_rect,
    draw_rect_outline,
    draw_rect_rounded,
    draw_text,
    draw_texture,
    measure_text,
    _get_image_shader,
    _get_uniform_shader,
)
from .button import GpuButton, GpuOperatorProps
from .enum_buttons import GpuEnumButtons
from .grid_list import GpuGridList, ScrollState
from .icon_button import GpuIconButton
from .layout import GpuLayout
from .label import GpuLabel
from .icons import IconProvider
from .panel import GpuPanel, HitResult, get_region_offsets
from .separator import GpuSeparator
from .text_field import GpuTextField
from .template_icon import GpuTemplateIcon
from .theme import (
    ThemeColors,
    _color_with_alpha,
    get_theme,
    reset_theme,
)
from .widget import GpuWidget, draw_icon, draw_text_in_rect, point_in_rect
from ._logger import GpuUiLogger

__all__ = [
    # Constants
    "BOX_PAD",
    "FONT_ID",
    "FONT_SIZE_PRIMARY",
    "FONT_SIZE_SECONDARY",
    "ICON_SIZE",
    "PANEL_PAD",
    "SCROLLBAR_MIN_HEIGHT",
    "SCROLLBAR_WIDTH",
    "SEPARATOR_HEIGHT",
    "WIDGET_GAP",
    "WIDGET_GAP_ALIGNED",
    "WIDGET_HEIGHT",
    "WIDGET_PAD_X",
    # DPI
    "get_ui_scale",
    "scaled",
    # Drawing
    "draw_rect",
    "draw_rect_outline",
    "draw_rect_rounded",
    "draw_text",
    "draw_texture",
    "measure_text",
    # Theme
    "ThemeColors",
    "get_theme",
    "reset_theme",
    # Layout
    "GpuLayout",
    # Panel
    "GpuPanel",
    "HitResult",
    "get_region_offsets",
    # Widgets
    "GpuWidget",
    "GpuButton",
    "GpuEnumButtons",
    "GpuLabel",
    "GpuOperatorProps",
    "GpuSeparator",
    "GpuTemplateIcon",
    "GpuTextField",
    # Helpers
    "draw_icon",
    "draw_text_in_rect",
    "point_in_rect",
    # Logger
    "GpuUiLogger",
    # Icons
    "IconProvider",
]
