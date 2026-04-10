"""Initial schema: assets, tags, asset_tags."""

from __future__ import annotations

import sqlite3


def upgrade(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE assets (
            id          TEXT PRIMARY KEY,          -- UUID v4
            name        TEXT NOT NULL,
            type        TEXT NOT NULL,             -- 'MATERIAL' | 'MESH'
            blend_path  TEXT NOT NULL,             -- relative to library root
            created_at  TEXT NOT NULL,             -- ISO-8601
            updated_at  TEXT NOT NULL              -- ISO-8601
        );

        CREATE TABLE tags (
            id   INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        );

        CREATE TABLE asset_tags (
            asset_id TEXT NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
            tag_id   INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
            PRIMARY KEY (asset_id, tag_id)
        );

        CREATE INDEX idx_assets_type ON assets(type);
        CREATE INDEX idx_asset_tags_asset ON asset_tags(asset_id);
        CREATE INDEX idx_asset_tags_tag ON asset_tags(tag_id);
        """
    )
