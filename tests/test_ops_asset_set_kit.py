"""Tests for ops/asset_set_kit.py — MELVIL_OT_asset_set_kit."""

from __future__ import annotations

import sqlite3
from unittest.mock import MagicMock, patch

import pytest

from melvil.db.connection import migrate
from melvil.db import assets as assets_db
from melvil.db import kits as kits_db
from melvil.db.kits import DEFAULT_KIT_ID

_KIT_B_ID = "bbbbbbbb-0000-4000-8000-000000000001"
_ASSET_ID = "aaaaaaaa-0000-4000-8000-000000000001"


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.execute("PRAGMA foreign_keys = ON")
    c.row_factory = sqlite3.Row
    migrate(c)
    kits_db.insert_kit(c, id=_KIT_B_ID, name="Game Project")
    assets_db.insert_asset(c, id=_ASSET_ID, name="Red Metal", type="MATERIAL",
                            blend_path="materials/red_metal.blend", kit_id=DEFAULT_KIT_ID)
    yield c
    c.close()


def _make_op(asset_id="", kit_id=""):
    from melvil.ops.asset_set_kit import MELVIL_OT_asset_set_kit

    op = MELVIL_OT_asset_set_kit()
    op.asset_id = asset_id
    op.kit_id = kit_id
    return op


def _make_ctx():
    return MagicMock()


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


def test_bl_idname():
    from melvil.ops.asset_set_kit import MELVIL_OT_asset_set_kit

    assert MELVIL_OT_asset_set_kit.bl_idname == "melvil.asset_set_kit"


def test_bl_label():
    from melvil.ops.asset_set_kit import MELVIL_OT_asset_set_kit

    assert MELVIL_OT_asset_set_kit.bl_label == "Move to Kit"


# ---------------------------------------------------------------------------
# poll()
# ---------------------------------------------------------------------------


def test_poll_always_true():
    from melvil.ops.asset_set_kit import MELVIL_OT_asset_set_kit

    assert MELVIL_OT_asset_set_kit.poll(MagicMock()) is True


# ---------------------------------------------------------------------------
# execute() — validation
# ---------------------------------------------------------------------------


def test_execute_no_asset_id_returns_cancelled():
    op = _make_op(asset_id="", kit_id=_KIT_B_ID)
    with patch("melvil.ops.asset_set_kit.open_db"), \
         patch("melvil.ops.asset_set_kit.resolve_db_path"):
        result = op.execute(_make_ctx())
    assert result == {"CANCELLED"}


def test_execute_no_kit_id_returns_cancelled():
    op = _make_op(asset_id=_ASSET_ID, kit_id="")
    with patch("melvil.ops.asset_set_kit.open_db"), \
         patch("melvil.ops.asset_set_kit.resolve_db_path"):
        result = op.execute(_make_ctx())
    assert result == {"CANCELLED"}


def test_execute_unknown_asset_returns_cancelled(conn):
    op = _make_op(asset_id="nonexistent-uuid", kit_id=_KIT_B_ID)

    with patch("melvil.ops.asset_set_kit.open_db") as mock_open, \
         patch("melvil.ops.asset_set_kit.resolve_db_path"):
        mock_open.return_value.__enter__ = lambda s: conn
        mock_open.return_value.__exit__ = MagicMock(return_value=False)
        result = op.execute(_make_ctx())

    assert result == {"CANCELLED"}


# ---------------------------------------------------------------------------
# execute() — success
# ---------------------------------------------------------------------------


def test_execute_reassigns_asset_to_kit(conn):
    op = _make_op(asset_id=_ASSET_ID, kit_id=_KIT_B_ID)

    with patch("melvil.ops.asset_set_kit.open_db") as mock_open, \
         patch("melvil.ops.asset_set_kit.resolve_db_path"):
        mock_open.return_value.__enter__ = lambda s: conn
        mock_open.return_value.__exit__ = MagicMock(return_value=False)
        result = op.execute(_make_ctx())

    assert result == {"FINISHED"}
    row = assets_db.get_asset(conn, _ASSET_ID)
    assert row["kit_id"] == _KIT_B_ID


def test_execute_library_not_configured_returns_cancelled():
    from melvil.core.library import LibraryNotConfiguredError

    op = _make_op(asset_id=_ASSET_ID, kit_id=_KIT_B_ID)

    with patch("melvil.ops.asset_set_kit.resolve_db_path",
               side_effect=LibraryNotConfiguredError("not configured")):
        result = op.execute(_make_ctx())

    assert result == {"CANCELLED"}
