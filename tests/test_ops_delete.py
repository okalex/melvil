"""Tests for ops/delete.py — BLAMMO_OT_delete_asset."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
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


def _mock_open_db(conn):
    @contextmanager
    def _cm(_path):
        yield conn
    return _cm


SAMPLE = dict(
    id="aaaaaaaa-0000-4000-8000-000000000001",
    name="Red Metal",
    type="MATERIAL",
    blend_path="red_metal_aaaaaaaa.blend",
)


def _make_op(asset_id=""):
    from blammo.ops.delete import BLAMMO_OT_delete_asset

    op = BLAMMO_OT_delete_asset()
    op.asset_id = asset_id
    return op


# ---------------------------------------------------------------------------
# poll()
# ---------------------------------------------------------------------------


class TestPoll:
    def test_always_returns_true(self):
        from blammo.ops.delete import BLAMMO_OT_delete_asset

        assert BLAMMO_OT_delete_asset.poll(MagicMock()) is True


# ---------------------------------------------------------------------------
# execute()
# ---------------------------------------------------------------------------


class TestExecute:
    def test_no_asset_id_returns_cancelled(self):
        op = _make_op(asset_id="")
        with patch("blammo.ops.delete.resolve_library_root", return_value="/lib"):
            result = op.execute(MagicMock())
        assert result == {"CANCELLED"}

    def test_whitespace_id_returns_cancelled(self):
        op = _make_op(asset_id="   ")
        with patch("blammo.ops.delete.resolve_library_root", return_value="/lib"):
            result = op.execute(MagicMock())
        assert result == {"CANCELLED"}

    def test_library_not_configured_returns_cancelled(self):
        from blammo.core.library import LibraryNotConfiguredError

        op = _make_op(asset_id=SAMPLE["id"])
        with patch("blammo.ops.delete.resolve_library_root", side_effect=LibraryNotConfiguredError("x")):
            result = op.execute(MagicMock())
        assert result == {"CANCELLED"}

    def test_asset_not_in_db_returns_cancelled(self, conn):
        op = _make_op(asset_id="does-not-exist")

        with patch("blammo.ops.delete.resolve_library_root", return_value="/tmp/lib"), \
             patch("blammo.ops.delete.resolve_db_path", return_value=":memory:"), \
             patch("blammo.ops.delete.open_db", _mock_open_db(conn)):
            result = op.execute(MagicMock())

        assert result == {"CANCELLED"}

    def test_deletes_blend_file_and_db_record(self, conn, tmp_path):
        assets_db.insert_asset(conn, **SAMPLE)

        # Create a fake .blend file for the operator to delete.
        blend_file = tmp_path / SAMPLE["blend_path"]
        blend_file.write_bytes(b"BLND")

        op = _make_op(asset_id=SAMPLE["id"])

        with patch("blammo.ops.delete.resolve_library_root", return_value=tmp_path), \
             patch("blammo.ops.delete.resolve_db_path", return_value=":memory:"), \
             patch("blammo.ops.delete.open_db", _mock_open_db(conn)):
            result = op.execute(MagicMock())

        assert result == {"FINISHED"}
        assert not blend_file.exists()
        assert assets_db.get_asset(conn, SAMPLE["id"]) is None

    def test_succeeds_when_blend_file_already_missing(self, conn, tmp_path):
        """If the .blend file is already gone, the DB record should still be removed."""
        assets_db.insert_asset(conn, **SAMPLE)

        op = _make_op(asset_id=SAMPLE["id"])

        with patch("blammo.ops.delete.resolve_library_root", return_value=tmp_path), \
             patch("blammo.ops.delete.resolve_db_path", return_value=":memory:"), \
             patch("blammo.ops.delete.open_db", _mock_open_db(conn)):
            result = op.execute(MagicMock())

        assert result == {"FINISHED"}
        assert assets_db.get_asset(conn, SAMPLE["id"]) is None

    def test_does_not_delete_textures(self, conn, tmp_path):
        """Texture files must not be touched — they may be shared."""
        assets_db.insert_asset(conn, **SAMPLE)
        textures_dir = tmp_path / "textures"
        textures_dir.mkdir()
        shared_texture = textures_dir / "rock.png"
        shared_texture.write_bytes(b"PNG")

        op = _make_op(asset_id=SAMPLE["id"])

        with patch("blammo.ops.delete.resolve_library_root", return_value=tmp_path), \
             patch("blammo.ops.delete.resolve_db_path", return_value=":memory:"), \
             patch("blammo.ops.delete.open_db", _mock_open_db(conn)):
            op.execute(MagicMock())

        # Texture file must still be present.
        assert shared_texture.exists()

    def test_deletes_preview_file_when_present(self, conn, tmp_path):
        assets_db.insert_asset(conn, **SAMPLE, preview_path="previews/abc.png")
        preview_file = tmp_path / "previews" / "abc.png"
        preview_file.parent.mkdir()
        preview_file.write_bytes(b"PNG")

        op = _make_op(asset_id=SAMPLE["id"])

        with patch("blammo.ops.delete.resolve_library_root", return_value=tmp_path), \
             patch("blammo.ops.delete.resolve_db_path", return_value=":memory:"), \
             patch("blammo.ops.delete.open_db", _mock_open_db(conn)):
            result = op.execute(MagicMock())

        assert result == {"FINISHED"}
        assert not preview_file.exists()

    def test_succeeds_when_preview_file_already_missing(self, conn, tmp_path):
        assets_db.insert_asset(conn, **SAMPLE, preview_path="previews/abc.png")
        # Do NOT create the preview file — it's already gone.

        op = _make_op(asset_id=SAMPLE["id"])

        with patch("blammo.ops.delete.resolve_library_root", return_value=tmp_path), \
             patch("blammo.ops.delete.resolve_db_path", return_value=":memory:"), \
             patch("blammo.ops.delete.open_db", _mock_open_db(conn)):
            result = op.execute(MagicMock())

        assert result == {"FINISHED"}
        assert assets_db.get_asset(conn, SAMPLE["id"]) is None

    def test_succeeds_when_no_preview_path(self, conn, tmp_path):
        """Assets with no preview_path should delete cleanly without touching previews dir."""
        assets_db.insert_asset(conn, **SAMPLE)  # preview_path defaults to None

        op = _make_op(asset_id=SAMPLE["id"])

        with patch("blammo.ops.delete.resolve_library_root", return_value=tmp_path), \
             patch("blammo.ops.delete.resolve_db_path", return_value=":memory:"), \
             patch("blammo.ops.delete.open_db", _mock_open_db(conn)):
            result = op.execute(MagicMock())

        assert result == {"FINISHED"}

    def test_oserror_during_preview_delete_is_non_fatal(self, conn, tmp_path):
        assets_db.insert_asset(conn, **SAMPLE, preview_path="previews/abc.png")

        op = _make_op(asset_id=SAMPLE["id"])

        with patch("blammo.ops.delete.resolve_library_root", return_value=tmp_path), \
             patch("blammo.ops.delete.resolve_db_path", return_value=":memory:"), \
             patch("blammo.ops.delete.open_db", _mock_open_db(conn)), \
             patch("pathlib.Path.unlink", side_effect=OSError("permission denied")):
            result = op.execute(MagicMock())

        assert result == {"FINISHED"}
        assert assets_db.get_asset(conn, SAMPLE["id"]) is None
