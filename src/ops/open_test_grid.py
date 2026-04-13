"""
MELVIL_OT_open_test_grid — temporary test popup for the custom grid component.

Invoked by ``Ctrl+Shift+S`` in the 3D View.  Displays a floating popup
with fake asset data so the grid component can be developed and validated
incrementally before integration with the real browser.

This operator and its keymap will be removed after Phase 7.
"""

from __future__ import annotations

import uuid

import bpy

_POPUP_WIDTH = 500

# Asset types to cycle through when generating fake data.
_FAKE_TYPES = ("MATERIAL", "MESH", "NODE_GROUP")

_TYPE_LABELS: dict[str, str] = {
    "MATERIAL": "Material",
    "MESH": "Mesh",
    "NODE_GROUP": "Node Group",
}

_TYPE_ICONS: dict[str, str] = {
    "MATERIAL": "MATERIAL",
    "MESH": "MESH_DATA",
    "NODE_GROUP": "NODETREE",
}


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


class MELVIL_OT_open_test_grid(bpy.types.Operator):
    """Open a test popup for the custom grid component (Ctrl+Shift+S)"""

    bl_idname = "melvil.open_test_grid"
    bl_label = "Melvil Grid Test"
    bl_options = {"REGISTER"}

    _items: list[dict] = []

    @classmethod
    def poll(cls, context):
        return context.area is not None and context.area.type == "VIEW_3D"

    def invoke(self, context, event):
        self._items = _generate_fake_items(30)
        wm = context.window_manager
        return wm.invoke_popup(self, width=_POPUP_WIDTH)

    def check(self, context):
        return True

    def modal(self, context, event):
        return {"PASS_THROUGH"}

    def execute(self, context):
        return {"FINISHED"}

    def draw(self, context):
        layout = self.layout
        layout.label(text="Grid Test Popup", icon="ASSET_MANAGER")
        layout.separator()

        box = layout.box()
        box.label(text=f"{len(self._items)} fake assets loaded")

        for item in self._items[:6]:
            row = box.row(align=True)
            row.label(
                text="",
                icon=_TYPE_ICONS.get(item["type"], "OBJECT_DATA"),
            )
            row.label(text=item["name"])

        if len(self._items) > 6:
            box.label(text=f"… and {len(self._items) - 6} more")


def register() -> None:
    bpy.utils.register_class(MELVIL_OT_open_test_grid)


def unregister() -> None:
    bpy.utils.unregister_class(MELVIL_OT_open_test_grid)
