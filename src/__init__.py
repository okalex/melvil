bl_info = {
    "name": "Melvil",
    "author": "",
    "version": (0, 1, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > Melvil",
    "description": "Personal asset library manager",
    "category": "Generic",
}

from . import preferences
from .ops import registry as ops_registry
from .ui import registry as ui_registry
from .core.library import ensure_db

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


def unregister():
    for mod in reversed(_modules):
        mod.unregister()
