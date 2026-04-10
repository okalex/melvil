"""Tests for ops/save.py — MELVIL_OT_save_asset."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest

from melvil.db.connection import migrate


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
    """Return a context manager mock that yields ``conn``."""
    @contextmanager
    def _cm(_path):
        yield conn
    return _cm


def _make_mesh_object(name="Cube", material=None):
    obj = MagicMock()
    obj.name = name
    obj.type = "MESH"
    obj.active_material = material
    return obj


def _make_material(name="Red Metal"):
    mat = MagicMock()
    mat.name = name
    return mat


def _make_context(obj=None, area_type="VIEW_3D"):
    ctx = MagicMock()
    ctx.active_object = obj
    area = MagicMock()
    area.type = area_type
    ctx.area = area
    return ctx


# ---------------------------------------------------------------------------
# poll()
# ---------------------------------------------------------------------------


class TestPoll:
    def test_returns_true_with_active_object(self):
        from melvil.ops.save import MELVIL_OT_save_asset

        ctx = _make_context(obj=_make_mesh_object())
        assert MELVIL_OT_save_asset.poll(ctx) is True

    def test_returns_false_without_active_object(self):
        from melvil.ops.save import MELVIL_OT_save_asset

        ctx = _make_context(obj=None)
        assert MELVIL_OT_save_asset.poll(ctx) is False


# ---------------------------------------------------------------------------
# execute() — MESH
# ---------------------------------------------------------------------------


class TestExecuteMesh:
    def _make_op(self, mesh_name="Cube"):
        from melvil.ops.save import MELVIL_OT_save_asset

        op = MELVIL_OT_save_asset()
        op.save_type = "MESH"
        op.mesh_name = mesh_name
        op.material_name = ""
        return op

    def test_save_mesh_returns_finished(self, conn):
        from melvil.ops.save import MELVIL_OT_save_asset

        op = self._make_op()
        ctx = _make_context(obj=_make_mesh_object())

        with patch("melvil.ops.save.resolve_library_root", return_value="/lib"), \
             patch("melvil.ops.save.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ops.save.open_db", _mock_open_db(conn)), \
             patch("melvil.ops.save.AssetWriter") as MockWriter:
            MockWriter.return_value.write.return_value = "aaaaaaaa-0000-4000-8000-000000000001"
            result = op.execute(ctx)

        assert result == {"FINISHED"}

    def test_save_mesh_calls_writer_with_correct_args(self, conn):
        from melvil.ops.save import MELVIL_OT_save_asset

        obj = _make_mesh_object(name="Suzanne")
        op = self._make_op(mesh_name="Suzanne")
        ctx = _make_context(obj=obj)

        with patch("melvil.ops.save.resolve_library_root", return_value="/lib"), \
             patch("melvil.ops.save.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ops.save.open_db", _mock_open_db(conn)), \
             patch("melvil.ops.save.AssetWriter") as MockWriter:
            mock_instance = MockWriter.return_value
            mock_instance.write.return_value = "aaaaaaaa-0000-4000-8000-000000000001"
            op.execute(ctx)

        mock_instance.write.assert_called_once_with(obj, "Suzanne", "MESH")

    def test_error_when_no_mesh_object(self, conn):
        from melvil.ops.save import MELVIL_OT_save_asset

        obj = MagicMock()
        obj.type = "CURVE"
        op = self._make_op()
        ctx = _make_context(obj=obj)

        with patch("melvil.ops.save.resolve_library_root", return_value="/lib"), \
             patch("melvil.ops.save.resolve_db_path", return_value=":memory:"):
            result = op.execute(ctx)

        assert result == {"CANCELLED"}

    def test_error_when_empty_mesh_name(self, conn):
        from melvil.ops.save import MELVIL_OT_save_asset

        op = self._make_op(mesh_name="   ")
        ctx = _make_context(obj=_make_mesh_object())

        with patch("melvil.ops.save.resolve_library_root", return_value="/lib"), \
             patch("melvil.ops.save.resolve_db_path", return_value=":memory:"):
            result = op.execute(ctx)

        assert result == {"CANCELLED"}

    def test_error_when_library_not_configured(self, conn):
        from melvil.ops.save import MELVIL_OT_save_asset
        from melvil.core.library import LibraryNotConfiguredError

        op = self._make_op()
        ctx = _make_context(obj=_make_mesh_object())

        with patch("melvil.ops.save.resolve_library_root", side_effect=LibraryNotConfiguredError("not set")):
            result = op.execute(ctx)

        assert result == {"CANCELLED"}


# ---------------------------------------------------------------------------
# execute() — MATERIAL
# ---------------------------------------------------------------------------


class TestExecuteMaterial:
    def _make_op(self, material_name="Red Metal"):
        from melvil.ops.save import MELVIL_OT_save_asset

        op = MELVIL_OT_save_asset()
        op.save_type = "MATERIAL"
        op.mesh_name = ""
        op.material_name = material_name
        return op

    def test_save_material_returns_finished(self, conn):
        mat = _make_material()
        obj = _make_mesh_object(material=mat)
        op = self._make_op()
        ctx = _make_context(obj=obj)

        with patch("melvil.ops.save.resolve_library_root", return_value="/lib"), \
             patch("melvil.ops.save.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ops.save.open_db", _mock_open_db(conn)), \
             patch("melvil.ops.save.AssetWriter") as MockWriter:
            MockWriter.return_value.write.return_value = "bbbbbbbb-0000-4000-8000-000000000002"
            result = op.execute(ctx)

        assert result == {"FINISHED"}

    def test_save_material_calls_writer_with_correct_args(self, conn):
        mat = _make_material(name="Blue Glass")
        obj = _make_mesh_object(material=mat)
        op = self._make_op(material_name="Blue Glass")
        ctx = _make_context(obj=obj)

        with patch("melvil.ops.save.resolve_library_root", return_value="/lib"), \
             patch("melvil.ops.save.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ops.save.open_db", _mock_open_db(conn)), \
             patch("melvil.ops.save.AssetWriter") as MockWriter:
            mock_instance = MockWriter.return_value
            mock_instance.write.return_value = "bbbbbbbb-0000-4000-8000-000000000002"
            op.execute(ctx)

        mock_instance.write.assert_called_once_with(mat, "Blue Glass", "MATERIAL")

    def test_error_when_no_active_material(self):
        from melvil.ops.save import MELVIL_OT_save_asset

        obj = _make_mesh_object(material=None)
        op = self._make_op()
        ctx = _make_context(obj=obj)

        with patch("melvil.ops.save.resolve_library_root", return_value="/lib"), \
             patch("melvil.ops.save.resolve_db_path", return_value=":memory:"):
            result = op.execute(ctx)

        assert result == {"CANCELLED"}

    def test_error_when_empty_material_name(self):
        from melvil.ops.save import MELVIL_OT_save_asset

        mat = _make_material()
        obj = _make_mesh_object(material=mat)
        op = self._make_op(material_name="")
        ctx = _make_context(obj=obj)

        with patch("melvil.ops.save.resolve_library_root", return_value="/lib"), \
             patch("melvil.ops.save.resolve_db_path", return_value=":memory:"):
            result = op.execute(ctx)

        assert result == {"CANCELLED"}


# ---------------------------------------------------------------------------
# execute() — BOTH
# ---------------------------------------------------------------------------


class TestExecuteBoth:
    def test_saves_both_calls_writer_twice(self, conn):
        from melvil.ops.save import MELVIL_OT_save_asset

        mat = _make_material(name="Iron")
        obj = _make_mesh_object(name="Sphere", material=mat)

        op = MELVIL_OT_save_asset()
        op.save_type = "BOTH"
        op.mesh_name = "Sphere"
        op.material_name = "Iron"
        ctx = _make_context(obj=obj)

        with patch("melvil.ops.save.resolve_library_root", return_value="/lib"), \
             patch("melvil.ops.save.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ops.save.open_db", _mock_open_db(conn)), \
             patch("melvil.ops.save.AssetWriter") as MockWriter:
            mock_instance = MockWriter.return_value
            mock_instance.write.side_effect = [
                "aaaaaaaa-0000-4000-8000-000000000001",
                "bbbbbbbb-0000-4000-8000-000000000002",
            ]
            result = op.execute(ctx)

        assert result == {"FINISHED"}
        assert mock_instance.write.call_count == 2
        calls = mock_instance.write.call_args_list
        assert calls[0].args == (obj, "Sphere", "MESH")
        assert calls[1].args == (mat, "Iron", "MATERIAL")

    def test_both_fails_when_no_material(self, conn):
        from melvil.ops.save import MELVIL_OT_save_asset

        obj = _make_mesh_object(material=None)

        op = MELVIL_OT_save_asset()
        op.save_type = "BOTH"
        op.mesh_name = "Cube"
        op.material_name = "Mat"
        ctx = _make_context(obj=obj)

        with patch("melvil.ops.save.resolve_library_root", return_value="/lib"), \
             patch("melvil.ops.save.resolve_db_path", return_value=":memory:"):
            result = op.execute(ctx)

        assert result == {"CANCELLED"}
