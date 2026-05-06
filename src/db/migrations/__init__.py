"""
Migration discovery for the Blammo SQLite database.

Migration files live alongside this package in db/migrations/ and follow the
naming convention:

    NNNN_short_description.py   e.g. 0001_initial_setup.py

Each file must expose a single function:

    def upgrade(conn: sqlite3.Connection) -> None: ...

Migrations are discovered at import time, sorted by their numeric prefix, and
exposed as MIGRATIONS (list of callables) and LATEST_VERSION (int).

To add a new migration:
  1. Create the next numbered file in this directory.
  2. Implement upgrade(conn).
  That's it — no registration needed.

Never edit an existing migration file.
"""

from __future__ import annotations

import importlib
import re
import sqlite3
from pathlib import Path
from typing import Callable

Migration = Callable[[sqlite3.Connection], None]

_MIGRATION_RE = re.compile(r"^(\d+)_[a-zA-Z0-9_]+\.py$")


def _discover() -> list[Migration]:
    migrations_dir = Path(__file__).parent
    entries: list[tuple[int, str]] = []

    for path in migrations_dir.iterdir():
        m = _MIGRATION_RE.match(path.name)
        if m:
            entries.append((int(m.group(1)), path.stem))

    entries.sort(key=lambda e: e[0])

    result: list[Migration] = []
    for number, stem in entries:
        module = importlib.import_module(f".{stem}", package=__name__)
        result.append(module.upgrade)
    return result


MIGRATIONS: list[Migration] = _discover()
LATEST_VERSION: int = len(MIGRATIONS)
