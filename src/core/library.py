"""
Library helpers: resolve paths from preferences and ensure the database
is initialised.
"""

from __future__ import annotations

from pathlib import Path

import bpy

from ..db import open_db


class LibraryNotConfiguredError(Exception):
    """Raised when an operation requires a library root that hasn't been set."""


def get_prefs():
    from ..preferences import MelvilPreferences
    return bpy.context.preferences.addons[MelvilPreferences.bl_idname].preferences


def _default_library_root() -> Path:
    """
    Return the default library root when no explicit path is configured.

    Resolves to something like:
        ~/Library/Application Support/Blender/5.0/datafiles/melvil
    """
    return Path(bpy.utils.user_resource("DATAFILES", path="melvil", create=True))


def resolve_library_root() -> Path:
    """
    Return the absolute path to the library root directory.

    When the library_root preference is empty the default location inside
    Blender's user data files directory is used (see ``_default_library_root``).
    The library root is where managed .blend files and the textures/ subfolder
    are stored.
    """
    prefs = get_prefs()
    root = prefs.library_root.strip()
    if not root:
        return _default_library_root()
    return Path(bpy.path.abspath(root))


def _default_db_path() -> Path:
    """
    Return the default DB path using Blender's user config directory.
    This is stable across extension reinstalls.

    Resolves to something like:
        ~/Library/Application Support/Blender/5.0/config/melvil/melvil.db
    """
    config_dir = bpy.utils.user_resource("CONFIG", path="melvil", create=True)
    return Path(config_dir) / "melvil.db"


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


def ensure_db() -> None:
    """
    Open the database (creating it and running any pending migrations).
    The directory is created if it doesn't exist.
    """
    path = resolve_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open_db(path):
        pass  # migrations are applied inside open_db; nothing else needed here
