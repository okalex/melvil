"""Tests for core/library.py — path resolution helpers."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch


class TestOsAppDataDir:
    def test_returns_path(self):
        from melvil.core.library import _os_app_data_dir

        result = _os_app_data_dir()
        assert isinstance(result, Path)

    def test_darwin_uses_application_support(self):
        from melvil.core.library import _os_app_data_dir

        with patch.object(sys, "platform", "darwin"):
            result = _os_app_data_dir()

        assert "Application Support" in str(result)
        assert result.name == "Melvil"

    def test_win32_uses_appdata_env(self, tmp_path):
        from melvil.core.library import _os_app_data_dir

        with patch.object(sys, "platform", "win32"), \
             patch.dict("os.environ", {"APPDATA": str(tmp_path)}):
            result = _os_app_data_dir()

        assert result == tmp_path / "Melvil"

    def test_linux_uses_xdg_data_home(self, tmp_path):
        from melvil.core.library import _os_app_data_dir

        with patch.object(sys, "platform", "linux"), \
             patch.dict("os.environ", {"XDG_DATA_HOME": str(tmp_path)}):
            result = _os_app_data_dir()

        assert result == tmp_path / "melvil"

    def test_linux_falls_back_to_local_share(self):
        from melvil.core.library import _os_app_data_dir
        import os

        env_without_xdg = {k: v for k, v in os.environ.items() if k != "XDG_DATA_HOME"}
        with patch.object(sys, "platform", "linux"), \
             patch.dict("os.environ", env_without_xdg, clear=True):
            result = _os_app_data_dir()

        assert result == Path.home() / ".local" / "share" / "melvil"


class TestDefaultLibraryRoot:
    def test_returns_path(self):
        from melvil.core.library import _default_library_root

        result = _default_library_root()
        assert isinstance(result, Path)

    def test_ends_with_assets_under_melvil_dir(self):
        from melvil.core.library import _default_library_root

        result = _default_library_root()
        assert result.name == "assets"
        assert "melvil" in str(result).lower() or "Melvil" in str(result)

    def test_is_child_of_os_app_data_dir(self):
        from melvil.core.library import _default_library_root, _os_app_data_dir

        assert _default_library_root() == _os_app_data_dir() / "assets"


class TestDefaultDbPath:
    def test_returns_path(self):
        from melvil.core.library import _default_db_path

        result = _default_db_path()
        assert isinstance(result, Path)

    def test_db_filename(self):
        from melvil.core.library import _default_db_path

        result = _default_db_path()
        assert result.name == "melvil.db"

    def test_is_sibling_to_assets_dir(self):
        from melvil.core.library import _default_db_path, _os_app_data_dir

        assert _default_db_path() == _os_app_data_dir() / "melvil.db"


class TestResolveLibraryRoot:
    def _mock_prefs(self, library_root=""):
        prefs = MagicMock()
        prefs.library_root = library_root
        return prefs

    def test_returns_default_when_library_root_empty(self):
        from melvil.core.library import resolve_library_root

        with patch("melvil.core.library.get_prefs", return_value=self._mock_prefs("")):
            result = resolve_library_root()

        assert isinstance(result, Path)
        assert result != Path("")

    def test_default_ends_with_assets(self):
        from melvil.core.library import resolve_library_root

        with patch("melvil.core.library.get_prefs", return_value=self._mock_prefs("")):
            result = resolve_library_root()

        assert result.name == "assets"

    def test_uses_explicit_library_root_when_set(self):
        from melvil.core.library import resolve_library_root

        with patch("melvil.core.library.get_prefs", return_value=self._mock_prefs("/custom/lib")):
            result = resolve_library_root()

        assert result == Path("/custom/lib")

    def test_strips_whitespace_from_library_root(self):
        from melvil.core.library import resolve_library_root

        with patch("melvil.core.library.get_prefs", return_value=self._mock_prefs("  ")):
            result = resolve_library_root()

        # Whitespace-only → falls back to default, which ends with 'assets'
        assert result.name == "assets"


class TestSyncBlenderAssetLibrary:
    def _mock_prefs(self, library_root=""):
        prefs = MagicMock()
        prefs.library_root = library_root
        return prefs

    def _fresh_asset_libraries(self):
        """Return a fresh real list to use as asset_libraries in tests."""
        return []

    def test_creates_entry_when_absent(self):
        import bpy
        from melvil.core.library import BLENDER_ASSET_LIBRARY_NAME, sync_blender_asset_library

        asset_libraries = self._fresh_asset_libraries()
        bpy.context.preferences.filepaths.asset_libraries = asset_libraries

        with patch("melvil.core.library.get_prefs", return_value=self._mock_prefs("")):
            sync_blender_asset_library()

        assert len(asset_libraries) == 1
        assert asset_libraries[0].name == BLENDER_ASSET_LIBRARY_NAME

    def test_new_entry_path_matches_library_root(self):
        import bpy
        from melvil.core.library import sync_blender_asset_library

        asset_libraries = self._fresh_asset_libraries()
        bpy.context.preferences.filepaths.asset_libraries = asset_libraries

        with patch("melvil.core.library.get_prefs", return_value=self._mock_prefs("/my/assets")):
            sync_blender_asset_library()

        assert asset_libraries[0].path == "/my/assets"

    def test_updates_path_when_entry_exists_with_old_path(self):
        import bpy
        from melvil.core.library import BLENDER_ASSET_LIBRARY_NAME, sync_blender_asset_library

        existing = MagicMock()
        existing.name = BLENDER_ASSET_LIBRARY_NAME
        existing.path = "/old/path"
        asset_libraries = [existing]
        bpy.context.preferences.filepaths.asset_libraries = asset_libraries

        with patch("melvil.core.library.get_prefs", return_value=self._mock_prefs("/new/path")):
            sync_blender_asset_library()

        assert existing.path == "/new/path"
        # Should not have added a new entry
        assert len(asset_libraries) == 1

    def test_no_duplicate_when_path_already_correct(self):
        import bpy
        from melvil.core.library import BLENDER_ASSET_LIBRARY_NAME, sync_blender_asset_library

        existing = MagicMock()
        existing.name = BLENDER_ASSET_LIBRARY_NAME
        existing.path = "/my/assets"
        asset_libraries = [existing]
        bpy.context.preferences.filepaths.asset_libraries = asset_libraries

        with patch("melvil.core.library.get_prefs", return_value=self._mock_prefs("/my/assets")):
            sync_blender_asset_library()

        assert len(asset_libraries) == 1

    def test_does_not_affect_other_libraries(self):
        import bpy
        from melvil.core.library import sync_blender_asset_library

        other = MagicMock()
        other.name = "Other Library"
        other.path = "/other/path"
        asset_libraries = [other]
        bpy.context.preferences.filepaths.asset_libraries = asset_libraries

        with patch("melvil.core.library.get_prefs", return_value=self._mock_prefs("/my/assets")):
            sync_blender_asset_library()

        # The original entry should be untouched
        assert asset_libraries[0].name == "Other Library"
        assert asset_libraries[0].path == "/other/path"
        # A new Melvil entry should have been added
        assert len(asset_libraries) == 2
