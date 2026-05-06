"""Tests for blammo.preferences."""

from blammo.preferences import BlammoPreferences


def test_bl_idname():
    """bl_idname must match the package name."""
    assert BlammoPreferences.bl_idname == "blammo"


def test_has_library_root():
    """Must declare a library_root annotation."""
    assert "library_root" in BlammoPreferences.__annotations__


def test_has_db_path():
    """Must declare a db_path annotation."""
    assert "db_path" in BlammoPreferences.__annotations__


def test_has_auto_generate_previews():
    """Must declare an auto_generate_previews annotation."""
    assert "auto_generate_previews" in BlammoPreferences.__annotations__


def test_has_material_preview_object():
    """Must declare a material_preview_object annotation."""
    assert "material_preview_object" in BlammoPreferences.__annotations__
