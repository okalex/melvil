"""
CRUD helpers for the `tags` and `asset_tags` tables.
"""

from __future__ import annotations

import re
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Optional


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_tag(name: str) -> str:
    """Normalize a tag name: strip, collapse whitespace, lowercase.

    Returns an empty string if the result would be empty (caller should discard).
    """
    return re.sub(r"\s+", " ", name.strip()).lower()


# ---------------------------------------------------------------------------
# Tag table helpers
# ---------------------------------------------------------------------------


def get_or_create_tag(conn: sqlite3.Connection, name: str) -> str:
    """Return the UUID of tag *name* (normalized), creating it if needed."""
    normalized = normalize_tag(name)
    if not normalized:
        raise ValueError(f"Tag name {name!r} normalizes to an empty string")
    row = conn.execute("SELECT id FROM tags WHERE name = ?", (normalized,)).fetchone()
    if row:
        return row["id"]
    tag_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO tags (id, name) VALUES (?, ?)",
        (tag_id, normalized),
    )
    return tag_id


def get_tag_by_id(conn: sqlite3.Connection, tag_id: str) -> Optional[sqlite3.Row]:
    return conn.execute("SELECT * FROM tags WHERE id = ?", (tag_id,)).fetchone()


def get_tag_by_name(conn: sqlite3.Connection, name: str) -> Optional[sqlite3.Row]:
    """Look up a tag by its normalized name."""
    return conn.execute(
        "SELECT * FROM tags WHERE name = ?", (normalize_tag(name),)
    ).fetchone()


def list_tags(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM tags ORDER BY name").fetchall()


def list_tags_with_usage(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Return all tags ordered by name, each with a ``usage_count`` column."""
    return conn.execute(
        """
        SELECT t.*, COUNT(at.asset_id) AS usage_count
        FROM tags t
        LEFT JOIN asset_tags at ON at.tag_id = t.id
        GROUP BY t.id
        ORDER BY t.name
        """
    ).fetchall()


def rename_tag(conn: sqlite3.Connection, tag_id: str, new_name: str) -> None:
    """Rename a tag globally.  Raises ValueError on empty or conflicting name."""
    normalized = normalize_tag(new_name)
    if not normalized:
        raise ValueError(f"New tag name {new_name!r} normalizes to an empty string")
    conflict = conn.execute(
        "SELECT id FROM tags WHERE name = ? AND id != ?", (normalized, tag_id)
    ).fetchone()
    if conflict:
        raise ValueError(f"A tag named {normalized!r} already exists")
    conn.execute(
        "UPDATE tags SET name = ?, updated_at = ? WHERE id = ?",
        (normalized, _now(), tag_id),
    )


def delete_tag(conn: sqlite3.Connection, tag_id: str) -> None:
    """Delete a tag globally (cascades to asset_tags via FK)."""
    conn.execute("DELETE FROM tags WHERE id = ?", (tag_id,))


def autocomplete_tags(
    conn: sqlite3.Connection, query: str, limit: int = 10
) -> list[sqlite3.Row]:
    """Return up to *limit* tags whose name contains *query* as a substring.

    Results are ordered by usage count descending so common tags appear first.
    """
    normalized_query = normalize_tag(query)
    return conn.execute(
        """
        SELECT t.id, t.name, COUNT(at.asset_id) AS usage_count
        FROM tags t
        LEFT JOIN asset_tags at ON at.tag_id = t.id
        WHERE t.name LIKE '%' || ? || '%'
        GROUP BY t.id
        ORDER BY usage_count DESC
        LIMIT ?
        """,
        (normalized_query, limit),
    ).fetchall()


# ---------------------------------------------------------------------------
# asset_tags helpers
# ---------------------------------------------------------------------------


def add_asset_tag(conn: sqlite3.Connection, asset_id: str, tag_name: str) -> None:
    """Apply *tag_name* (normalized) to *asset_id*, creating the tag if needed."""
    normalized = normalize_tag(tag_name)
    if not normalized:
        return
    tag_id = get_or_create_tag(conn, normalized)
    conn.execute(
        "INSERT OR IGNORE INTO asset_tags (asset_id, tag_id) VALUES (?, ?)",
        (asset_id, tag_id),
    )


def remove_asset_tag(conn: sqlite3.Connection, asset_id: str, tag_id: str) -> None:
    """Remove the association between *asset_id* and the tag with *tag_id* (UUID)."""
    conn.execute(
        "DELETE FROM asset_tags WHERE asset_id = ? AND tag_id = ?",
        (asset_id, tag_id),
    )


def clear_asset_tags(conn: sqlite3.Connection, asset_id: str) -> None:
    """Remove all tag associations for *asset_id* without deleting the tag records."""
    conn.execute("DELETE FROM asset_tags WHERE asset_id = ?", (asset_id,))


def get_asset_tag_names(
    conn: sqlite3.Connection,
    asset_ids: list[str],
) -> dict[str, list[str]]:
    """Return ``{asset_id: [tag_name, ...]}`` (alphabetical) for each asset.

    Returns an empty dict when *asset_ids* is empty.
    """
    if not asset_ids:
        return {}
    placeholders = ",".join("?" * len(asset_ids))
    rows = conn.execute(
        f"SELECT at.asset_id, t.name FROM asset_tags at "  # noqa: S608
        f"JOIN tags t ON t.id = at.tag_id "
        f"WHERE at.asset_id IN ({placeholders}) ORDER BY at.asset_id, t.name",
        asset_ids,
    ).fetchall()
    result: dict[str, list[str]] = {}
    for row in rows:
        result.setdefault(row["asset_id"], []).append(row["name"])
    return result


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
        (normalize_tag(tag_name),),
    ).fetchall()


def list_tags_for_asset_ids(
    conn: sqlite3.Connection,
    asset_ids: list[str],
) -> list[sqlite3.Row]:
    """Return distinct tag rows (id, name) present on any of *asset_ids*, sorted by name.

    Returns an empty list when *asset_ids* is empty.
    """
    if not asset_ids:
        return []
    placeholders = ",".join("?" * len(asset_ids))
    return conn.execute(
        f"""
        SELECT DISTINCT t.id, t.name
        FROM tags t
        JOIN asset_tags at ON at.tag_id = t.id
        WHERE at.asset_id IN ({placeholders})
        ORDER BY t.name
        """,  # noqa: S608
        asset_ids,
    ).fetchall()


def get_asset_tag_memberships(
    conn: sqlite3.Connection,
    asset_ids: list[str],
) -> dict[str, set[str]]:
    """Return ``{asset_id: {tag_id, ...}}`` for each asset in *asset_ids*.

    Assets with no tags are omitted from the result.  Returns an empty dict
    when *asset_ids* is empty.
    """
    if not asset_ids:
        return {}
    placeholders = ",".join("?" * len(asset_ids))
    rows = conn.execute(
        f"SELECT asset_id, tag_id FROM asset_tags WHERE asset_id IN ({placeholders})",  # noqa: S608
        asset_ids,
    ).fetchall()
    result: dict[str, set[str]] = {}
    for row in rows:
        result.setdefault(row["asset_id"], set()).add(row["tag_id"])
    return result

