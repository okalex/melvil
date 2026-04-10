"""Shared registration utilities."""

from __future__ import annotations

import bpy


def register_class(cls) -> None:
    """Register a bpy class, unregistering it first if already registered.

    Blender raises ValueError if a class is registered twice, which happens
    when Reload Scripts re-runs the module without a full Blender restart.
    """
    try:
        bpy.utils.register_class(cls)
    except ValueError:
        bpy.utils.unregister_class(cls)
        bpy.utils.register_class(cls)
