"""Add nullable preview_path column to assets table."""

from __future__ import annotations

import sqlite3


def upgrade(conn: sqlite3.Connection) -> None:
    conn.execute("ALTER TABLE assets ADD COLUMN preview_path TEXT")
