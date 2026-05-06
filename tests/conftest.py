"""
Configure bpy mock and import path for tests.

Blender's bpy module is only available at runtime inside Blender, so we mock
it here. We also register src/ as the 'blammo' package so that tests can
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

    class NODE_MT_context_menu:
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

    class NODE_MT_add:
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
    bpy_types.NODE_MT_context_menu = NODE_MT_context_menu
    bpy_types.NODE_MT_add = NODE_MT_add

    class SpaceView3D:
        """Minimal SpaceView3D stand-in with draw_handler_add/remove."""
        draw_handler_add = MagicMock(return_value="FAKE_HANDLE")
        draw_handler_remove = MagicMock()

    bpy_types.SpaceView3D = SpaceView3D

    class WindowManager:
        """Minimal WindowManager stand-in for attribute assignment in register()."""

    class Scene:
        """Minimal Scene stand-in for attribute assignment in register()."""

    bpy_types.WindowManager = WindowManager
    bpy_types.Scene = Scene

    bpy.types = bpy_types
    sys.modules["bpy.types"] = bpy_types

    # bpy.utils
    bpy_utils = types.ModuleType("bpy.utils")
    bpy_utils.register_class = MagicMock()
    bpy_utils.unregister_class = MagicMock()
    bpy_utils.extension_path_user = MagicMock(return_value="/tmp/blammo_test_data")
    bpy_utils.user_resource = MagicMock(return_value="/tmp/blammo_test_config")
    bpy_utils_previews = types.ModuleType("bpy.utils.previews")
    bpy_utils_previews.new = MagicMock(return_value=MagicMock())
    bpy_utils_previews.remove = MagicMock()
    bpy_utils.previews = bpy_utils_previews
    sys.modules["bpy.utils.previews"] = bpy_utils_previews
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

    # bpy.ops / bpy.data / bpy.app — light mocks
    bpy.ops = MagicMock()
    bpy.data = MagicMock()
    bpy.app = MagicMock()

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
    mock_context.preferences.system.ui_scale = 1.0
    bpy.context = mock_context

    # Make bpy.ops.preferences.asset_library_add() append a stub entry so that
    # sync_blender_asset_library() can modify asset_libraries[-1] after the call.
    def _mock_asset_library_add(directory=""):
        lib = MagicMock()
        lib.name = ""
        lib.path = directory
        mock_context.preferences.filepaths.asset_libraries.append(lib)

    bpy.ops.preferences.asset_library_add.side_effect = _mock_asset_library_add

    return bpy


# Install the mock before any addon module is imported.
if "bpy" not in sys.modules:
    sys.modules["bpy"] = _make_bpy_mock()

# ---------------------------------------------------------------------------
# Mock Blender-only C modules (gpu, blf, gpu_extras)
# ---------------------------------------------------------------------------
# These are only available inside Blender's embedded Python.  gpu/grid_list.py
# imports them at module level, so they must exist before exec_module runs.

if "gpu" not in sys.modules:
    _gpu = types.ModuleType("gpu")
    _gpu.shader = MagicMock()
    _gpu.state = MagicMock()
    _gpu.texture = MagicMock()
    sys.modules["gpu"] = _gpu

if "blf" not in sys.modules:
    _blf = types.ModuleType("blf")
    _blf.size = MagicMock()
    _blf.color = MagicMock()
    _blf.position = MagicMock()
    _blf.draw = MagicMock()
    _blf.dimensions = MagicMock(return_value=(0.0, 0.0))
    sys.modules["blf"] = _blf

if "gpu_extras" not in sys.modules:
    _gpu_extras = types.ModuleType("gpu_extras")
    sys.modules["gpu_extras"] = _gpu_extras
if "gpu_extras.batch" not in sys.modules:
    _gpu_extras_batch = types.ModuleType("gpu_extras.batch")
    _gpu_extras_batch.batch_for_shader = MagicMock()
    sys.modules["gpu_extras.batch"] = _gpu_extras_batch

# ---------------------------------------------------------------------------
# Register src/ as the 'blammo' package
# ---------------------------------------------------------------------------
# src/ is the addon root. Because it isn't named 'blammo', Python won't find
# it via normal sys.path searching. We load it explicitly under the 'blammo'
# name so that `import blammo` and all relative imports within the package
# work as they do inside Blender.

_src = str(Path(__file__).parent.parent / "src")

if "blammo" not in sys.modules:
    _spec = importlib.util.spec_from_file_location(
        "blammo",
        f"{_src}/__init__.py",
        submodule_search_locations=[_src],
    )
    _mod = importlib.util.module_from_spec(_spec)
    _mod.__package__ = "blammo"
    sys.modules["blammo"] = _mod
    _spec.loader.exec_module(_mod)
