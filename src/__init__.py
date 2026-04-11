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


def register():
    for mod in _modules:
        mod.register()
    ensure_db()
    sync_blender_asset_library()


def unregister():
    for mod in reversed(_modules):
        mod.unregister()
