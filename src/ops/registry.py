"""
Central registry for all Blammo operators.
"""

import bpy

from ..utils import register_class as _safe_register
from .add_node_group import BLAMMO_OT_add_node_group
from .asset_edit_tags import BLAMMO_OT_asset_edit_tags
from .asset_rename import BLAMMO_OT_asset_name_confirm
from .asset_select import BLAMMO_OT_asset_select
from .asset_set_kit import BLAMMO_OT_asset_set_kit
from .delete import BLAMMO_OT_delete_asset
from .kit_create import BLAMMO_OT_kit_create
from .kit_rename import BLAMMO_OT_kit_rename
from .load import BLAMMO_OT_load_asset
from . import load_material as _load_material_mod
from .load_material import (
    BLAMMO_OT_load_material_to_slot,
    BLAMMO_PG_MaterialItem,
    BLAMMO_UL_MaterialList,
)
from .open_blend_file import BLAMMO_OT_open_blend_file, BLAMMO_OT_reveal_blend_file
from .open_browser import BLAMMO_OT_open_browser
from .save import BLAMMO_OT_save_asset, BLAMMO_OT_save_nodes_as_asset
from .set_active_kit import BLAMMO_OT_set_active_kit
from .set_preview_object import BLAMMO_OT_set_preview_object
from .tag_add import BLAMMO_OT_tag_add
from .tag_create import BLAMMO_OT_tag_create
from .tag_delete import BLAMMO_OT_tag_delete
from .tag_delete_unused import BLAMMO_OT_tag_delete_unused
from .tag_filter_clear import BLAMMO_OT_tag_filter_clear
from .tag_filter_set import BLAMMO_OT_tag_filter_set
from .tag_filter_toggle import BLAMMO_OT_tag_filter_toggle
from .tag_remove import BLAMMO_OT_tag_remove
from .tag_rename import BLAMMO_OT_tag_rename
from .toggle_sidebar import BLAMMO_OT_toggle_sidebar

_classes = (
    BLAMMO_OT_add_node_group,
    BLAMMO_OT_asset_edit_tags,
    BLAMMO_OT_asset_name_confirm,
    BLAMMO_OT_asset_select,
    BLAMMO_OT_asset_set_kit,
    BLAMMO_OT_kit_create,
    BLAMMO_OT_kit_rename,
    BLAMMO_OT_save_asset,
    BLAMMO_OT_save_nodes_as_asset,
    BLAMMO_OT_load_asset,
    BLAMMO_OT_load_material_to_slot,
    BLAMMO_OT_delete_asset,
    BLAMMO_OT_open_blend_file,
    BLAMMO_OT_reveal_blend_file,
    BLAMMO_OT_open_browser,
    BLAMMO_OT_set_active_kit,
    BLAMMO_OT_set_preview_object,
    BLAMMO_OT_tag_add,
    BLAMMO_OT_tag_create,
    BLAMMO_OT_tag_remove,
    BLAMMO_OT_tag_rename,
    BLAMMO_OT_tag_delete,
    BLAMMO_OT_tag_delete_unused,
    BLAMMO_OT_tag_filter_clear,
    BLAMMO_OT_tag_filter_set,
    BLAMMO_OT_tag_filter_toggle,
    BLAMMO_OT_toggle_sidebar,
)


def register():
    _load_material_mod.register()
    for cls in _classes:
        _safe_register(cls)


def unregister():
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
    _load_material_mod.unregister()
