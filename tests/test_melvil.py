"""Tests for the top-level melvil package (register/unregister lifecycle)."""

import bpy
import melvil


def _reset_register_mocks():
    bpy.utils.register_class.reset_mock()
    bpy.utils.unregister_class.reset_mock()


def test_addon_importable():
    """The top-level melvil package must import cleanly."""
    pass  # import at module level above is the test


def test_register_does_not_raise():
    """register() must complete without raising."""
    _reset_register_mocks()
    melvil.register()


def test_unregister_does_not_raise():
    """unregister() must complete without raising."""
    _reset_register_mocks()
    melvil.register()
    melvil.unregister()


def test_register_registers_preferences():
    """register() must register MelvilPreferences with bpy."""
    from melvil.preferences import MelvilPreferences

    _reset_register_mocks()
    melvil.register()

    registered_classes = [
        call.args[0] for call in bpy.utils.register_class.call_args_list
    ]
    assert MelvilPreferences in registered_classes


def test_unregister_unregisters_preferences():
    """unregister() must unregister MelvilPreferences with bpy."""
    from melvil.preferences import MelvilPreferences

    _reset_register_mocks()
    melvil.register()
    melvil.unregister()

    unregistered_classes = [
        call.args[0] for call in bpy.utils.unregister_class.call_args_list
    ]
    assert MelvilPreferences in unregistered_classes
