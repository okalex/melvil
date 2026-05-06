"""
Database connection and migration runner.

Usage:
    from blammo.db.connection import open_db

    with open_db("/path/to/blammo.db") as conn:
        ...
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from .migrations import LATEST_VERSION, MIGRATIONS


def _get_version(conn: sqlite3.Connection) -> int:
    return conn.execute("PRAGMA user_version").fetchone()[0]


def _set_version(conn: sqlite3.Connection, version: int) -> None:
    # user_version is an integer pragma; parameterised queries are not
    # supported for PRAGMA statements, but the value is always an int we
    # control so this is safe.
    conn.execute(f"PRAGMA user_version = {version:d}")


def migrate(conn: sqlite3.Connection) -> None:
    """Apply any pending migrations to *conn* and advance user_version."""
    current = _get_version(conn)
    pending = MIGRATIONS[current:]  # migrations are 0-indexed; version is 1-based count
    for i, migration in enumerate(pending):
        new_version = current + i + 1
        with conn:  # each migration is its own transaction
            migration(conn)
            _set_version(conn, new_version)


def _configure(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row


@contextmanager
def open_db(path: str | Path) -> Generator[sqlite3.Connection, None, None]:
    """
    Open (or create) the SQLite database at *path*, run pending migrations,
    and yield the connection. Closes the connection on exit.
    """
    conn = sqlite3.connect(str(path))
    try:
        _configure(conn)
        migrate(conn)
        yield conn
    finally:
        conn.close()
