"""Rebuild tags with UUID PK + timestamps; rebuild asset_tags with TEXT tag_id."""

from __future__ import annotations

import sqlite3
import uuid


def upgrade(conn: sqlite3.Connection) -> None:
    # 1. Snapshot existing data before dropping tables.
    existing_tags = conn.execute("SELECT id, name FROM tags").fetchall()
    existing_asset_tags = conn.execute(
        "SELECT asset_id, tag_id FROM asset_tags"
    ).fetchall()

    # Build mapping from old integer id to new UUID string.
    id_map: dict[int, str] = {row[0]: str(uuid.uuid4()) for row in existing_tags}

    # 2. Drop the old asset_tags table and its indexes.
    conn.execute("DROP INDEX IF EXISTS idx_asset_tags_asset")
    conn.execute("DROP INDEX IF EXISTS idx_asset_tags_tag")
    conn.execute("DROP TABLE IF EXISTS asset_tags")

    # 3. Drop the old tags table.
    conn.execute("DROP TABLE IF EXISTS tags")

    # 4. Create the new tags table with UUID PK and audit timestamps.
    conn.execute(
        """
        CREATE TABLE tags (
            id         TEXT PRIMARY KEY,
            name       TEXT NOT NULL UNIQUE,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # 5. Re-insert existing tags with new UUID ids.
    for row in existing_tags:
        conn.execute(
            "INSERT INTO tags (id, name) VALUES (?, ?)",
            (id_map[row[0]], row[1]),
        )

    # 6. Create the new asset_tags table (tag_id is now TEXT).
    conn.execute(
        """
        CREATE TABLE asset_tags (
            asset_id TEXT NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
            tag_id   TEXT NOT NULL REFERENCES tags(id)   ON DELETE CASCADE,
            PRIMARY KEY (asset_id, tag_id)
        )
        """
    )

    # 7. Re-insert existing asset_tag rows using the new UUID tag ids.
    for row in existing_asset_tags:
        asset_id, old_tag_id = row[0], row[1]
        new_tag_id = id_map.get(old_tag_id)
        if new_tag_id is not None:
            conn.execute(
                "INSERT OR IGNORE INTO asset_tags (asset_id, tag_id) VALUES (?, ?)",
                (asset_id, new_tag_id),
            )

    # 8. Create indexes.
    conn.execute("CREATE INDEX idx_asset_tags_asset_id ON asset_tags(asset_id)")
    conn.execute("CREATE INDEX idx_asset_tags_tag_id   ON asset_tags(tag_id)")
    conn.execute("CREATE INDEX idx_tags_name           ON tags(name)")
