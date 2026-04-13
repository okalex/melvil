"""
MELVIL_OT_gpu_browser — GPU-drawn asset browser.

Invoked by ``Ctrl+Shift+S`` in the 3D View.  Creates a :class:`GpuPanel`
that renders the Melvil asset browser entirely via GPU draw handlers.
Press ``ESC`` or ``RMB`` to dismiss.

This operator is the incremental replacement for the popup-based browser.
Widgets and functionality are added as each GPU UI phase lands.
"""

from __future__ import annotations

import bpy

from ..ui.gpu_ui import GpuPanel, get_region_offsets

_PANEL_MARGIN_X = 0
_PANEL_MARGIN_Y = 18


class MELVIL_OT_gpu_browser(bpy.types.Operator):
    bl_idname = "melvil.gpu_browser"
    bl_label = "Melvil Browser (GPU)"
    bl_options = {"REGISTER", "INTERNAL"}

    _panel: GpuPanel | None = None

    @classmethod
    def poll(cls, context):
        return context.area is not None and context.area.type == "VIEW_3D"

    @staticmethod
    def _compute_anchor() -> tuple[int, int]:
        """Return ``(x, y)`` top-left anchor in WINDOW-region pixels.

        Places the panel to the right of the vertical toolbar with a
        margin, and below any overlay button rows at the top of the
        WINDOW region.
        """
        try:
            area = bpy.context.area
            region = bpy.context.region
            offset_x, offset_y = get_region_offsets(area)
            x = offset_x + _PANEL_MARGIN_X
            y = region.height - offset_y - _PANEL_MARGIN_Y
            return (x, y)
        except Exception:
            return (_PANEL_MARGIN, 800)

    def invoke(self, context, event):
        self._panel = GpuPanel(
            width=900,
            anchor=self._compute_anchor,
            build_fn=self._build,
        )
        self._panel.attach(context.area)
        context.window_manager.modal_handler_add(self)
        context.area.tag_redraw()
        return {"RUNNING_MODAL"}

    def _build(self, layout):
        """Build the browser widget tree.

        Widgets are added incrementally as each GPU UI phase lands.
        """
        layout.separator()
        layout.separator()
        layout.separator()

    def modal(self, context, event):
        if event.type in {"ESC", "RIGHTMOUSE"} and event.value == "PRESS":
            self._cleanup(context)
            return {"CANCELLED"}

        if event.type == "LEFTMOUSE" and event.value == "PRESS":
            if self._panel and not self._panel.is_inside(
                event.mouse_region_x, event.mouse_region_y,
            ):
                self._cleanup(context)
                return {"CANCELLED"}

        if context.area is not None:
            context.area.tag_redraw()

        return {"RUNNING_MODAL"}

    def cancel(self, context):
        self._cleanup(context)

    def _cleanup(self, context):
        if self._panel is not None:
            self._panel.detach()
            self._panel = None
        if context.area is not None:
            context.area.tag_redraw()
