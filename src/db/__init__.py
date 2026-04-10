"""
db package — SQLite database layer.

Public API:
    open_db(path)          context manager → sqlite3.Connection (migrated)
    assets.*               CRUD for the assets table
    tags.*                 CRUD for tags and asset_tags tables
"""

from .connection import open_db

__all__ = ["open_db"]
