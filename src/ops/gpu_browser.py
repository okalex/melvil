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

from ..ui.gpu import GpuPanel, get_region_offsets

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
            return (0, 800)

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

        Mirrors the three-column structure of ``open_browser.py`` using
        only implemented GPU UI elements. Unsupported elements (props,
        template_list, template_icon, operator_menu_enum) are omitted.
        """
        layout.label(text="Melvil Asset Library", icon="ASSET_MANAGER")
        layout.separator()

        # Three-column split: left filters | asset list | asset details.
        outer_split = layout.split(factor=0.24)
        left = outer_split.column()
        rest_col = outer_split.column()
        inner_split = rest_col.split(factor=0.45)
        middle = inner_split.column()
        right = inner_split.column()

        # -- Left column: filters --------------------------------------------
        left.label(text="Search by name/tag", icon="VIEWZOOM")
        # search_query prop — not yet implemented
        left.separator()

        left.label(text="Asset type")
        # type_filter prop (expand=True) — not yet implemented
        left.separator()

        # Kit selector header row with New Kit and Rename Kit buttons.
        kit_header = left.row(align=True)
        kit_header.label(text="Kit")
        kit_header.operator("melvil.kit_create", text="New", icon="ADD")
        rename_sub = kit_header.row()
        rename_sub.enabled = False  # requires kit selection (no kit_filter yet)
        rename_sub.operator("melvil.kit_rename", text="Rename", icon="GREASEPENCIL")

        # kit_filter prop (expand=True) — not yet implemented
        left.separator()

        # Tag filter section.
        tag_header = left.row(align=True)
        tag_header.label(text="Tags", icon="TAG")
        # tag template_list — not yet implemented
        tag_side = left.column(align=True)
        tag_side.operator("melvil.tag_create", text="New", icon="ADD")
        delete_col = tag_side.column()
        delete_col.enabled = False  # requires active tag filter
        delete_col.operator("melvil.tag_delete", text="Delete", icon="REMOVE")
        left.separator()

        # -- Middle column: asset list ---------------------------------------
        middle.label(text="Assets", icon="ASSET_MANAGER")
        # unified asset section — not yet implemented
        middle.separator()

        # -- Right column: asset details -------------------------------------
        right.label(text="Asset details", icon="PROPERTIES")
        right_box = right.box()
        right_box.label(text="No asset selected", icon="INFO")

    def modal(self, context, event):
        # Update hover position every frame.
        if self._panel is not None:
            self._panel.update_mouse(
                event.mouse_region_x, event.mouse_region_y,
            )

        if event.type in {"ESC", "RIGHTMOUSE"} and event.value == "PRESS":
            self._cleanup(context)
            return {"CANCELLED"}

        if event.type == "LEFTMOUSE" and event.value == "PRESS":
            if self._panel is not None:
                if not self._panel.is_inside(
                    event.mouse_region_x, event.mouse_region_y,
                ):
                    self._cleanup(context)
                    return {"CANCELLED"}
                # Dispatch hit-tested operator.
                hit = self._panel.hit_test(
                    event.mouse_region_x, event.mouse_region_y,
                )
                if hit is not None and hit.widget_type == "operator":
                    try:
                        op_fn = getattr(bpy.ops, hit.id.split(".", 1)[0])
                        op_fn = getattr(op_fn, hit.id.split(".", 1)[1])
                        op_fn(**hit.kwargs)
                    except Exception:  # noqa: BLE001
                        pass
                    return {"RUNNING_MODAL"}

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
