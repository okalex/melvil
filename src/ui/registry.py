"""
Central registry for all Melvil panels and UI classes.
"""

import bpy

from ..utils import register_class as _safe_register
from . import keymaps, menu_items, menus, menus_add, menus_material, menus_node_add, menus_node_editor, previews_collection, scene_props
from .draw_helpers import MELVIL_UL_asset_tags, MELVIL_UL_filter_tags
from .panel import MELVIL_PT_main

_classes = (
    MELVIL_UL_filter_tags,
    MELVIL_UL_asset_tags,
    MELVIL_PT_main,
)


def register():
    previews_collection.register()
    scene_props.register()
    for cls in _classes:
        _safe_register(cls)
    menus.register()
    menu_items.register()
    menus_add.register()
    menus_material.register()
    menus_node_add.register()
    menus_node_editor.register()
    keymaps.register()


def unregister():
    keymaps.unregister()
    menus_material.unregister()
    menus_node_editor.unregister()
    menus_node_add.unregister()
    menus_add.unregister()
    menu_items.unregister()
    menus.unregister()
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
    scene_props.unregister()
    previews_collection.unregister()
