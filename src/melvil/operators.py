import bpy


class MELVIL_OT_hello(bpy.types.Operator):
    """Hello World operator"""

    bl_idname = "melvil.hello"
    bl_label = "Hello"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        self.report({"INFO"}, "Hello from Melvil!")
        return {"FINISHED"}


classes = (MELVIL_OT_hello,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
