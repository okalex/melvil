import bpy

from . import preferences
from .ops import registry as ops_registry
from .ui import registry as ui_registry
from .core.library import ensure_db, sync_blender_asset_library

# Ordered list of modules that expose register()/unregister().
_modules = [
    preferences,
    ops_registry,
    ui_registry,
]


def _sync_deferred():
    """Timer callback: runs after Blender's UI context is ready."""
    sync_blender_asset_library()
    return None  # Don't reschedule.


def register():
    for mod in _modules:
        mod.register()
    ensure_db()
    # Defer the asset library sync so that bpy.ops is callable (requires an
    # active window context that isn't available during addon registration).
    bpy.app.timers.register(_sync_deferred, first_interval=0.0)


def unregister():
    for mod in reversed(_modules):
        mod.unregister()
