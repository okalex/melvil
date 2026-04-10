"""
Library helpers: resolve the effective DB path from preferences and
ensure the database is initialised (migrations applied).
"""

from __future__ import annotations

from pathlib import Path

import bpy

from ..db import open_db


def get_prefs():
    from ..preferences import MelvilPreferences
    return bpy.context.preferences.addons[MelvilPreferences.bl_idname].preferences


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
