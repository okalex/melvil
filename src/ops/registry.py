"""
Central registry for all Melvil operators.
"""

import bpy

from ..utils import register_class as _safe_register
from .delete import MELVIL_OT_delete_asset
from .load import MELVIL_OT_load_asset
from .save import MELVIL_OT_save_asset

_classes = (
    MELVIL_OT_save_asset,
    MELVIL_OT_load_asset,
    MELVIL_OT_delete_asset,
)


def register():
    for cls in _classes:
        _safe_register(cls)


def unregister():
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
