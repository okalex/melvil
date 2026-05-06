"""Tests for the top-level blammo package (register/unregister lifecycle)."""

import bpy
import blammo


def _reset_register_mocks():
    bpy.utils.register_class.reset_mock()
    bpy.utils.unregister_class.reset_mock()
    bpy.app.timers.register.reset_mock()


def test_addon_importable():
    """The top-level blammo package must import cleanly."""
    pass  # import at module level above is the test


def test_register_does_not_raise():
    """register() must complete without raising."""
    _reset_register_mocks()
    blammo.register()


def test_unregister_does_not_raise():
    """unregister() must complete without raising."""
    _reset_register_mocks()
    blammo.register()
    blammo.unregister()


def test_register_registers_preferences():
    """register() must register BlammoPreferences with bpy."""
    from blammo.preferences import BlammoPreferences

    _reset_register_mocks()
    blammo.register()

    registered_classes = [
        call.args[0] for call in bpy.utils.register_class.call_args_list
    ]
    assert BlammoPreferences in registered_classes


def test_unregister_unregisters_preferences():
    """unregister() must unregister BlammoPreferences with bpy."""
    from blammo.preferences import BlammoPreferences

    _reset_register_mocks()
    blammo.register()
    blammo.unregister()

    unregistered_classes = [
        call.args[0] for call in bpy.utils.unregister_class.call_args_list
    ]
    assert BlammoPreferences in unregistered_classes


def test_register_schedules_asset_library_sync():
    """register() must schedule a deferred sync of the Blender asset library."""
    _reset_register_mocks()
    blammo.register()

    bpy.app.timers.register.assert_called_once()
    args, kwargs = bpy.app.timers.register.call_args
    assert callable(args[0])
    assert kwargs.get("first_interval") == 0.0
