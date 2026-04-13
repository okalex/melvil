"""
MELVIL_OT_open_test_grid — temporary viewport overlay for the custom grid.

Invoked by ``Ctrl+Shift+S`` in the 3D View.  Registers a
``SpaceView3D.draw_handler_add`` callback that renders fake asset cards
using the GPU grid component.  Press ``ESC`` or ``RMB`` to dismiss.

GPU drawing does **not** work inside a popup operator's ``draw()`` (the
UILayout pipeline overwrites it), so the test surface renders as a
viewport overlay via ``POST_PIXEL`` instead.

This operator and its keymap will be removed after Phase 7.
"""

from __future__ import annotations

import uuid

import bpy

from ..ui.grid_list import draw_grid

_GRID_COLS = 3
_GRID_ROWS_VISIBLE = 4

# Asset types to cycle through when generating fake data.
_FAKE_TYPES = ("MATERIAL", "MESH", "NODE_GROUP")

_TYPE_LABELS: dict[str, str] = {
    "MATERIAL": "Material",
    "MESH": "Mesh",
    "NODE_GROUP": "Node Group",
}

# ---------------------------------------------------------------------------
# Module-level draw handler state
# ---------------------------------------------------------------------------
# Shared mutable dict passed to ``draw_handler_add`` so the callback always
# sees current items without needing a reference to the operator instance.

_draw_state: dict = {
    "active": False,
    "items": [],
    "cols": _GRID_COLS,
    "rows_visible": _GRID_ROWS_VISIBLE,
    "scroll_offset": 0,
}
_draw_handle = None


def _get_region_offsets(area) -> tuple[int, int]:
    """Return (offset_x, offset_y) to clear the toolbar and header overlays.

    In Blender's 3D viewport the TOOLS, HEADER, and TOOL_HEADER regions
    overlay the WINDOW region, so ``POST_PIXEL`` drawing at ``(0, 0)``
    sits behind them.  This helper inspects the area's regions and returns
    pixel offsets that push the grid past those overlays.
    """
    offset_x = 0
    offset_y = 0
    for r in area.regions:
        if r.type == "TOOLS":
            offset_x = max(offset_x, r.width)
        elif r.type in {"HEADER", "TOOL_HEADER"}:
            offset_y += r.height
    return offset_x, offset_y


def _draw_callback(state: dict) -> None:
    """``SpaceView3D`` ``POST_PIXEL`` callback — render the card grid."""
    if not state.get("active") or not state.get("items"):
        return
    area = bpy.context.area
    region = bpy.context.region
    offset_x, offset_y = _get_region_offsets(area)
    draw_grid(
        region,
        state["items"],
        cols=state["cols"],
        rows_visible=state["rows_visible"],
        scroll_offset=state["scroll_offset"],
        offset_x=offset_x,
        offset_y=offset_y,
    )


# ---------------------------------------------------------------------------
# Fake data helper
# ---------------------------------------------------------------------------

def _generate_fake_items(count: int = 30) -> list[dict]:
    """Return *count* fake asset dicts for testing."""
    items = []
    for i in range(count):
        asset_type = _FAKE_TYPES[i % len(_FAKE_TYPES)]
        items.append({
            "id": str(uuid.uuid4()),
            "name": f"Fake {_TYPE_LABELS[asset_type]} {i + 1}",
            "type": asset_type,
            "preview_path": None,
            "blend_path": "",
        })
    return items


# ---------------------------------------------------------------------------
# Operator
# ---------------------------------------------------------------------------

class MELVIL_OT_open_test_grid(bpy.types.Operator):
    """Toggle the GPU grid test overlay in the viewport (Ctrl+Shift+S)"""

    bl_idname = "melvil.open_test_grid"
    bl_label = "Melvil Grid Test"
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        return context.area is not None and context.area.type == "VIEW_3D"

    def invoke(self, context, event):
        global _draw_handle

        _draw_state["items"] = _generate_fake_items(30)
        _draw_state["scroll_offset"] = 0
        _draw_state["active"] = True

        _draw_handle = bpy.types.SpaceView3D.draw_handler_add(
            _draw_callback, (_draw_state,), 'WINDOW', 'POST_PIXEL',
        )
        context.window_manager.modal_handler_add(self)
        context.area.tag_redraw()
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        if event.type in {'RIGHTMOUSE', 'ESC'}:
            _cleanup_draw_handler(context)
            return {"CANCELLED"}

        return {"PASS_THROUGH"}

    def execute(self, context):
        return {"FINISHED"}


def _cleanup_draw_handler(context=None) -> None:
    """Remove the viewport draw handler and deactivate rendering."""
    global _draw_handle
    if _draw_handle is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_draw_handle, 'WINDOW')
        _draw_handle = None
    _draw_state["active"] = False
    _draw_state["items"] = []
    if context is not None and context.area is not None:
        context.area.tag_redraw()


def register() -> None:
    bpy.utils.register_class(MELVIL_OT_open_test_grid)


def unregister() -> None:
    bpy.utils.unregister_class(MELVIL_OT_open_test_grid)
