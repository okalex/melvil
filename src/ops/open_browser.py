"""
BLAMMO_OT_open_browser — open the GPU-drawn asset browser.

Invoked by ``Ctrl+Shift+A`` in the 3D View.  Creates a :class:`UiContext`
whose rendering and build logic live in :mod:`blammo.ui.browser`.
Press ``ESC`` or ``RMB`` to dismiss.
"""

import bpy
from bpy.props import EnumProperty, StringProperty

from ..ui.gpu import UiContext
from ..ui.browser import (
    TYPE_ENUM_ITEMS,
    build_browser,
    compute_anchor,
    draw_asset_card,
    draw_asset_tag_item,
    draw_filter_tag_item,
    get_kit_filter_items,
    handle_icon_button,
)


class BLAMMO_OT_open_browser(bpy.types.Operator):
    bl_idname = "blammo.open_browser"
    bl_label = "Blammo! Browser (GPU)"
    bl_options = {"REGISTER", "INTERNAL"}

    type_filter: EnumProperty(
        name="Category",
        items=TYPE_ENUM_ITEMS,
        default="ALL",
        options={"HIDDEN"},
    )

    kit_filter: EnumProperty(
        name="Kit",
        items=get_kit_filter_items,
        default=0,
        options={"HIDDEN"},
    )

    search_query: StringProperty(
        name="Asset name",
        default="",
        options={"HIDDEN", "TEXTEDIT_UPDATE"},
    )

    _ui_context = None

    @classmethod
    def poll(cls, context):
        return context.area is not None and context.area.type == "VIEW_3D"

    def invoke(self, context, event):
        self._ui_context = UiContext(
            width=900,
            anchor=compute_anchor,
            build_fn=lambda layout: build_browser(self, self._ui_context, layout),
        )
        self._ui_context.register_list_drawer(
            "BLAMMO_UL_filter_tags", draw_filter_tag_item,
        )
        self._ui_context.register_list_drawer(
            "BLAMMO_UL_asset_grid", draw_asset_card,
        )
        self._ui_context.register_list_drawer(
            "BLAMMO_UL_asset_tags", draw_asset_tag_item,
        )
        self._ui_context.register_widget_handler(
            "icon_button", handle_icon_button,
        )
        self._ui_context.attach(context.area)
        context.window_manager.modal_handler_add(self)
        context.area.tag_redraw()
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        if self._ui_context is None:
            return {"RUNNING_MODAL"}

        result = self._ui_context.handle_event(event)

        if result.redraw and context.area is not None:
            context.area.tag_redraw()
        if result.cancelled:
            self._cleanup(context)
            return {"CANCELLED"}
        return {"RUNNING_MODAL"}

    def cancel(self, context):
        self._cleanup(context)

    def _cleanup(self, context):
        if self._ui_context is not None:
            self._ui_context.detach()
            self._ui_context = None
        if context.area is not None:
            context.area.tag_redraw()
