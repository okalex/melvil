"""
CRUD helpers for the `kits` table.

All functions accept a sqlite3.Connection so callers control transactions.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Optional

# Fixed UUID for the default "General" kit; matches the migration seed.
DEFAULT_KIT_ID = "00000000-0000-4000-8000-000000000001"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def insert_kit(
    conn: sqlite3.Connection,
    *,
    id: str,
    name: str,
    description: Optional[str] = None,
) -> None:
    now = _now()
    conn.execute(
        """
        INSERT INTO kits (id, name, description, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (id, name, description, now, now),
    )


def get_kit(conn: sqlite3.Connection, id: str) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM kits WHERE id = ?", (id,)
    ).fetchone()


def get_kit_by_name(conn: sqlite3.Connection, name: str) -> Optional[sqlite3.Row]:
    """Case-insensitive lookup by name."""
    return conn.execute(
        "SELECT * FROM kits WHERE lower(name) = lower(?)", (name,)
    ).fetchone()


def list_kits(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM kits ORDER BY name").fetchall()


def update_kit(
    conn: sqlite3.Connection,
    id: str,
    *,
    name: Optional[str] = None,
    description: Optional[str] = None,
) -> None:
    fields: list[str] = []
    params: list[object] = []
    if name is not None:
        fields.append("name = ?")
        params.append(name)
    if description is not None:
        fields.append("description = ?")
        params.append(description)
    if not fields:
        return
    fields.append("updated_at = ?")
    params.append(_now())
    params.append(id)
    conn.execute(
        f"UPDATE kits SET {', '.join(fields)} WHERE id = ?",  # noqa: S608
        params,
    )
