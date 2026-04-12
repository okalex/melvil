"""Tests for melvil.preferences."""

from melvil.preferences import MelvilPreferences


def test_bl_idname():
    """bl_idname must match the package name."""
    assert MelvilPreferences.bl_idname == "melvil"


def test_has_library_root():
    """Must declare a library_root annotation."""
    assert "library_root" in MelvilPreferences.__annotations__


def test_has_db_path():
    """Must declare a db_path annotation."""
    assert "db_path" in MelvilPreferences.__annotations__


def test_has_auto_generate_previews():
    """Must declare an auto_generate_previews annotation."""
    assert "auto_generate_previews" in MelvilPreferences.__annotations__


def test_has_material_preview_object():
    """Must declare a material_preview_object annotation."""
    assert "material_preview_object" in MelvilPreferences.__annotations__
