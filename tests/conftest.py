"""
Configure bpy mock and import path for tests.

Blender's bpy module is only available at runtime inside Blender, so we mock
it here. We also register src/ as the 'melvil' package so that tests can
import it by its addon name without requiring an installed package.
"""

import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# bpy mock
# ---------------------------------------------------------------------------


def _make_bpy_mock() -> types.ModuleType:
    bpy = types.ModuleType("bpy")

    # bpy.types — base classes for operators, panels, etc.
    bpy_types = types.ModuleType("bpy.types")

    class _Base:
        bl_idname = ""
        bl_label = ""
        bl_options = set()

    class Operator(_Base):
        def report(self, type, message):
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

    class Menu(_Base):
        def draw(self, context):
            pass

    class UIList(_Base):
        bl_idname = ""
        layout_type = "DEFAULT"

        def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
            pass

    class VIEW3D_MT_object_context_menu:
        _handlers: list = []

        @classmethod
        def append(cls, fn):
            cls._handlers.append(fn)

        @classmethod
        def remove(cls, fn):
            try:
                cls._handlers.remove(fn)
            except ValueError:
                pass

    class VIEW3D_MT_add:
        _handlers: list = []

        @classmethod
        def append(cls, fn):
            cls._handlers.append(fn)

        @classmethod
        def remove(cls, fn):
            try:
                cls._handlers.remove(fn)
            except ValueError:
                pass

    class MATERIAL_MT_context_menu:
        _handlers: list = []

        @classmethod
        def append(cls, fn):
            cls._handlers.append(fn)

        @classmethod
        def remove(cls, fn):
            try:
                cls._handlers.remove(fn)
            except ValueError:
                pass

    bpy_types.Operator = Operator
    bpy_types.Panel = Panel
    bpy_types.PropertyGroup = PropertyGroup
    bpy_types.AddonPreferences = AddonPreferences
    bpy_types.Menu = Menu
    bpy_types.UIList = UIList
    bpy_types.VIEW3D_MT_object_context_menu = VIEW3D_MT_object_context_menu
    bpy_types.VIEW3D_MT_add = VIEW3D_MT_add
    bpy_types.MATERIAL_MT_context_menu = MATERIAL_MT_context_menu

    class WindowManager:
        """Minimal WindowManager stand-in for attribute assignment in register()."""

    bpy_types.WindowManager = WindowManager

    bpy.types = bpy_types
    sys.modules["bpy.types"] = bpy_types

    # bpy.utils
    bpy_utils = types.ModuleType("bpy.utils")
    bpy_utils.register_class = MagicMock()
    bpy_utils.unregister_class = MagicMock()
    bpy_utils.extension_path_user = MagicMock(return_value="/tmp/melvil_test_data")
    bpy_utils.user_resource = MagicMock(return_value="/tmp/melvil_test_config")
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

    # bpy.ops / bpy.data — light mocks
    bpy.ops = MagicMock()
    bpy.data = MagicMock()

    # bpy.path
    bpy_path = types.ModuleType("bpy.path")
    bpy_path.abspath = lambda p: p  # identity — paths are already absolute in tests
    bpy.path = bpy_path
    sys.modules["bpy.path"] = bpy_path

    # bpy.context — wire up preferences so ensure_db() sees an empty library_root
    # and short-circuits without touching the filesystem.
    mock_prefs = MagicMock()
    mock_prefs.library_root = ""
    mock_prefs.db_path = ""
    mock_addon = MagicMock()
    mock_addon.preferences = mock_prefs
    mock_addons = MagicMock()
    mock_addons.__getitem__ = MagicMock(return_value=mock_addon)
    mock_context = MagicMock()
    mock_context.preferences.addons = mock_addons
    mock_context.preferences.filepaths.asset_libraries = []
    bpy.context = mock_context

    return bpy


# Install the mock before any addon module is imported.
if "bpy" not in sys.modules:
    sys.modules["bpy"] = _make_bpy_mock()

# ---------------------------------------------------------------------------
# Register src/ as the 'melvil' package
# ---------------------------------------------------------------------------
# src/ is the addon root. Because it isn't named 'melvil', Python won't find
# it via normal sys.path searching. We load it explicitly under the 'melvil'
# name so that `import melvil` and all relative imports within the package
# work as they do inside Blender.

_src = str(Path(__file__).parent.parent / "src")

if "melvil" not in sys.modules:
    _spec = importlib.util.spec_from_file_location(
        "melvil",
        f"{_src}/__init__.py",
        submodule_search_locations=[_src],
    )
    _mod = importlib.util.module_from_spec(_spec)
    _mod.__package__ = "melvil"
    sys.modules["melvil"] = _mod
    _spec.loader.exec_module(_mod)
