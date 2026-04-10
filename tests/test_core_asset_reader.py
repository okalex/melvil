"""Tests for core/asset_reader.py."""

from __future__ import annotations

import sqlite3
from pathlib import Path
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


@pytest.fixture
def library_root(tmp_path) -> Path:
    root = tmp_path / "library"
    root.mkdir()
    return root


SAMPLE_MATERIAL = dict(
    id="aaaaaaaa-0000-4000-8000-000000000001",
    name="Red Metal",
    type="MATERIAL",
    blend_path="red_metal_aaaaaaaa.blend",
)

SAMPLE_MESH = dict(
    id="bbbbbbbb-0000-4000-8000-000000000002",
    name="Stone Wall",
    type="MESH",
    blend_path="stone_wall_bbbbbbbb.blend",
)


# ---------------------------------------------------------------------------
# AssetReader.read
# ---------------------------------------------------------------------------


class TestAssetReaderRead:
    def test_raises_for_unknown_asset(self, library_root, conn):
        from melvil.core.asset_reader import AssetReader, AssetNotFoundError

        reader = AssetReader(library_root, conn)
        with pytest.raises(AssetNotFoundError):
            reader.read("does-not-exist")

    def test_loads_material_from_correct_path(self, library_root, conn):
        from melvil.core.asset_reader import AssetReader

        assets_db.insert_asset(conn, **SAMPLE_MATERIAL)
        mock_material = MagicMock()

        with patch("melvil.core.asset_reader._load_datablock", return_value=mock_material) as mock_load:
            reader = AssetReader(library_root, conn)
            result = reader.read(SAMPLE_MATERIAL["id"])

        expected_path = str(library_root / SAMPLE_MATERIAL["blend_path"])
        mock_load.assert_called_once_with(expected_path, "Red Metal", "materials")
        assert result is mock_material

    def test_loads_mesh_with_objects_collection(self, library_root, conn):
        from melvil.core.asset_reader import AssetReader

        assets_db.insert_asset(conn, **SAMPLE_MESH)
        mock_obj = MagicMock()

        with patch("melvil.core.asset_reader._load_datablock", return_value=mock_obj) as mock_load:
            reader = AssetReader(library_root, conn)
            result = reader.read(SAMPLE_MESH["id"])

        _, _, collection_arg = mock_load.call_args[0]
        assert collection_arg == "objects"
        assert result is mock_obj

    def test_raises_for_unsupported_type(self, library_root, conn):
        from melvil.core.asset_reader import AssetReader

        assets_db.insert_asset(
            conn,
            id="cccccccc-0000-4000-8000-000000000003",
            name="Sound FX",
            type="SOUND",
            blend_path="sound.blend",
        )

        reader = AssetReader(library_root, conn)
        with pytest.raises(ValueError, match="SOUND"):
            reader.read("cccccccc-0000-4000-8000-000000000003")

    def test_blend_path_resolved_relative_to_library_root(self, library_root, conn):
        from melvil.core.asset_reader import AssetReader

        assets_db.insert_asset(conn, **SAMPLE_MATERIAL)

        captured = {}

        def fake_load(filepath, name, collection):
            captured["filepath"] = filepath
            return MagicMock()

        with patch("melvil.core.asset_reader._load_datablock", side_effect=fake_load):
            reader = AssetReader(library_root, conn)
            reader.read(SAMPLE_MATERIAL["id"])

        assert captured["filepath"] == str(library_root / SAMPLE_MATERIAL["blend_path"])


# ---------------------------------------------------------------------------
# AssetNotFoundError
# ---------------------------------------------------------------------------


class TestAssetNotFoundError:
    def test_is_exception_subclass(self):
        from melvil.core.asset_reader import AssetNotFoundError
        assert issubclass(AssetNotFoundError, Exception)

    def test_message_contains_id(self, library_root, conn):
        from melvil.core.asset_reader import AssetReader, AssetNotFoundError

        reader = AssetReader(library_root, conn)
        with pytest.raises(AssetNotFoundError, match="missing-id"):
            reader.read("missing-id")
