import bpy


class MELVIL_PT_main(bpy.types.Panel):
    """Main panel"""

    bl_label = "Melvil"
    bl_idname = "MELVIL_PT_main"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Melvil"

    def draw(self, context):
        layout = self.layout
        layout.operator("melvil.hello")


classes = (MELVIL_PT_main,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
