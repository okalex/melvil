import bpy
from bpy.props import StringProperty
from bpy.types import AddonPreferences


class MelvilPreferences(AddonPreferences):
    bl_idname = __package__

    library_root: StringProperty(
        name="Library Root",
        description="Directory where managed .blend files and textures are stored",
        subtype="DIR_PATH",
        default="",
    )

    db_path: StringProperty(
        name="Database Path",
        description=(
            "Path to the SQLite database file. "
            "Leave empty to use <library_root>/melvil.db"
        ),
        subtype="FILE_PATH",
        default="",
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "library_root")
        layout.prop(self, "db_path")


_classes = (MelvilPreferences,)


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
