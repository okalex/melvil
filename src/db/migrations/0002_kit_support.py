"""Add kits table and kit_id FK column on assets."""

from __future__ import annotations

import sqlite3

# Fixed UUID for the default "General" kit; stable across all installations.
DEFAULT_KIT_ID = "00000000-0000-4000-8000-000000000001"


def upgrade(conn: sqlite3.Connection) -> None:
    # Clean up any partial state from a failed previous run (dev-time only).
    conn.execute("DROP TABLE IF EXISTS kits")
    conn.execute("DROP TABLE IF EXISTS assets_new")

    # 1. Create the kits table.
    conn.execute(
        """
        CREATE TABLE kits (
            id           TEXT PRIMARY KEY,
            name         TEXT NOT NULL,
            description  TEXT,
            created_at   TEXT NOT NULL,
            updated_at   TEXT NOT NULL,
            workspace_id TEXT,
            owner_id     TEXT
        )
        """
    )

    # 2. Insert the default "General" kit.
    conn.execute(
        "INSERT INTO kits (id, name, created_at, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
        (DEFAULT_KIT_ID, "General"),
    )

    # 3. Add kit_id as nullable — SQLite forbids ADD COLUMN with both a
    #    REFERENCES constraint and a non-NULL DEFAULT.
    conn.execute("ALTER TABLE assets ADD COLUMN kit_id TEXT")

    # 4. Assign all existing assets to the General kit.
    conn.execute("UPDATE assets SET kit_id = ?", (DEFAULT_KIT_ID,))

    # 5. Rebuild the assets table to enforce NOT NULL + FK.
    #    SQLite does not support ALTER COLUMN, so the standard approach is to
    #    create a replacement table, copy data, drop the original, and rename.
    conn.execute(
        """
        CREATE TABLE assets_new (
            id          TEXT PRIMARY KEY,
            name        TEXT NOT NULL,
            type        TEXT NOT NULL,
            blend_path  TEXT NOT NULL,
            kit_id      TEXT NOT NULL REFERENCES kits(id),
            created_at  TEXT NOT NULL,
            updated_at  TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        INSERT INTO assets_new (id, name, type, blend_path, kit_id, created_at, updated_at)
        SELECT id, name, type, blend_path, kit_id, created_at, updated_at FROM assets
        """
    )
    conn.execute("DROP TABLE assets")
    conn.execute("ALTER TABLE assets_new RENAME TO assets")
    conn.execute("CREATE INDEX idx_assets_type ON assets(type)")
