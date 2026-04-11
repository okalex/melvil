import bpy
from bpy.props import StringProperty
from bpy.types import AddonPreferences

from .utils import register_class as _safe_register


def _on_library_root_update(self, context):
    from .core.library import sync_blender_asset_library
    sync_blender_asset_library()


class MelvilPreferences(AddonPreferences):
    bl_idname = __package__

    library_root: StringProperty(
        name="Library Root",
        description="Directory where managed .blend files and textures are stored",
        subtype="DIR_PATH",
        default="",
        update=_on_library_root_update,
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
        from .core.library import _default_db_path, _default_library_root

        layout = self.layout
        layout.prop(self, "library_root")
        if not self.library_root.strip():
            layout.label(text=f"Default: {_default_library_root()}", icon="INFO")

        layout.prop(self, "db_path")

        # Show the resolved DB location so the user knows where the index lives.
        if not self.db_path.strip():
            layout.label(text=f"Default DB: {_default_db_path()}", icon="INFO")


_classes = (MelvilPreferences,)


def register():
    for cls in _classes:
        _safe_register(cls)


def unregister():
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
