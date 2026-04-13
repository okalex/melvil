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
from pathlib import Path

import bpy
import gpu

from ..ui.grid_list import compute_max_offset, draw_grid, hit_test, is_over_grid

_GRID_COLS = 3
_GRID_ROWS_VISIBLE = 4

# Asset types to cycle through when generating fake data.
_FAKE_TYPES = ("MATERIAL", "MESH", "NODE_GROUP")

_TYPE_LABELS: dict[str, str] = {
    "MATERIAL": "Material",
    "MESH": "Mesh",
    "NODE_GROUP": "Node Group",
}

_RESOURCE_DIR = Path(__file__).resolve().parent.parent / "resources" / "img"

_PLACEHOLDER_FILES: dict[str, str] = {
    "MATERIAL": "placeholder_material.png",
    "MESH": "placeholder_mesh.png",
    "NODE_GROUP": "placeholder_node_group.png",
}

# Preview textures are cached for the lifetime of the overlay to avoid
# reloading images every frame.
_texture_cache: dict[str, object] = {}

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


def _get_test_preview_texture(item: dict):
    """Load and cache a GPU texture for the item's preview placeholder."""
    preview_path = item.get("preview_path")
    if not preview_path:
        return None
    if preview_path in _texture_cache:
        return _texture_cache[preview_path]
    try:
        img = bpy.data.images.load(str(preview_path), check_existing=True)
        texture = gpu.texture.from_image(img)
        _texture_cache[preview_path] = texture
        return texture
    except Exception:
        return None


def _draw_callback(state: dict) -> None:
    """``SpaceView3D`` ``POST_PIXEL`` callback — render the card grid."""
    if not state.get("active") or not state.get("items"):
        return
    area = bpy.context.area
    region = bpy.context.region
    offset_x, offset_y = _get_region_offsets(area)

    # Read scroll state from the transient WM property group.
    scroll_props = bpy.context.window_manager.melvil_grid_scroll
    is_list = scroll_props.display_mode == "LIST"
    cols = 1 if is_list else state["cols"]
    draw_grid(
        region,
        state["items"],
        cols=cols,
        rows_visible=state["rows_visible"],
        scroll_offset=scroll_props.scroll_offset,
        selected_id=scroll_props.selected_id,
        hovered_index=scroll_props.hovered_index,
        offset_x=offset_x,
        offset_y=offset_y,
        get_preview_texture=_get_test_preview_texture,
    )


# ---------------------------------------------------------------------------
# Fake data helper
# ---------------------------------------------------------------------------

def _generate_fake_items(count: int = 30) -> list[dict]:
    """Return *count* fake asset dicts for testing."""
    items = []
    for i in range(count):
        asset_type = _FAKE_TYPES[i % len(_FAKE_TYPES)]
        placeholder = _PLACEHOLDER_FILES.get(asset_type)
        preview_path = str(_RESOURCE_DIR / placeholder) if placeholder else None
        items.append({
            "id": str(uuid.uuid4()),
            "name": f"Fake {_TYPE_LABELS[asset_type]} {i + 1}",
            "type": asset_type,
            "preview_path": preview_path,
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
        _draw_state["active"] = True

        # Reset transient scroll state.
        scroll_props = context.window_manager.melvil_grid_scroll
        scroll_props.scroll_offset = 0
        scroll_props.selected_id = ""
        scroll_props.hovered_index = -1
        scroll_props.display_mode = "GRID"

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

        # Toggle display mode with T.
        if event.type == 'T' and event.value == 'PRESS':
            scroll_props = context.window_manager.melvil_grid_scroll
            scroll_props.display_mode = (
                "LIST" if scroll_props.display_mode == "GRID" else "GRID"
            )
            scroll_props.scroll_offset = 0
            scroll_props.hovered_index = -1
            context.area.tag_redraw()
            return {"RUNNING_MODAL"}

        # Convert window coords to region-local for hit testing.
        region = context.region
        mx = event.mouse_x - region.x
        my = event.mouse_y - region.y

        over = is_over_grid(mx, my)

        # Hover tracking — update on every mouse move.
        if event.type == 'MOUSEMOVE':
            scroll_props = context.window_manager.melvil_grid_scroll
            result = hit_test(mx, my)
            new_hover = result[1] if result is not None else -1
            if new_hover != scroll_props.hovered_index:
                scroll_props.hovered_index = new_hover
                context.area.tag_redraw()
            return {"PASS_THROUGH"}

        # Click selection — select the card under the cursor.
        if over and event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            scroll_props = context.window_manager.melvil_grid_scroll
            result = hit_test(mx, my)
            if result is not None:
                scroll_props.selected_id = result[0]
                context.area.tag_redraw()
            return {"RUNNING_MODAL"}

        if over and event.type == 'WHEELUPMOUSE':
            scroll_props = context.window_manager.melvil_grid_scroll
            scroll_props.scroll_offset = max(0, scroll_props.scroll_offset - 1)
            context.area.tag_redraw()
            return {"RUNNING_MODAL"}

        if over and event.type == 'WHEELDOWNMOUSE':
            scroll_props = context.window_manager.melvil_grid_scroll
            is_list = scroll_props.display_mode == "LIST"
            cols = 1 if is_list else _draw_state["cols"]
            max_off = compute_max_offset(
                len(_draw_state["items"]),
                cols,
                _draw_state["rows_visible"],
            )
            scroll_props.scroll_offset = min(max_off, scroll_props.scroll_offset + 1)
            context.area.tag_redraw()
            return {"RUNNING_MODAL"}

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
    _texture_cache.clear()
    if context is not None and context.area is not None:
        context.area.tag_redraw()


def register() -> None:
    bpy.utils.register_class(MELVIL_OT_open_test_grid)


def unregister() -> None:
    bpy.utils.unregister_class(MELVIL_OT_open_test_grid)
