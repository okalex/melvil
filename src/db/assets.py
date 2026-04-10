"""
CRUD helpers for the `assets` table.

All functions accept a sqlite3.Connection so callers control transactions.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Optional


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def insert_asset(
    conn: sqlite3.Connection,
    *,
    id: str,
    name: str,
    type: str,
    blend_path: str,
) -> None:
    now = _now()
    conn.execute(
        """
        INSERT INTO assets (id, name, type, blend_path, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (id, name, type, blend_path, now, now),
    )


def get_asset(
    conn: sqlite3.Connection, id: str
) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM assets WHERE id = ?", (id,)
    ).fetchone()


def list_assets(
    conn: sqlite3.Connection,
    *,
    type: Optional[str] = None,
) -> list[sqlite3.Row]:
    if type is not None:
        return conn.execute(
            "SELECT * FROM assets WHERE type = ? ORDER BY name", (type,)
        ).fetchall()
    return conn.execute(
        "SELECT * FROM assets ORDER BY name"
    ).fetchall()


def update_asset(
    conn: sqlite3.Connection,
    id: str,
    *,
    name: Optional[str] = None,
    blend_path: Optional[str] = None,
) -> None:
    fields: list[str] = []
    params: list[object] = []
    if name is not None:
        fields.append("name = ?")
        params.append(name)
    if blend_path is not None:
        fields.append("blend_path = ?")
        params.append(blend_path)
    if not fields:
        return
    fields.append("updated_at = ?")
    params.append(_now())
    params.append(id)
    conn.execute(
        f"UPDATE assets SET {', '.join(fields)} WHERE id = ?",  # noqa: S608
        params,
    )


def delete_asset(conn: sqlite3.Connection, id: str) -> None:
    conn.execute("DELETE FROM assets WHERE id = ?", (id,))
