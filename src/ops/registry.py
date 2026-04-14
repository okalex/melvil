"""
Central registry for all Melvil operators.
"""

import bpy

from ..utils import register_class as _safe_register
from .add_node_group import MELVIL_OT_add_node_group
from .asset_edit_tags import MELVIL_OT_asset_edit_tags
from .asset_rename import MELVIL_OT_asset_name_confirm
from .asset_select import MELVIL_OT_asset_select
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
from .open_blend_file import MELVIL_OT_open_blend_file, MELVIL_OT_reveal_blend_file
from .gpu_browser import MELVIL_OT_gpu_browser
from .save import MELVIL_OT_save_asset, MELVIL_OT_save_nodes_as_asset
from ..ui.grid_list import MELVIL_OT_grid_scroll_nav
from .set_active_kit import MELVIL_OT_set_active_kit
from .set_preview_object import MELVIL_OT_set_preview_object
from .tag_add import MELVIL_OT_tag_add
from .tag_create import MELVIL_OT_tag_create
from .tag_delete import MELVIL_OT_tag_delete
from .tag_delete_unused import MELVIL_OT_tag_delete_unused
from .tag_filter_clear import MELVIL_OT_tag_filter_clear
from .tag_filter_set import MELVIL_OT_tag_filter_set
from .tag_filter_toggle import MELVIL_OT_tag_filter_toggle
from .tag_remove import MELVIL_OT_tag_remove
from .tag_rename import MELVIL_OT_tag_rename
from .toggle_sidebar import MELVIL_OT_toggle_sidebar

_classes = (
    MELVIL_OT_add_node_group,
    MELVIL_OT_asset_edit_tags,
    MELVIL_OT_asset_name_confirm,
    MELVIL_OT_asset_select,
    MELVIL_OT_asset_set_kit,
    MELVIL_OT_kit_create,
    MELVIL_OT_kit_rename,
    MELVIL_OT_save_asset,
    MELVIL_OT_save_nodes_as_asset,
    MELVIL_OT_load_asset,
    MELVIL_OT_load_material_to_slot,
    MELVIL_OT_delete_asset,
    MELVIL_OT_open_blend_file,
    MELVIL_OT_reveal_blend_file,
    MELVIL_OT_gpu_browser,
    MELVIL_OT_grid_scroll_nav,
    MELVIL_OT_set_active_kit,
    MELVIL_OT_set_preview_object,
    MELVIL_OT_tag_add,
    MELVIL_OT_tag_create,
    MELVIL_OT_tag_remove,
    MELVIL_OT_tag_rename,
    MELVIL_OT_tag_delete,
    MELVIL_OT_tag_delete_unused,
    MELVIL_OT_tag_filter_clear,
    MELVIL_OT_tag_filter_set,
    MELVIL_OT_tag_filter_toggle,
    MELVIL_OT_toggle_sidebar,
)


def register():
    _load_material_mod.register()
    for cls in _classes:
        _safe_register(cls)


def unregister():
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
    _load_material_mod.unregister()
