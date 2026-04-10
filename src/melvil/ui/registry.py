"""
Central registry for all Melvil panels and UI classes.
Import panel modules here and add their classes to _classes.
"""

import bpy

_classes = ()


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
