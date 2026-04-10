"""Tests for core/library.py — path resolution helpers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch


class TestResolveLibraryRoot:
    def _mock_prefs(self, library_root=""):
        prefs = MagicMock()
        prefs.library_root = library_root
        return prefs

    def test_returns_default_when_library_root_empty(self):
        from melvil.core.library import resolve_library_root

        with patch("melvil.core.library.get_prefs", return_value=self._mock_prefs("")):
            result = resolve_library_root()

        # Should be the DATAFILES/melvil default, not raise
        assert isinstance(result, Path)
        assert result != Path("")

    def test_default_contains_melvil(self):
        from melvil.core.library import resolve_library_root

        with patch("melvil.core.library.get_prefs", return_value=self._mock_prefs("")):
            result = resolve_library_root()

        assert "melvil" in str(result).lower()

    def test_uses_explicit_library_root_when_set(self):
        from melvil.core.library import resolve_library_root
        import bpy

        with patch("melvil.core.library.get_prefs", return_value=self._mock_prefs("/custom/lib")):
            result = resolve_library_root()

        # bpy.path.abspath is identity in tests
        assert result == Path("/custom/lib")

    def test_strips_whitespace_from_library_root(self):
        from melvil.core.library import resolve_library_root

        with patch("melvil.core.library.get_prefs", return_value=self._mock_prefs("  ")):
            result = resolve_library_root()

        # Whitespace-only → falls back to default
        assert "melvil" in str(result).lower()


class TestDefaultLibraryRoot:
    def test_returns_path(self):
        from melvil.core.library import _default_library_root

        result = _default_library_root()
        assert isinstance(result, Path)

    def test_ends_with_melvil(self):
        from melvil.core.library import _default_library_root

        result = _default_library_root()
        # In real Blender this is <datafiles>/melvil; in tests the bpy mock
        # returns the whole path so just assert "melvil" appears somewhere.
        assert "melvil" in str(result)
