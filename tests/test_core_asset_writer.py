"""Tests for core/asset_writer.py."""

from __future__ import annotations

import sqlite3
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from blammo.db.connection import migrate
from blammo.db import assets as assets_db


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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_datablock():
    """A minimal fake datablock with no textures and not already an asset."""
    db = MagicMock()
    db.material_slots = []
    db.asset_data = None  # not yet marked as a Blender asset
    del db.node_tree  # not a material
    return db


def _make_mock_node_group(name="MyGroup", nested=None):
    """
    A minimal fake NodeTree (node group) datablock.

    *nested* is an optional list of (group_node_tree,) that will be added
    as GROUP-type child nodes so _collect_nested_node_groups can find them.
    """
    ng = MagicMock()
    ng.name = name
    ng.asset_data = None  # not yet marked as a Blender asset
    nodes = []
    for child_tree in (nested or []):
        group_node = MagicMock()
        group_node.type = "GROUP"
        group_node.node_tree = child_tree
        nodes.append(group_node)
    ng.nodes = nodes
    # NodeTrees don't have node_tree or material_slots attributes.
    del ng.node_tree
    del ng.material_slots
    return ng


# ---------------------------------------------------------------------------
# _slugify
# ---------------------------------------------------------------------------


class TestSlugify:
    def test_lowercase(self):
        from blammo.core.asset_writer import _slugify
        assert _slugify("Red Metal") == "red_metal"

    def test_special_chars_become_underscore(self):
        from blammo.core.asset_writer import _slugify
        assert _slugify("Hello, World!") == "hello_world"

    def test_leading_trailing_underscores_stripped(self):
        from blammo.core.asset_writer import _slugify
        assert _slugify("___foo___") == "foo"

    def test_empty_fallback(self):
        from blammo.core.asset_writer import _slugify
        assert _slugify("!!!") == "asset"

    def test_numbers_preserved(self):
        from blammo.core.asset_writer import _slugify
        assert _slugify("Tile v2") == "tile_v2"


# ---------------------------------------------------------------------------
# AssetWriter._build_filename
# ---------------------------------------------------------------------------


class TestBuildFilename:
    def test_format(self):
        from blammo.core.asset_writer import AssetWriter
        asset_id = "12345678-abcd-ef01-2345-678901234567"
        name = "Rusty Iron"
        filename = AssetWriter._build_filename(name, asset_id)
        assert filename == "rusty_iron_12345678.blend"

    def test_hyphens_removed_from_id(self):
        from blammo.core.asset_writer import AssetWriter
        asset_id = "abcd1234-5678-0000-0000-000000000000"
        filename = AssetWriter._build_filename("Foo", asset_id)
        assert "-" not in filename


# ---------------------------------------------------------------------------
# AssetWriter.write
# ---------------------------------------------------------------------------


class TestAssetWriterWrite:
    def test_write_inserts_db_record(self, library_root, conn):
        from blammo.core.asset_writer import AssetWriter

        writer = AssetWriter(library_root, conn)
        datablock = _make_mock_datablock()

        with patch("blammo.core.asset_writer._write_blend_file") as mock_write, \
             patch("blammo.core.textures.collect_external_images", return_value=[]):
            asset_id = writer.write(datablock, "Red Metal", "MATERIAL")

        row = assets_db.get_asset(conn, asset_id)
        assert row is not None
        assert row["name"] == "Red Metal"
        assert row["type"] == "MATERIAL"

    def test_write_returns_valid_uuid(self, library_root, conn):
        from blammo.core.asset_writer import AssetWriter

        writer = AssetWriter(library_root, conn)
        datablock = _make_mock_datablock()

        with patch("blammo.core.asset_writer._write_blend_file"), \
             patch("blammo.core.textures.collect_external_images", return_value=[]):
            asset_id = writer.write(datablock, "Mesh Cube", "MESH")

        # Should be a valid UUID
        parsed = uuid.UUID(asset_id)
        assert str(parsed) == asset_id

    def test_blend_path_is_relative(self, library_root, conn):
        from blammo.core.asset_writer import AssetWriter

        writer = AssetWriter(library_root, conn)
        datablock = _make_mock_datablock()

        with patch("blammo.core.asset_writer._write_blend_file"), \
             patch("blammo.core.textures.collect_external_images", return_value=[]):
            asset_id = writer.write(datablock, "Stone Wall", "MATERIAL")

        row = assets_db.get_asset(conn, asset_id)
        blend_path = row["blend_path"]

        # Must be a bare filename, not an absolute path
        assert not Path(blend_path).is_absolute()
        assert blend_path.endswith(".blend")

    def test_write_calls_write_blend_file(self, library_root, conn):
        from blammo.core.asset_writer import AssetWriter

        writer = AssetWriter(library_root, conn)
        datablock = _make_mock_datablock()

        with patch("blammo.core.asset_writer._write_blend_file") as mock_write, \
             patch("blammo.core.textures.collect_external_images", return_value=[]):
            writer.write(datablock, "Marble", "MATERIAL")

        mock_write.assert_called_once()
        filepath_arg, datablocks_arg = mock_write.call_args[0]
        assert filepath_arg.endswith(".blend")
        assert datablock in datablocks_arg

    def test_texture_paths_restored_after_write(self, library_root, conn):
        """Image filepaths must be restored to originals even when write succeeds."""
        from blammo.core.asset_writer import AssetWriter

        img = MagicMock()
        img.filepath = "/original/path/rock.png"

        writer = AssetWriter(library_root, conn)
        datablock = _make_mock_datablock()

        with patch("blammo.core.asset_writer._write_blend_file"), \
             patch("blammo.core.textures.collect_external_images", return_value=[img]), \
             patch("blammo.core.textures.copy_textures", return_value={"/original/path/rock.png": "//textures/rock.png"}):
            writer.write(datablock, "Rock", "MATERIAL")

        assert img.filepath == "/original/path/rock.png"

    def test_texture_paths_restored_on_write_error(self, library_root, conn):
        """Image filepaths must be restored even when _write_blend_file raises."""
        from blammo.core.asset_writer import AssetWriter

        img = MagicMock()
        img.filepath = "/original/path/rock.png"

        writer = AssetWriter(library_root, conn)
        datablock = _make_mock_datablock()

        with pytest.raises(RuntimeError), \
             patch("blammo.core.asset_writer._write_blend_file", side_effect=RuntimeError("disk full")), \
             patch("blammo.core.textures.collect_external_images", return_value=[img]), \
             patch("blammo.core.textures.copy_textures", return_value={"/original/path/rock.png": "//textures/rock.png"}):
            writer.write(datablock, "Rock", "MATERIAL")

        assert img.filepath == "/original/path/rock.png"

    def test_creates_library_root_if_missing(self, tmp_path, conn):
        from blammo.core.asset_writer import AssetWriter

        library_root = tmp_path / "new_library"
        assert not library_root.exists()

        writer = AssetWriter(library_root, conn)
        datablock = _make_mock_datablock()

        with patch("blammo.core.asset_writer._write_blend_file"), \
             patch("blammo.core.textures.collect_external_images", return_value=[]):
            writer.write(datablock, "Test", "MATERIAL")

        assert library_root.exists()

    def test_write_with_explicit_kit_id_stores_kit(self, library_root, conn):
        """kit_id passed to write() should be stored in the DB record."""
        from blammo.core.asset_writer import AssetWriter
        from blammo.db.assets import get_asset

        kit_id = "00000000-0000-4000-8000-000000000001"  # General kit (seeded by migration)
        writer = AssetWriter(library_root, conn)
        datablock = _make_mock_datablock()

        with patch("blammo.core.asset_writer._write_blend_file"), \
             patch("blammo.core.textures.collect_external_images", return_value=[]):
            asset_id = writer.write(datablock, "Brick Wall", "MATERIAL", kit_id=kit_id)

        row = get_asset(conn, asset_id)
        assert row["kit_id"] == kit_id


# ---------------------------------------------------------------------------
# _collect_nested_node_groups
# ---------------------------------------------------------------------------


class TestCollectNestedNodeGroups:
    def test_root_only_returned_when_no_children(self):
        from blammo.core.asset_writer import _collect_nested_node_groups

        root = _make_mock_node_group("Root")
        result = _collect_nested_node_groups(root)
        assert result == {root}

    def test_single_nested_group_included(self):
        from blammo.core.asset_writer import _collect_nested_node_groups

        child = _make_mock_node_group("Child")
        root = _make_mock_node_group("Root", nested=[child])
        result = _collect_nested_node_groups(root)
        assert root in result
        assert child in result

    def test_deeply_nested_groups_all_included(self):
        from blammo.core.asset_writer import _collect_nested_node_groups

        grandchild = _make_mock_node_group("Grandchild")
        child = _make_mock_node_group("Child", nested=[grandchild])
        root = _make_mock_node_group("Root", nested=[child])
        result = _collect_nested_node_groups(root)
        assert {root, child, grandchild} == result

    def test_diamond_dependency_not_duplicated(self):
        """A shared sub-group referenced by two parents appears once."""
        from blammo.core.asset_writer import _collect_nested_node_groups

        shared = _make_mock_node_group("Shared")
        left = _make_mock_node_group("Left", nested=[shared])
        right = _make_mock_node_group("Right", nested=[shared])
        root = _make_mock_node_group("Root", nested=[left, right])
        result = _collect_nested_node_groups(root)
        assert result == {root, left, right, shared}

    def test_cycle_does_not_recurse_infinitely(self):
        """A cyclic reference must not cause infinite recursion."""
        from blammo.core.asset_writer import _collect_nested_node_groups

        root = _make_mock_node_group("Root")
        # Manually wire a self-referential cycle
        group_node = MagicMock()
        group_node.type = "GROUP"
        group_node.node_tree = root
        root.nodes = [group_node]

        result = _collect_nested_node_groups(root)
        assert result == {root}


# ---------------------------------------------------------------------------
# AssetWriter.write — NODE_GROUP
# ---------------------------------------------------------------------------


class TestAssetWriterWriteNodeGroup:
    def test_write_node_group_inserts_db_record(self, library_root, conn):
        from blammo.core.asset_writer import AssetWriter

        ng = _make_mock_node_group("Noise FX")
        writer = AssetWriter(library_root, conn)

        with patch("blammo.core.asset_writer._write_blend_file"), \
             patch("blammo.core.textures.collect_external_images", return_value=[]):
            asset_id = writer.write(ng, "Noise FX", "NODE_GROUP")

        row = assets_db.get_asset(conn, asset_id)
        assert row is not None
        assert row["name"] == "Noise FX"
        assert row["type"] == "NODE_GROUP"

    def test_write_node_group_includes_nested_in_datablocks(self, library_root, conn):
        """_write_blend_file must receive the root and all nested node groups."""
        from blammo.core.asset_writer import AssetWriter

        child = _make_mock_node_group("Child")
        root = _make_mock_node_group("Root", nested=[child])
        writer = AssetWriter(library_root, conn)

        with patch("blammo.core.asset_writer._write_blend_file") as mock_write, \
             patch("blammo.core.textures.collect_external_images", return_value=[]):
            writer.write(root, "Root", "NODE_GROUP")

        _, datablocks_arg = mock_write.call_args[0]
        assert root in datablocks_arg
        assert child in datablocks_arg

    def test_write_node_group_texture_paths_restored(self, library_root, conn):
        """Image filepaths must be restored after writing a node group."""
        from blammo.core.asset_writer import AssetWriter

        img = MagicMock()
        img.filepath = "/original/noise.png"
        ng = _make_mock_node_group("Noise FX")
        writer = AssetWriter(library_root, conn)

        with patch("blammo.core.asset_writer._write_blend_file"), \
             patch("blammo.core.textures.collect_external_images", return_value=[img]), \
             patch("blammo.core.textures.copy_textures", return_value={"/original/noise.png": "//textures/noise.png"}):
            writer.write(ng, "Noise FX", "NODE_GROUP")

        assert img.filepath == "/original/noise.png"

    def test_write_node_group_texture_paths_restored_on_error(self, library_root, conn):
        """Image filepaths must be restored even when write raises."""
        from blammo.core.asset_writer import AssetWriter

        img = MagicMock()
        img.filepath = "/original/noise.png"
        ng = _make_mock_node_group("Noise FX")
        writer = AssetWriter(library_root, conn)

        with pytest.raises(RuntimeError), \
             patch("blammo.core.asset_writer._write_blend_file", side_effect=RuntimeError("boom")), \
             patch("blammo.core.textures.collect_external_images", return_value=[img]), \
             patch("blammo.core.textures.copy_textures", return_value={"/original/noise.png": "//textures/noise.png"}):
            writer.write(ng, "Noise FX", "NODE_GROUP")

        assert img.filepath == "/original/noise.png"


# ---------------------------------------------------------------------------
# Asset marking lifecycle
# ---------------------------------------------------------------------------


class TestAssetMarkingLifecycle:
    """Ensure datablocks are temporarily marked as Blender assets during write."""

    def test_datablock_marked_before_write(self, library_root, conn):
        """asset_mark() must be called before _write_blend_file."""
        from blammo.core.asset_writer import AssetWriter

        call_order = []
        datablock = _make_mock_datablock()
        datablock.asset_mark.side_effect = lambda: call_order.append("mark")
        writer = AssetWriter(library_root, conn)

        def _record_write(filepath, datablocks, **kwargs):
            call_order.append("write")

        with patch("blammo.core.asset_writer._write_blend_file", side_effect=_record_write), \
             patch("blammo.core.textures.collect_external_images", return_value=[]):
            writer.write(datablock, "Test", "MATERIAL")

        assert call_order.index("mark") < call_order.index("write")

    def test_datablock_cleared_after_successful_write(self, library_root, conn):
        """asset_clear() must be called after a successful write."""
        from blammo.core.asset_writer import AssetWriter

        datablock = _make_mock_datablock()
        writer = AssetWriter(library_root, conn)

        with patch("blammo.core.asset_writer._write_blend_file"), \
             patch("blammo.core.textures.collect_external_images", return_value=[]):
            writer.write(datablock, "Test", "MATERIAL")

        datablock.asset_clear.assert_called_once()

    def test_datablock_cleared_after_write_error(self, library_root, conn):
        """asset_clear() must be called even when _write_blend_file raises."""
        from blammo.core.asset_writer import AssetWriter

        datablock = _make_mock_datablock()
        writer = AssetWriter(library_root, conn)

        with pytest.raises(RuntimeError), \
             patch("blammo.core.asset_writer._write_blend_file", side_effect=RuntimeError("disk full")), \
             patch("blammo.core.textures.collect_external_images", return_value=[]):
            writer.write(datablock, "Test", "MATERIAL")

        datablock.asset_clear.assert_called_once()

    def test_already_asset_not_marked_or_cleared(self, library_root, conn):
        """If datablock is already an asset, asset_mark/clear must not be called."""
        from blammo.core.asset_writer import AssetWriter

        datablock = _make_mock_datablock()
        datablock.asset_data = MagicMock()  # already an asset
        writer = AssetWriter(library_root, conn)

        with patch("blammo.core.asset_writer._write_blend_file"), \
             patch("blammo.core.textures.collect_external_images", return_value=[]):
            writer.write(datablock, "Test", "MATERIAL")

        datablock.asset_mark.assert_not_called()
        datablock.asset_clear.assert_not_called()

    def test_node_group_root_marked_and_cleared(self, library_root, conn):
        """The root node tree must be marked then cleared; nested groups must not be."""
        from blammo.core.asset_writer import AssetWriter

        child = _make_mock_node_group("Child")
        root = _make_mock_node_group("Root", nested=[child])
        writer = AssetWriter(library_root, conn)

        with patch("blammo.core.asset_writer._write_blend_file"), \
             patch("blammo.core.textures.collect_external_images", return_value=[]):
            writer.write(root, "Root", "NODE_GROUP")

        root.asset_mark.assert_called_once()
        root.asset_clear.assert_called_once()
        child.asset_mark.assert_not_called()
        child.asset_clear.assert_not_called()

    def test_write_node_group_root_name_restored(self, library_root, conn):
        """The root node group's name must be restored after writing."""
        from blammo.core.asset_writer import AssetWriter

        ng = _make_mock_node_group("Original Name")
        writer = AssetWriter(library_root, conn)

        with patch("blammo.core.asset_writer._write_blend_file"), \
             patch("blammo.core.textures.collect_external_images", return_value=[]):
            writer.write(ng, "New Name", "NODE_GROUP")

        assert ng.name == "Original Name"

