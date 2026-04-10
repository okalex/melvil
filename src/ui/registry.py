"""
Central registry for all Melvil panels and UI classes.
"""

import bpy

from ..utils import register_class as _safe_register
from . import keymaps
from .panel import MELVIL_PT_main

_classes = (
    MELVIL_PT_main,
)


def register():
    for cls in _classes:
        _safe_register(cls)
    keymaps.register()


def unregister():
    keymaps.unregister()
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
