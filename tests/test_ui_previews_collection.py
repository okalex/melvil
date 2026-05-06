"""
Tests for src/ui/previews_collection.py
"""

import sys
from unittest.mock import MagicMock, patch, call
import pytest


@pytest.fixture(autouse=True)
def reset_collection():
    """Ensure _collection is reset to None before and after each test."""
    import blammo.ui.previews_collection as pc

    pc._collection = None
    yield
    pc._collection = None


# ---------------------------------------------------------------------------
# register()
# ---------------------------------------------------------------------------


def test_register_creates_collection():
    import blammo.ui.previews_collection as pc

    mock_col = MagicMock()
    mock_bpy = MagicMock()
    mock_bpy.utils.previews.new.return_value = mock_col

    with patch.dict(sys.modules, {"bpy": mock_bpy}):
        pc.register()

    mock_bpy.utils.previews.new.assert_called_once_with()
    assert pc._collection is mock_col


def test_register_replaces_existing_collection():
    """Calling register() again overwrites the previous collection reference."""
    import blammo.ui.previews_collection as pc

    first_col = MagicMock()
    second_col = MagicMock()
    mock_bpy = MagicMock()
    mock_bpy.utils.previews.new.side_effect = [first_col, second_col]

    with patch.dict(sys.modules, {"bpy": mock_bpy}):
        pc.register()
        pc.register()

    assert pc._collection is second_col


# ---------------------------------------------------------------------------
# unregister()
# ---------------------------------------------------------------------------


def test_unregister_removes_collection():
    import blammo.ui.previews_collection as pc

    mock_col = MagicMock()
    pc._collection = mock_col
    mock_bpy = MagicMock()

    with patch.dict(sys.modules, {"bpy": mock_bpy}):
        pc.unregister()

    mock_bpy.utils.previews.remove.assert_called_once_with(mock_col)
    assert pc._collection is None


def test_unregister_when_collection_is_none():
    """unregister() should be a no-op when _collection is already None."""
    import blammo.ui.previews_collection as pc

    mock_bpy = MagicMock()

    with patch.dict(sys.modules, {"bpy": mock_bpy}):
        pc.unregister()  # should not raise

    mock_bpy.utils.previews.remove.assert_not_called()


# ---------------------------------------------------------------------------
# get_icon_id()
# ---------------------------------------------------------------------------


def test_get_icon_id_returns_none_when_collection_is_none(tmp_path):
    import blammo.ui.previews_collection as pc

    preview = tmp_path / "abc.png"
    preview.write_bytes(b"")

    result = pc.get_icon_id("abc", str(preview))

    assert result is None


def test_get_icon_id_returns_none_when_path_is_none():
    import blammo.ui.previews_collection as pc

    pc._collection = MagicMock()

    result = pc.get_icon_id("abc", None)

    assert result is None


def test_get_icon_id_returns_none_when_file_missing():
    import blammo.ui.previews_collection as pc

    pc._collection = MagicMock()

    result = pc.get_icon_id("abc", "/nonexistent/path/abc.png")

    assert result is None


def test_get_icon_id_loads_on_first_access(tmp_path):
    import blammo.ui.previews_collection as pc

    preview = tmp_path / "abc.png"
    preview.write_bytes(b"")

    mock_col = MagicMock()
    mock_col.__contains__ = MagicMock(return_value=False)
    mock_col.__getitem__ = MagicMock(return_value=MagicMock(icon_id=42))
    pc._collection = mock_col

    result = pc.get_icon_id("abc", str(preview))

    mock_col.load.assert_called_once_with("abc", str(preview), "IMAGE")
    assert result == 42


def test_get_icon_id_uses_cache_on_second_access(tmp_path):
    import blammo.ui.previews_collection as pc

    preview = tmp_path / "abc.png"
    preview.write_bytes(b"")

    mock_col = MagicMock()
    mock_col.__contains__ = MagicMock(return_value=True)
    mock_col.__getitem__ = MagicMock(return_value=MagicMock(icon_id=99))
    pc._collection = mock_col

    result = pc.get_icon_id("abc", str(preview))

    mock_col.load.assert_not_called()
    assert result == 99


def test_get_icon_id_returns_icon_id_integer(tmp_path):
    import blammo.ui.previews_collection as pc

    preview = tmp_path / "xyz.png"
    preview.write_bytes(b"")

    mock_entry = MagicMock()
    mock_entry.icon_id = 12345
    mock_col = MagicMock()
    mock_col.__contains__ = MagicMock(return_value=False)
    mock_col.__getitem__ = MagicMock(return_value=mock_entry)
    pc._collection = mock_col

    result = pc.get_icon_id("xyz", str(preview))

    assert result == 12345


# ---------------------------------------------------------------------------
# get_placeholder_icon_id()
# ---------------------------------------------------------------------------


def test_get_placeholder_icon_id_returns_none_when_collection_is_none():
    import blammo.ui.previews_collection as pc

    result = pc.get_placeholder_icon_id("MESH")

    assert result is None


def test_get_placeholder_icon_id_returns_none_for_unknown_type():
    import blammo.ui.previews_collection as pc

    pc._collection = MagicMock()

    result = pc.get_placeholder_icon_id("UNKNOWN_TYPE")

    assert result is None


def test_get_placeholder_icon_id_returns_none_when_file_missing():
    import blammo.ui.previews_collection as pc

    pc._collection = MagicMock()

    with patch("blammo.ui.previews_collection._RESOURCES_DIR", __import__("pathlib").Path("/nonexistent")):
        result = pc.get_placeholder_icon_id("MESH")

    assert result is None


def test_get_placeholder_icon_id_loads_from_resources(tmp_path):
    import blammo.ui.previews_collection as pc

    img = tmp_path / "placeholder_mesh.png"
    img.write_bytes(b"")

    mock_col = MagicMock()
    mock_col.__contains__ = MagicMock(return_value=False)
    mock_col.__getitem__ = MagicMock(return_value=MagicMock(icon_id=77))
    pc._collection = mock_col

    with patch("blammo.ui.previews_collection._RESOURCES_DIR", tmp_path):
        result = pc.get_placeholder_icon_id("MESH")

    mock_col.load.assert_called_once_with("PLACEHOLDER_MESH", str(img), "IMAGE")
    assert result == 77


def test_get_placeholder_icon_id_uses_cache(tmp_path):
    import blammo.ui.previews_collection as pc

    img = tmp_path / "placeholder_material.png"
    img.write_bytes(b"")

    mock_col = MagicMock()
    mock_col.__contains__ = MagicMock(return_value=True)
    mock_col.__getitem__ = MagicMock(return_value=MagicMock(icon_id=88))
    pc._collection = mock_col

    with patch("blammo.ui.previews_collection._RESOURCES_DIR", tmp_path):
        result = pc.get_placeholder_icon_id("MATERIAL")

    mock_col.load.assert_not_called()
    assert result == 88


def test_get_placeholder_icon_id_covers_all_asset_types(tmp_path):
    """All three known asset types must resolve to a placeholder file."""
    import blammo.ui.previews_collection as pc

    for asset_type in ("MATERIAL", "MESH", "NODE_GROUP"):
        filename = pc._PLACEHOLDER_FILENAMES[asset_type]
        (tmp_path / filename).write_bytes(b"")

    mock_col = MagicMock()
    mock_col.__contains__ = MagicMock(return_value=False)
    mock_col.__getitem__ = MagicMock(return_value=MagicMock(icon_id=1))
    pc._collection = mock_col

    with patch("blammo.ui.previews_collection._RESOURCES_DIR", tmp_path):
        for asset_type in ("MATERIAL", "MESH", "NODE_GROUP"):
            assert pc.get_placeholder_icon_id(asset_type) is not None

