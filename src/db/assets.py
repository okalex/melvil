"""
CRUD helpers for the `assets` table.

All functions accept a sqlite3.Connection so callers control transactions.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Optional

from .kits import DEFAULT_KIT_ID


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def insert_asset(
    conn: sqlite3.Connection,
    *,
    id: str,
    name: str,
    type: str,
    blend_path: str,
    kit_id: str = DEFAULT_KIT_ID,
    preview_path: Optional[str] = None,
) -> None:
    now = _now()
    conn.execute(
        """
        INSERT INTO assets (id, name, type, blend_path, kit_id, preview_path, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (id, name, type, blend_path, kit_id, preview_path, now, now),
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
    kit_id: Optional[str] = None,
) -> list[sqlite3.Row]:
    conditions: list[str] = []
    params: list[object] = []
    if type is not None:
        conditions.append("type = ?")
        params.append(type)
    if kit_id is not None:
        conditions.append("kit_id = ?")
        params.append(kit_id)
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    return conn.execute(
        f"SELECT * FROM assets {where} ORDER BY name",  # noqa: S608
        params,
    ).fetchall()


def update_asset(
    conn: sqlite3.Connection,
    id: str,
    *,
    name: Optional[str] = None,
    blend_path: Optional[str] = None,
    kit_id: Optional[str] = None,
    preview_path: Optional[str] = None,
) -> None:
    fields: list[str] = []
    params: list[object] = []
    if name is not None:
        fields.append("name = ?")
        params.append(name)
    if blend_path is not None:
        fields.append("blend_path = ?")
        params.append(blend_path)
    if kit_id is not None:
        fields.append("kit_id = ?")
        params.append(kit_id)
    if preview_path is not None:
        fields.append("preview_path = ?")
        params.append(preview_path)
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
