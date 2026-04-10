"""
CRUD helpers for the `tags` and `asset_tags` tables.
"""

from __future__ import annotations

import sqlite3
from typing import Optional


def get_or_create_tag(conn: sqlite3.Connection, name: str) -> int:
    """Return the id of tag *name*, creating it if it doesn't exist."""
    row = conn.execute("SELECT id FROM tags WHERE name = ?", (name,)).fetchone()
    if row:
        return row["id"]
    cur = conn.execute("INSERT INTO tags (name) VALUES (?)", (name,))
    return cur.lastrowid  # type: ignore[return-value]


def get_tag(conn: sqlite3.Connection, name: str) -> Optional[sqlite3.Row]:
    return conn.execute("SELECT * FROM tags WHERE name = ?", (name,)).fetchone()


def list_tags(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM tags ORDER BY name").fetchall()


def add_asset_tag(conn: sqlite3.Connection, asset_id: str, tag_name: str) -> None:
    tag_id = get_or_create_tag(conn, tag_name)
    conn.execute(
        "INSERT OR IGNORE INTO asset_tags (asset_id, tag_id) VALUES (?, ?)",
        (asset_id, tag_id),
    )


def remove_asset_tag(conn: sqlite3.Connection, asset_id: str, tag_name: str) -> None:
    row = get_tag(conn, tag_name)
    if row is None:
        return
    conn.execute(
        "DELETE FROM asset_tags WHERE asset_id = ? AND tag_id = ?",
        (asset_id, row["id"]),
    )


def get_asset_tags(conn: sqlite3.Connection, asset_id: str) -> list[str]:
    rows = conn.execute(
        """
        SELECT t.name FROM tags t
        JOIN asset_tags at ON at.tag_id = t.id
        WHERE at.asset_id = ?
        ORDER BY t.name
        """,
        (asset_id,),
    ).fetchall()
    return [r["name"] for r in rows]


def list_assets_for_tag(conn: sqlite3.Connection, tag_name: str) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT a.* FROM assets a
        JOIN asset_tags at ON at.asset_id = a.id
        JOIN tags t ON t.id = at.tag_id
        WHERE t.name = ?
        ORDER BY a.name
        """,
        (tag_name,),
    ).fetchall()
