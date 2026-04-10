bl_info = {
    "name": "Melvil",
    "author": "",
    "version": (0, 1, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > Melvil",
    "description": "",
    "category": "Generic",
}

from . import operators, panels


def register():
    operators.register()
    panels.register()


def unregister():
    panels.unregister()
    operators.unregister()
