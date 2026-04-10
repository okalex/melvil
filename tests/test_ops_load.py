"""Tests for ops/load.py — MELVIL_OT_load_asset."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest

from melvil.db.connection import migrate
from melvil.db import assets as assets_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.execute("PRAGMA foreign_keys = ON")
    c.row_factory = sqlite3.Row
    migrate(c)
    yield c
    c.close()


def _mock_open_db(conn):
    @contextmanager
    def _cm(_path):
        yield conn
    return _cm


SAMPLE_MATERIAL = dict(
    id="aaaaaaaa-0000-4000-8000-000000000001",
    name="Red Metal",
    type="MATERIAL",
    blend_path="red_metal_aaaaaaaa.blend",
)

SAMPLE_MESH = dict(
    id="bbbbbbbb-0000-4000-8000-000000000002",
    name="Suzanne",
    type="MESH",
    blend_path="suzanne_bbbbbbbb.blend",
)


def _make_op(asset_id=""):
    from melvil.ops.load import MELVIL_OT_load_asset

    op = MELVIL_OT_load_asset()
    op.asset_id = asset_id
    return op


def _make_context(mode="OBJECT"):
    ctx = MagicMock()
    ctx.mode = mode
    ctx.scene = MagicMock()
    return ctx


# ---------------------------------------------------------------------------
# poll()
# ---------------------------------------------------------------------------


class TestPoll:
    def test_returns_true_when_scene_exists(self):
        from melvil.ops.load import MELVIL_OT_load_asset

        ctx = _make_context()
        assert MELVIL_OT_load_asset.poll(ctx) is True

    def test_returns_false_when_no_scene(self):
        from melvil.ops.load import MELVIL_OT_load_asset

        ctx = MagicMock()
        ctx.scene = None
        assert MELVIL_OT_load_asset.poll(ctx) is False


# ---------------------------------------------------------------------------
# execute()
# ---------------------------------------------------------------------------


class TestExecute:
    def test_no_asset_id_returns_cancelled(self):
        op = _make_op(asset_id="")
        ctx = _make_context()

        with patch("melvil.ops.load.resolve_library_root", return_value="/lib"):
            result = op.execute(ctx)

        assert result == {"CANCELLED"}

    def test_library_not_configured_returns_cancelled(self):
        from melvil.core.library import LibraryNotConfiguredError

        op = _make_op(asset_id="aaaaaaaa-0000-4000-8000-000000000001")
        ctx = _make_context()

        with patch("melvil.ops.load.resolve_library_root", side_effect=LibraryNotConfiguredError("not set")):
            result = op.execute(ctx)

        assert result == {"CANCELLED"}

    def test_asset_not_found_returns_cancelled(self, conn):
        from melvil.core.asset_reader import AssetNotFoundError

        op = _make_op(asset_id="does-not-exist")
        ctx = _make_context()

        with patch("melvil.ops.load.resolve_library_root", return_value="/lib"), \
             patch("melvil.ops.load.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ops.load.open_db", _mock_open_db(conn)), \
             patch("melvil.ops.load.AssetReader") as MockReader:
            MockReader.return_value.read.side_effect = AssetNotFoundError("not found")
            result = op.execute(ctx)

        assert result == {"CANCELLED"}

    def test_load_material_returns_finished(self, conn):
        assets_db.insert_asset(conn, **SAMPLE_MATERIAL)
        mock_material = MagicMock(spec=[])  # no users_collection → treated as material
        mock_material.name = "Red Metal"

        op = _make_op(asset_id=SAMPLE_MATERIAL["id"])
        ctx = _make_context()

        with patch("melvil.ops.load.resolve_library_root", return_value="/lib"), \
             patch("melvil.ops.load.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ops.load.open_db", _mock_open_db(conn)), \
             patch("melvil.ops.load.AssetReader") as MockReader:
            MockReader.return_value.read.return_value = mock_material
            result = op.execute(ctx)

        assert result == {"FINISHED"}

    def test_load_mesh_links_to_collection(self, conn):
        assets_db.insert_asset(conn, **SAMPLE_MESH)
        mock_obj = MagicMock()
        mock_obj.name = "Suzanne"
        mock_obj.users_collection = []  # attribute present → it's an Object

        op = _make_op(asset_id=SAMPLE_MESH["id"])
        ctx = _make_context()

        with patch("melvil.ops.load.resolve_library_root", return_value="/lib"), \
             patch("melvil.ops.load.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ops.load.open_db", _mock_open_db(conn)), \
             patch("melvil.ops.load.AssetReader") as MockReader, \
             patch("melvil.ops.load.bpy") as mock_bpy:
            MockReader.return_value.read.return_value = mock_obj
            result = op.execute(ctx)

        ctx.collection.objects.link.assert_called_once_with(mock_obj)
        assert result == {"FINISHED"}

    def test_load_mesh_places_at_cursor(self, conn):
        assets_db.insert_asset(conn, **SAMPLE_MESH)
        mock_obj = MagicMock()
        mock_obj.name = "Suzanne"
        mock_obj.users_collection = []

        cursor_loc = MagicMock()
        op = _make_op(asset_id=SAMPLE_MESH["id"])
        ctx = _make_context()
        ctx.scene.cursor.location = cursor_loc

        with patch("melvil.ops.load.resolve_library_root", return_value="/lib"), \
             patch("melvil.ops.load.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ops.load.open_db", _mock_open_db(conn)), \
             patch("melvil.ops.load.AssetReader") as MockReader, \
             patch("melvil.ops.load.bpy"):
            MockReader.return_value.read.return_value = mock_obj
            op.execute(ctx)

        assert mock_obj.location == cursor_loc

    def test_none_datablock_returns_cancelled(self, conn):
        op = _make_op(asset_id="aaaaaaaa-0000-4000-8000-000000000001")
        ctx = _make_context()

        with patch("melvil.ops.load.resolve_library_root", return_value="/lib"), \
             patch("melvil.ops.load.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ops.load.open_db", _mock_open_db(conn)), \
             patch("melvil.ops.load.AssetReader") as MockReader:
            MockReader.return_value.read.return_value = None
            result = op.execute(ctx)

        assert result == {"CANCELLED"}

    def test_whitespace_asset_id_returns_cancelled(self):
        op = _make_op(asset_id="   ")
        ctx = _make_context()

        with patch("melvil.ops.load.resolve_library_root", return_value="/lib"):
            result = op.execute(ctx)

        assert result == {"CANCELLED"}
