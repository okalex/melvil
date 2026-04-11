"""
Central registry for all Melvil operators.
"""

import bpy

from ..utils import register_class as _safe_register
from .add_node_group import MELVIL_OT_add_node_group
from .asset_set_kit import MELVIL_OT_asset_set_kit
from .delete import MELVIL_OT_delete_asset
from .kit_create import MELVIL_OT_kit_create
from .kit_rename import MELVIL_OT_kit_rename
from .load import MELVIL_OT_load_asset
from . import load_material as _load_material_mod
from .load_material import (
    MELVIL_OT_load_material_to_slot,
    MELVIL_PG_MaterialItem,
    MELVIL_UL_MaterialList,
)
from . import open_browser as _open_browser_mod
from .open_browser import MELVIL_OT_open_browser
from .save import MELVIL_OT_save_asset, MELVIL_OT_save_nodes_as_asset
from .toggle_sidebar import MELVIL_OT_toggle_sidebar

_classes = (
    MELVIL_OT_add_node_group,
    MELVIL_OT_asset_set_kit,
    MELVIL_OT_kit_create,
    MELVIL_OT_kit_rename,
    MELVIL_OT_save_asset,
    MELVIL_OT_save_nodes_as_asset,
    MELVIL_OT_load_asset,
    MELVIL_OT_load_material_to_slot,
    MELVIL_OT_delete_asset,
    MELVIL_OT_open_browser,
    MELVIL_OT_toggle_sidebar,
)


def register():
    _load_material_mod.register()
    _open_browser_mod.register()
    for cls in _classes:
        _safe_register(cls)


def unregister():
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
    _open_browser_mod.unregister()
    _load_material_mod.unregister()
