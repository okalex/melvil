"""
Central registry for all Melvil operators.
Import operator modules here and add their classes to _classes.
"""

import bpy

from ..utils import register_class as _safe_register

_classes = ()


def register():
    for cls in _classes:
        _safe_register(cls)


def unregister():
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
