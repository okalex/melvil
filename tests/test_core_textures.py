"""Tests for core/textures.py — texture discovery and copying utilities."""

from __future__ import annotations

import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest


# ---------------------------------------------------------------------------
# Helpers to build fake bpy image / datablock objects
# ---------------------------------------------------------------------------


def _make_image(filepath: str = "/abs/textures/grid.png", packed: bool = False, source: str = "FILE") -> MagicMock:
    img = MagicMock()
    img.filepath = filepath
    img.filepath_from_user = MagicMock(return_value=filepath)
    img.packed_file = MagicMock() if packed else None
    img.source = source
    img.id_data = img  # makes identity comparison work in seen-set
    return img


def _make_tex_image_node(image=None) -> MagicMock:
    node = MagicMock()
    node.type = "TEX_IMAGE"
    node.image = image
    return node


def _make_material(images: list | None = None) -> MagicMock:
    mat = MagicMock()
    nodes = []
    for img in (images or []):
        nodes.append(_make_tex_image_node(img))
    mat.node_tree.nodes = nodes
    return mat


def _make_object(materials: list | None = None) -> MagicMock:
    obj = MagicMock()
    slots = []
    for mat in (materials or []):
        slot = MagicMock()
        slot.material = mat
        slots.append(slot)
    obj.material_slots = slots
    del obj.node_tree  # objects don't have node_tree
    return obj


# ---------------------------------------------------------------------------
# collect_external_images
# ---------------------------------------------------------------------------


class TestCollectExternalImages:
    def test_material_with_tex_image_node(self):
        from melvil.core.textures import collect_external_images

        img = _make_image("/src/grid.png")
        mat = _make_material([img])

        result = collect_external_images(mat)
        assert img in result

    def test_packed_image_excluded(self):
        from melvil.core.textures import collect_external_images

        img = _make_image("/src/grid.png", packed=True)
        mat = _make_material([img])

        result = collect_external_images(mat)
        assert result == []

    def test_non_file_source_excluded(self):
        from melvil.core.textures import collect_external_images

        img = _make_image("/src/grid.png", source="GENERATED")
        mat = _make_material([img])

        result = collect_external_images(mat)
        assert result == []

    def test_object_recurses_into_material_slots(self):
        from melvil.core.textures import collect_external_images

        img = _make_image("/src/rust.png")
        mat = _make_material([img])
        obj = _make_object([mat])

        result = collect_external_images(obj)
        assert img in result

    def test_deduplicates_same_image_in_multiple_materials(self):
        from melvil.core.textures import collect_external_images

        img = _make_image("/src/shared.png")
        mat1 = _make_material([img])
        mat2 = _make_material([img])
        obj = _make_object([mat1, mat2])

        result = collect_external_images(obj)
        assert result.count(img) == 1

    def test_empty_node_tree_returns_empty(self):
        from melvil.core.textures import collect_external_images

        mat = MagicMock()
        mat.node_tree = None

        result = collect_external_images(mat)
        assert result == []

    def test_node_without_image_skipped(self):
        from melvil.core.textures import collect_external_images

        node = _make_tex_image_node(image=None)
        mat = MagicMock()
        mat.node_tree.nodes = [node]

        result = collect_external_images(mat)
        assert result == []

    def test_node_group_datablock_returns_tex_image(self):
        """A NodeTree datablock (node group) with a TEX_IMAGE node is collected."""
        from melvil.core.textures import collect_external_images

        img = _make_image("/src/noise.png")
        node = _make_tex_image_node(img)
        node_group = MagicMock()
        node_group.nodes = [node]
        # NodeTrees don't have node_tree or material_slots
        del node_group.node_tree
        del node_group.material_slots

        result = collect_external_images(node_group)
        assert img in result

    def test_node_group_nested_images_collected(self):
        """Images inside nested GROUP nodes are collected recursively."""
        from melvil.core.textures import collect_external_images

        img_inner = _make_image("/src/inner.png")
        inner_node = _make_tex_image_node(img_inner)

        nested_tree = MagicMock()
        nested_tree.nodes = [inner_node]

        group_node = MagicMock()
        group_node.type = "GROUP"
        group_node.node_tree = nested_tree

        root_tree = MagicMock()
        root_tree.nodes = [group_node]
        del root_tree.node_tree
        del root_tree.material_slots

        result = collect_external_images(root_tree)
        assert img_inner in result

    def test_node_group_nested_deduplication(self):
        """The same image referenced in multiple nested groups is returned once."""
        from melvil.core.textures import collect_external_images

        img = _make_image("/src/shared.png")
        node_a = _make_tex_image_node(img)
        node_b = _make_tex_image_node(img)

        nested_tree = MagicMock()
        nested_tree.nodes = [node_b]

        group_node = MagicMock()
        group_node.type = "GROUP"
        group_node.node_tree = nested_tree

        root_tree = MagicMock()
        root_tree.nodes = [node_a, group_node]
        del root_tree.node_tree
        del root_tree.material_slots

        result = collect_external_images(root_tree)
        assert result.count(img) == 1

    def test_node_group_cycle_does_not_recurse_infinitely(self):
        """A self-referencing node tree must not cause infinite recursion."""
        from melvil.core.textures import collect_external_images

        root_tree = MagicMock()
        group_node = MagicMock()
        group_node.type = "GROUP"
        group_node.node_tree = root_tree  # cycle: root → root
        root_tree.nodes = [group_node]
        del root_tree.node_tree
        del root_tree.material_slots

        # Should complete without hitting Python's recursion limit.
        result = collect_external_images(root_tree)
        assert result == []

    def test_material_group_node_images_collected(self):
        """Images inside GROUP nodes within a material's node tree are collected."""
        from melvil.core.textures import collect_external_images

        img = _make_image("/src/detail.png")
        inner_node = _make_tex_image_node(img)

        nested_tree = MagicMock()
        nested_tree.nodes = [inner_node]

        group_node = MagicMock()
        group_node.type = "GROUP"
        group_node.node_tree = nested_tree

        mat = MagicMock()
        mat.node_tree.nodes = [group_node]

        result = collect_external_images(mat)
        assert img in result


# ---------------------------------------------------------------------------
# copy_textures
# ---------------------------------------------------------------------------


class TestCopyTextures:
    def test_copies_image_to_textures_dir(self, tmp_path):
        from melvil.core.textures import copy_textures

        # Create a fake source file so shutil.copy2 has something to copy
        src_file = tmp_path / "source" / "rock.png"
        src_file.parent.mkdir()
        src_file.write_bytes(b"\x89PNG")

        img = _make_image(filepath=str(src_file))
        img.filepath_from_user = MagicMock(return_value=str(src_file))

        textures_dir = tmp_path / "library" / "textures"
        result = copy_textures([img], textures_dir)

        assert (textures_dir / "rock.png").exists()
        assert result[str(src_file)] == "//textures/rock.png"

    def test_returns_empty_for_no_images(self, tmp_path):
        from melvil.core.textures import copy_textures

        result = copy_textures([], tmp_path / "textures")
        assert result == {}

    def test_does_not_overwrite_existing_file(self, tmp_path):
        from melvil.core.textures import copy_textures

        src_file = tmp_path / "src" / "tile.png"
        src_file.parent.mkdir()
        src_file.write_bytes(b"SRC")

        textures_dir = tmp_path / "lib" / "textures"
        textures_dir.mkdir(parents=True)
        existing = textures_dir / "tile.png"
        existing.write_bytes(b"EXISTING")

        img = _make_image(filepath=str(src_file))
        img.filepath_from_user = MagicMock(return_value=str(src_file))

        copy_textures([img], textures_dir)

        assert existing.read_bytes() == b"EXISTING"

    def test_skips_missing_source_file(self, tmp_path):
        from melvil.core.textures import copy_textures

        img = _make_image(filepath="/nonexistent/missing.png")
        img.filepath_from_user = MagicMock(return_value="/nonexistent/missing.png")

        textures_dir = tmp_path / "textures"
        result = copy_textures([img], textures_dir)

        assert result == {}

    def test_collision_gets_counter_suffix(self, tmp_path):
        from melvil.core.textures import copy_textures

        # Two different source files with the same filename
        src1 = tmp_path / "a" / "tile.png"
        src2 = tmp_path / "b" / "tile.png"
        src1.parent.mkdir(); src1.write_bytes(b"A")
        src2.parent.mkdir(); src2.write_bytes(b"B")

        img1 = _make_image(filepath=str(src1))
        img1.filepath_from_user = MagicMock(return_value=str(src1))
        img2 = _make_image(filepath=str(src2))
        img2.id_data = img2  # different identity
        img2.filepath_from_user = MagicMock(return_value=str(src2))

        textures_dir = tmp_path / "lib" / "textures"
        result = copy_textures([img1, img2], textures_dir)

        assert (textures_dir / "tile.png").exists()
        assert (textures_dir / "tile_2.png").exists()
        assert result[str(src1)] == "//textures/tile.png"
        assert result[str(src2)] == "//textures/tile_2.png"
