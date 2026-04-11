"""
Library helpers: resolve paths from preferences and ensure the database
is initialised.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import bpy

from ..db import open_db

BLENDER_ASSET_LIBRARY_NAME = "Melvil Assets"


class LibraryNotConfiguredError(Exception):
    """Raised when an operation requires a library root that hasn't been set."""


def get_prefs():
    from ..preferences import MelvilPreferences
    return bpy.context.preferences.addons[MelvilPreferences.bl_idname].preferences


def _os_app_data_dir() -> Path:
    """
    Return the platform-appropriate application data directory for Melvil.

    - macOS:  ~/Library/Application Support/Melvil
    - Windows: %APPDATA%/Melvil
    - Linux:   $XDG_DATA_HOME/melvil  (falls back to ~/.local/share/melvil)
    """
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        return base / "Melvil"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Melvil"
    # Linux / other POSIX
    xdg = os.environ.get("XDG_DATA_HOME", "")
    base = Path(xdg) if xdg else Path.home() / ".local" / "share"
    return base / "melvil"


def _default_library_root() -> Path:
    """
    Return the default assets directory when no explicit path is configured.

    Resolves to the platform app data dir + 'assets/', e.g.:
        ~/Library/Application Support/Melvil/assets/   (macOS)
        %APPDATA%/Melvil/assets/                        (Windows)
        ~/.local/share/melvil/assets/                   (Linux)
    """
    return _os_app_data_dir() / "assets"


def resolve_library_root() -> Path:
    """
    Return the absolute path to the library root directory.

    When the library_root preference is empty the default OS app data location
    is used (see ``_default_library_root``).  The library root is where managed
    .blend files and the textures/ subfolder are stored.
    """
    prefs = get_prefs()
    root = prefs.library_root.strip()
    if not root:
        return _default_library_root()
    return Path(bpy.path.abspath(root))


def _default_db_path() -> Path:
    """
    Return the default DB path in the platform app data directory.

    Resolves to, e.g.:
        ~/Library/Application Support/Melvil/melvil.db   (macOS)
        %APPDATA%/Melvil/melvil.db                        (Windows)
        ~/.local/share/melvil/melvil.db                   (Linux)
    """
    return _os_app_data_dir() / "melvil.db"


def resolve_db_path() -> Path:
    """
    Return the absolute path to the SQLite DB file.
    Uses the user-specified db_path if set, otherwise the default location
    inside Blender's per-extension user data directory.
    """
    prefs = get_prefs()
    db_path = prefs.db_path.strip()
    if db_path:
        return Path(bpy.path.abspath(db_path))

    return _default_db_path()


def sync_blender_asset_library() -> None:
    """
    Ensure Blender's asset library list contains a 'Melvil Assets' entry that
    points to the current assets directory.

    This is idempotent: it creates the entry if absent, and updates the path if
    it differs from the current library root.  Called on every addon startup and
    whenever the library_root preference changes.
    """
    assets_dir = str(resolve_library_root())
    asset_libraries = bpy.context.preferences.filepaths.asset_libraries

    # Look for an existing entry by name.
    for lib in asset_libraries:
        if lib.name == BLENDER_ASSET_LIBRARY_NAME:
            if lib.path != assets_dir:
                lib.path = assets_dir
            return

    # Not found — add a new entry.
    bpy.ops.preferences.asset_library_add(directory=assets_dir)
    # The newly added entry is always appended last.
    new_lib = asset_libraries[-1]
    new_lib.name = BLENDER_ASSET_LIBRARY_NAME


def ensure_db() -> None:
    """
    Open the database (creating it and running any pending migrations).
    The directory is created if it doesn't exist.
    """
    path = resolve_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open_db(path):
        pass  # migrations are applied inside open_db; nothing else needed here
