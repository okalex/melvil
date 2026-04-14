"""
MELVIL_OT_gpu_browser — GPU-drawn asset browser.

Invoked by ``Ctrl+Shift+S`` in the 3D View.  Creates a :class:`GpuPanel`
that renders the Melvil asset browser entirely via GPU draw handlers.
Press ``ESC`` or ``RMB`` to dismiss.

This operator is the incremental replacement for the popup-based browser.
Widgets and functionality are added as each GPU UI phase lands.
"""

import bpy
from bpy.props import EnumProperty, StringProperty

from ..ui.gpu import GpuPanel, get_region_offsets
from ..ui import scene_props as _scene_props
from ..ui.draw_helpers import load_all_tags
from .open_browser import _TYPE_ENUM_ITEMS, _get_kit_filter_items
from .tag_filter_toggle import get_active_tag_filters

_PANEL_MARGIN_X = 0
_PANEL_MARGIN_Y = 18


def _draw_filter_tag_item(layout, item, index, is_active):
    """Draw a single tag-filter row."""
    row = layout.row(align=True)
    row.label(text=item.name)
    sub = row.row()
    sub.scale_x = 0.15
    sub.icon_button(
        icon="GREASEPENCIL", button_id="tag_rename", style="GHOST",
    )


class MELVIL_OT_gpu_browser(bpy.types.Operator):
    bl_idname = "melvil.gpu_browser"
    bl_label = "Melvil Browser (GPU)"
    bl_options = {"REGISTER", "INTERNAL"}

    type_filter: EnumProperty(
        name="Category",
        items=_TYPE_ENUM_ITEMS,
        default="ALL",
        options={"HIDDEN"},
    )

    kit_filter: EnumProperty(
        name="Kit",
        items=_get_kit_filter_items,
        default=0,
        options={"HIDDEN"},
    )

    search_query: StringProperty(
        name="Asset name",
        default="",
        options={"HIDDEN", "TEXTEDIT_UPDATE"},
    )

    _panel = None

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
        self._panel.register_list_drawer(
            "MELVIL_UL_filter_tags", _draw_filter_tag_item,
        )
        self._panel.attach(context.area)
        context.window_manager.modal_handler_add(self)
        context.area.tag_redraw()
        return {"RUNNING_MODAL"}

    def _build(self, layout):
        """Build the browser widget tree.

        Mirrors the three-column structure of ``open_browser.py`` using
        only implemented GPU UI elements. Unsupported elements
        (template_list, template_icon, operator_menu_enum) are omitted.
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
        left.prop(self, "search_query", text="")
        left.separator()

        left.label(text="Asset type")
        left.prop(self, "type_filter", expand=True)
        left.separator()

        # Kit selector header row with New Kit and Rename Kit buttons.
        kit_header = left.row(align=True)
        kit_header.label(text="Kit")
        kit_header.operator("melvil.kit_create", text="New", icon="ADD")
        rename_sub = kit_header.row()
        rename_sub.enabled = self.kit_filter != "ALL_KITS"
        rename_op = rename_sub.operator(
            "melvil.kit_rename", text="Rename", icon="GREASEPENCIL",
        )
        rename_op.kit_id = (
            self.kit_filter if self.kit_filter != "ALL_KITS" else ""
        )

        left.prop(self, "kit_filter", expand=True)
        left.separator()

        # Tag filter section.
        tag_header = left.row(align=True)
        tag_header.label(text="Tags", icon="TAG")

        wm = bpy.context.window_manager
        try:
            visible_tags = load_all_tags()
        except Exception:  # noqa: BLE001
            visible_tags = []

        if visible_tags:
            active_tag_ids = get_active_tag_filters(wm)
            active_set = set(active_tag_ids)
            _scene_props._rebuilding_filter_tags = True
            try:
                wm.melvil_filter_tags.clear()
                for _ftag in visible_tags:
                    _item = wm.melvil_filter_tags.add()
                    _item.name = _ftag["name"]
                    _item.tag_id = _ftag["id"]
                    _item.is_active = _ftag["id"] in active_set
                wm.melvil_filter_tags_index = -1
            finally:
                _scene_props._rebuilding_filter_tags = False

            tag_row = left.row()
            tag_list_col = tag_row.column()
            tag_list_col.scale_x = 0.9
            tag_list_col.template_list(
                "MELVIL_UL_filter_tags", "gpu_tag_filter",
                wm, "melvil_filter_tags",
                wm, "melvil_filter_tags_index",
                rows=min(len(visible_tags), 8),
                allow_deselect=True,
            )
            tag_row.separator(factor=0.5)
            tag_btn_col = tag_row.column()
            tag_btn_col.scale_x = 0.1
            tag_btn_col.operator(
                "melvil.tag_create", text="", icon="ADD",
            )
            tag_btn_col.separator(factor=0.5)
            selected_idx = (
                self._panel._list_selections.get("gpu_tag_filter", -1)
                if self._panel is not None else -1
            )
            selected_tag = (
                wm.melvil_filter_tags[selected_idx]
                if 0 <= selected_idx < len(wm.melvil_filter_tags)
                else None
            )
            delete_btn = tag_btn_col.column()
            delete_btn.enabled = selected_tag is not None
            delete_op = delete_btn.operator(
                "melvil.tag_delete", text="", icon="REMOVE",
            )
            if selected_tag is not None:
                delete_op.tag_id = selected_tag.tag_id

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

        # -- Text field editing mode -----------------------------------------
        if self._panel is not None and self._panel.active_text_field is not None:
            # ESC / RMB cancel the text edit (not the browser).
            if event.type in {"ESC", "RIGHTMOUSE"} and event.value == "PRESS":
                self._panel.cancel_text_field()
                if context.area is not None:
                    context.area.tag_redraw()
                return {"RUNNING_MODAL"}

            # LMB: re-click on same field is a no-op; otherwise confirm
            # the current field and fall through to normal click handling.
            if event.type == "LEFTMOUSE" and event.value == "PRESS":
                hit = self._panel.hit_test(
                    event.mouse_region_x, event.mouse_region_y,
                )
                if (
                    hit is not None
                    and hit.widget_type == "text_field"
                    and hit.id == self._panel.active_text_field
                ):
                    return {"RUNNING_MODAL"}
                self._panel.confirm_text_field()
                # Fall through to normal LMB handling below.

            # All other PRESS events are routed to the text handler.
            elif event.value == "PRESS":
                self._panel.handle_text_event(event)
                if context.area is not None:
                    context.area.tag_redraw()
                return {"RUNNING_MODAL"}

        # -- Normal handling -------------------------------------------------
        if event.type in {"ESC", "RIGHTMOUSE"} and event.value == "PRESS":
            self._cleanup(context)
            return {"CANCELLED"}

        # -- Scroll events → dispatch through widget tree --------------------
        if (
            event.type in {"WHEELUPMOUSE", "WHEELDOWNMOUSE"}
            and event.value == "PRESS"
            and self._panel is not None
        ):
            ev = "SCROLL_UP" if event.type == "WHEELUPMOUSE" else "SCROLL_DOWN"
            self._panel.dispatch_event(
                ev, event.mouse_region_x, event.mouse_region_y,
            )
            if context.area is not None:
                context.area.tag_redraw()
            return {"RUNNING_MODAL"}

        if event.type == "LEFTMOUSE" and event.value == "PRESS":
            if self._panel is not None:
                if not self._panel.is_inside(
                    event.mouse_region_x, event.mouse_region_y,
                ):
                    self._cleanup(context)
                    return {"CANCELLED"}
                # Dispatch hit-tested widget.
                hit = self._panel.hit_test(
                    event.mouse_region_x, event.mouse_region_y,
                )
                if hit is not None and hit.widget_type == "text_field":
                    self._panel.activate_text_field(
                        hit.id, hit.kwargs["data"],
                    )
                    if context.area is not None:
                        context.area.tag_redraw()
                    return {"RUNNING_MODAL"}
                if hit is not None and hit.widget_type == "operator":
                    try:
                        op_fn = getattr(bpy.ops, hit.id.split(".", 1)[0])
                        op_fn = getattr(op_fn, hit.id.split(".", 1)[1])
                        op_fn("INVOKE_DEFAULT", **hit.kwargs)
                    except Exception:  # noqa: BLE001
                        pass
                    return {"RUNNING_MODAL"}
                if hit is not None and hit.widget_type == "prop":
                    data = hit.kwargs.get("data")
                    value = hit.kwargs.get("value")
                    if data is not None and value is not None:
                        try:
                            setattr(data, hit.id, value)
                        except Exception:  # noqa: BLE001
                            pass
                    return {"RUNNING_MODAL"}
                if hit is not None and hit.widget_type == "icon_button":
                    self._handle_icon_button(context, hit)
                    return {"RUNNING_MODAL"}
                if hit is not None and hit.widget_type == "list_row":
                    data = hit.kwargs.get("active_dataptr")
                    prop = hit.kwargs.get("active_propname")
                    idx = hit.kwargs.get("index")
                    list_id = hit.kwargs.get("list_id")
                    allow_deselect = hit.kwargs.get("allow_deselect", False)
                    # Toggle selection off when clicking the active item.
                    if (
                        allow_deselect
                        and list_id is not None
                        and self._panel._list_selections.get(list_id) == idx
                    ):
                        self._panel._list_selections[list_id] = -1
                        if data is not None and prop is not None:
                            try:
                                setattr(data, prop, -1)
                            except Exception:  # noqa: BLE001
                                pass
                    else:
                        if data is not None and prop is not None and idx is not None:
                            try:
                                setattr(data, prop, idx)
                            except Exception:  # noqa: BLE001
                                pass
                        # Track visual selection on the panel (separate from
                        # the data-model index which may be reset by callbacks).
                        if list_id is not None and idx is not None:
                            self._panel._list_selections[list_id] = idx
                    if context.area is not None:
                        context.area.tag_redraw()
                    return {"RUNNING_MODAL"}

        if context.area is not None:
            context.area.tag_redraw()

        return {"RUNNING_MODAL"}

    def cancel(self, context):
        self._cleanup(context)

    def _handle_icon_button(self, context, hit):
        """Dispatch an icon_button click to the appropriate action."""
        button_id = hit.id
        idx = hit.kwargs.get("index")
        if button_id == "tag_rename" and idx is not None:
            wm = context.window_manager
            tags = getattr(wm, "melvil_filter_tags", [])
            if 0 <= idx < len(tags):
                tag_item = tags[idx]
                bpy.ops.melvil.tag_rename("INVOKE_DEFAULT", tag_id=tag_item.tag_id)
        if context.area is not None:
            context.area.tag_redraw()

    def _cleanup(self, context):
        if self._panel is not None:
            self._panel.detach()
            self._panel = None
        if context.area is not None:
            context.area.tag_redraw()
