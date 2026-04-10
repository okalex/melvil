"""
Configure bpy mock for tests. Blender's bpy module is only available at runtime
inside Blender, so we mock it here to allow unit testing outside of Blender.
"""

import sys
import types
from unittest.mock import MagicMock


def _make_bpy_mock() -> types.ModuleType:
    bpy = types.ModuleType("bpy")

    # bpy.types — base classes for operators, panels, etc.
    bpy_types = types.ModuleType("bpy.types")

    class _Base:
        bl_idname = ""
        bl_label = ""
        bl_options = set()

    class Operator(_Base):
        pass

    class Panel(_Base):
        bl_space_type = ""
        bl_region_type = ""
        bl_category = ""

    class PropertyGroup(_Base):
        pass

    class AddonPreferences(_Base):
        bl_idname = ""

        def draw(self, context):
            pass

    bpy_types.Operator = Operator
    bpy_types.Panel = Panel
    bpy_types.PropertyGroup = PropertyGroup
    bpy_types.AddonPreferences = AddonPreferences
    bpy.types = bpy_types
    sys.modules["bpy.types"] = bpy_types

    # bpy.utils
    bpy_utils = types.ModuleType("bpy.utils")
    bpy_utils.register_class = MagicMock()
    bpy_utils.unregister_class = MagicMock()
    bpy.utils = bpy_utils
    sys.modules["bpy.utils"] = bpy_utils

    # bpy.props — register as a real submodule so `from bpy.props import X` works
    bpy_props = types.ModuleType("bpy.props")
    bpy_props.StringProperty = MagicMock(return_value=None)
    bpy_props.IntProperty = MagicMock(return_value=None)
    bpy_props.FloatProperty = MagicMock(return_value=None)
    bpy_props.BoolProperty = MagicMock(return_value=None)
    bpy_props.EnumProperty = MagicMock(return_value=None)
    bpy_props.CollectionProperty = MagicMock(return_value=None)
    bpy_props.PointerProperty = MagicMock(return_value=None)
    bpy.props = bpy_props
    sys.modules["bpy.props"] = bpy_props

    # bpy.ops / bpy.context / bpy.data — light mocks
    bpy.ops = MagicMock()
    bpy.context = MagicMock()
    bpy.data = MagicMock()

    return bpy


# Install the mock before any addon module is imported.
if "bpy" not in sys.modules:
    sys.modules["bpy"] = _make_bpy_mock()
