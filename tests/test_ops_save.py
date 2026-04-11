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

        from melvil.db.kits import DEFAULT_KIT_ID
        mock_instance.write.assert_called_once_with(obj, "Suzanne", "MESH", kit_id=DEFAULT_KIT_ID)

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

        from melvil.db.kits import DEFAULT_KIT_ID
        mock_instance.write.assert_called_once_with(mat, "Blue Glass", "MATERIAL", kit_id=DEFAULT_KIT_ID)

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
# invoke() — save_type context detection
# ---------------------------------------------------------------------------


class TestInvokeContextDetection:
    def _invoke(self, area_type="VIEW_3D", obj=None):
        from melvil.ops.save import MELVIL_OT_save_asset

        op = MELVIL_OT_save_asset()
        op.save_type = "MESH"   # default before invoke
        op.mesh_name = ""
        op.material_name = ""
        ctx = _make_context(obj=obj, area_type=area_type)

        with patch.object(ctx.window_manager, "invoke_props_dialog", return_value={"RUNNING_MODAL"}):
            op.invoke(ctx, MagicMock())
        return op

    def test_node_editor_with_material_selects_material(self):
        mat = _make_material()
        obj = _make_mesh_object(material=mat)
        op = self._invoke(area_type="NODE_EDITOR", obj=obj)
        assert op.save_type == "MATERIAL"

    def test_properties_editor_with_material_selects_material(self):
        mat = _make_material()
        obj = _make_mesh_object(material=mat)
        op = self._invoke(area_type="PROPERTIES", obj=obj)
        assert op.save_type == "MATERIAL"

    def test_view3d_mesh_with_material_selects_mesh(self):
        mat = _make_material()
        obj = _make_mesh_object(material=mat)
        op = self._invoke(area_type="VIEW_3D", obj=obj)
        assert op.save_type == "MESH"

    def test_view3d_mesh_without_material_selects_mesh(self):
        obj = _make_mesh_object(material=None)
        op = self._invoke(area_type="VIEW_3D", obj=obj)
        assert op.save_type == "MESH"

    def test_node_editor_with_group_node_selects_node_group(self):
        """Active GROUP node in node editor → save_type must be NODE_GROUP."""
        from melvil.ops.save import MELVIL_OT_save_asset

        ng = MagicMock()
        ng.name = "Noise Setup"
        active_node = MagicMock()
        active_node.type = "GROUP"
        active_node.node_tree = ng
        active_node.label = ""  # no custom label → falls back to node_tree.name

        op = MELVIL_OT_save_asset()
        op.save_type = "MESH"
        op.mesh_name = ""
        op.material_name = ""
        op.node_group_name = ""

        ctx = _make_context(obj=_make_mesh_object(), area_type="NODE_EDITOR")
        ctx.active_node = active_node

        with patch.object(ctx.window_manager, "invoke_props_dialog", return_value={"RUNNING_MODAL"}):
            op.invoke(ctx, MagicMock())

        assert op.save_type == "NODE_GROUP"
        assert op.node_group_name == "Noise Setup"

    def test_node_group_name_uses_label_when_set(self):
        """When the node has a custom label, it should be used over node_tree.name."""
        from melvil.ops.save import MELVIL_OT_save_asset

        ng = MagicMock()
        ng.name = "Color Ramp"  # internal datablock name
        active_node = MagicMock()
        active_node.type = "GROUP"
        active_node.node_tree = ng
        active_node.label = "Color Stuff"  # user-visible label

        op = MELVIL_OT_save_asset()
        op.save_type = "MESH"
        op.mesh_name = ""
        op.material_name = ""
        op.node_group_name = ""

        ctx = _make_context(obj=_make_mesh_object(), area_type="NODE_EDITOR")
        ctx.active_node = active_node

        with patch.object(ctx.window_manager, "invoke_props_dialog", return_value={"RUNNING_MODAL"}):
            op.invoke(ctx, MagicMock())

        assert op.node_group_name == "Color Stuff"

    def test_node_editor_with_material_and_no_group_node_selects_material(self):
        """NODE_EDITOR with a material active but no GROUP node → MATERIAL (unchanged)."""
        mat = _make_material()
        obj = _make_mesh_object(material=mat)
        op = self._invoke(area_type="NODE_EDITOR", obj=obj)
        assert op.save_type == "MATERIAL"

    def test_node_editor_group_node_takes_priority_over_material(self):
        """A GROUP node active in node editor beats the material context."""
        from melvil.ops.save import MELVIL_OT_save_asset

        ng = MagicMock()
        ng.name = "Fancy Group"
        active_node = MagicMock()
        active_node.type = "GROUP"
        active_node.node_tree = ng
        active_node.label = ""  # no custom label

        mat = _make_material()
        obj = _make_mesh_object(material=mat)
        op = MELVIL_OT_save_asset()
        op.save_type = "MESH"
        op.mesh_name = ""
        op.material_name = ""
        op.node_group_name = ""

        ctx = _make_context(obj=obj, area_type="NODE_EDITOR")
        ctx.active_node = active_node

        with patch.object(ctx.window_manager, "invoke_props_dialog", return_value={"RUNNING_MODAL"}):
            op.invoke(ctx, MagicMock())

        assert op.save_type == "NODE_GROUP"


# ---------------------------------------------------------------------------
# poll() — node group
# ---------------------------------------------------------------------------


class TestPollNodeGroup:
    def test_poll_true_with_group_node_and_no_active_object(self):
        """poll() returns True when active_node is a GROUP even without active_object."""
        from melvil.ops.save import MELVIL_OT_save_asset

        ng = MagicMock()
        active_node = MagicMock()
        active_node.type = "GROUP"
        active_node.node_tree = ng

        ctx = MagicMock()
        ctx.active_object = None
        ctx.active_node = active_node

        assert MELVIL_OT_save_asset.poll(ctx) is True

    def test_poll_false_without_active_object_or_group_node(self):
        from melvil.ops.save import MELVIL_OT_save_asset

        ctx = MagicMock()
        ctx.active_object = None
        active_node = MagicMock()
        active_node.type = "MATH"  # not a GROUP node
        active_node.node_tree = None
        ctx.active_node = active_node

        assert MELVIL_OT_save_asset.poll(ctx) is False


# ---------------------------------------------------------------------------
# execute() — NODE_GROUP
# ---------------------------------------------------------------------------


class TestExecuteNodeGroup:
    def _make_op(self, node_group_name="Noise FX"):
        from melvil.ops.save import MELVIL_OT_save_asset

        op = MELVIL_OT_save_asset()
        op.save_type = "NODE_GROUP"
        op.mesh_name = ""
        op.material_name = ""
        op.node_group_name = node_group_name
        return op

    def _make_ng_context(self, ng_name="Noise FX"):
        ng = MagicMock()
        ng.name = ng_name
        active_node = MagicMock()
        active_node.type = "GROUP"
        active_node.node_tree = ng
        ctx = _make_context(obj=_make_mesh_object(), area_type="NODE_EDITOR")
        ctx.active_node = active_node
        return ctx, ng

    def test_save_node_group_returns_finished(self, conn):
        op = self._make_op()
        ctx, _ = self._make_ng_context()

        with patch("melvil.ops.save.resolve_library_root", return_value="/lib"), \
             patch("melvil.ops.save.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ops.save.open_db", _mock_open_db(conn)), \
             patch("melvil.ops.save.AssetWriter") as MockWriter:
            MockWriter.return_value.write.return_value = "dddddddd-0000-4000-8000-000000000004"
            result = op.execute(ctx)

        assert result == {"FINISHED"}

    def test_save_node_group_calls_writer_with_correct_args(self, conn):
        op = self._make_op(node_group_name="Noise FX")
        ctx, ng = self._make_ng_context(ng_name="Noise FX")

        with patch("melvil.ops.save.resolve_library_root", return_value="/lib"), \
             patch("melvil.ops.save.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ops.save.open_db", _mock_open_db(conn)), \
             patch("melvil.ops.save.AssetWriter") as MockWriter:
            mock_instance = MockWriter.return_value
            mock_instance.write.return_value = "dddddddd-0000-4000-8000-000000000004"
            op.execute(ctx)

        from melvil.db.kits import DEFAULT_KIT_ID
        mock_instance.write.assert_called_once_with(ng, "Noise FX", "NODE_GROUP", kit_id=DEFAULT_KIT_ID)

    def test_error_when_no_active_node(self, conn):
        op = self._make_op()
        ctx = _make_context(obj=_make_mesh_object(), area_type="NODE_EDITOR")
        ctx.active_node = None

        with patch("melvil.ops.save.resolve_library_root", return_value="/lib"), \
             patch("melvil.ops.save.resolve_db_path", return_value=":memory:"):
            result = op.execute(ctx)

        assert result == {"CANCELLED"}

    def test_error_when_active_node_has_no_node_tree(self, conn):
        op = self._make_op()
        ctx = _make_context(obj=_make_mesh_object(), area_type="NODE_EDITOR")
        active_node = MagicMock()
        active_node.type = "GROUP"
        active_node.node_tree = None
        ctx.active_node = active_node

        with patch("melvil.ops.save.resolve_library_root", return_value="/lib"), \
             patch("melvil.ops.save.resolve_db_path", return_value=":memory:"):
            result = op.execute(ctx)

        assert result == {"CANCELLED"}

    def test_error_when_empty_node_group_name(self, conn):
        op = self._make_op(node_group_name="   ")
        ctx, _ = self._make_ng_context()

        with patch("melvil.ops.save.resolve_library_root", return_value="/lib"), \
             patch("melvil.ops.save.resolve_db_path", return_value=":memory:"):
            result = op.execute(ctx)

        assert result == {"CANCELLED"}


# ---------------------------------------------------------------------------
# MELVIL_OT_save_nodes_as_asset — poll
# ---------------------------------------------------------------------------


def _make_node_editor_context(nodes=None, has_space=True, area_type="NODE_EDITOR"):
    ctx = MagicMock()
    area = MagicMock()
    area.type = area_type
    ctx.area = area
    if has_space:
        nt = MagicMock()
        nt.nodes = nodes or []
        ctx.space_data.node_tree = nt
    else:
        ctx.space_data = None
    return ctx


def _make_selectable_node(select: bool = True, node_type: str = "SHADER", ng=None):
    node = MagicMock()
    node.select = select
    node.type = node_type
    node.node_tree = ng
    return node


class TestSaveNodesAsAssetPoll:
    def test_poll_true_for_single_selected_group_node(self):
        from melvil.ops.save import MELVIL_OT_save_nodes_as_asset

        ng = MagicMock()
        node = _make_selectable_node(select=True, node_type="GROUP", ng=ng)
        ctx = _make_node_editor_context(nodes=[node])
        assert MELVIL_OT_save_nodes_as_asset.poll(ctx) is True

    def test_poll_false_when_no_selected_nodes(self):
        from melvil.ops.save import MELVIL_OT_save_nodes_as_asset

        ctx = _make_node_editor_context(nodes=[_make_selectable_node(select=False)])
        assert MELVIL_OT_save_nodes_as_asset.poll(ctx) is False

    def test_poll_false_for_multiple_selected_nodes(self):
        """Multiple selected nodes should disable the operator."""
        from melvil.ops.save import MELVIL_OT_save_nodes_as_asset

        ng = MagicMock()
        nodes = [
            _make_selectable_node(select=True, node_type="GROUP", ng=ng),
            _make_selectable_node(select=True, node_type="GROUP", ng=ng),
        ]
        ctx = _make_node_editor_context(nodes=nodes)
        assert MELVIL_OT_save_nodes_as_asset.poll(ctx) is False

    def test_poll_false_for_single_non_group_node(self):
        """A single selected non-GROUP node should disable the operator."""
        from melvil.ops.save import MELVIL_OT_save_nodes_as_asset

        ctx = _make_node_editor_context(nodes=[_make_selectable_node(select=True, node_type="MATH")])
        assert MELVIL_OT_save_nodes_as_asset.poll(ctx) is False

    def test_poll_false_outside_node_editor(self):
        from melvil.ops.save import MELVIL_OT_save_nodes_as_asset

        ng = MagicMock()
        ctx = _make_node_editor_context(
            nodes=[_make_selectable_node(select=True, node_type="GROUP", ng=ng)],
            area_type="VIEW_3D",
        )
        assert MELVIL_OT_save_nodes_as_asset.poll(ctx) is False

    def test_poll_false_when_no_node_tree(self):
        from melvil.ops.save import MELVIL_OT_save_nodes_as_asset

        ctx = _make_node_editor_context(has_space=False)
        ctx.area.type = "NODE_EDITOR"
        assert MELVIL_OT_save_nodes_as_asset.poll(ctx) is False

    def test_poll_false_when_empty_node_list(self):
        from melvil.ops.save import MELVIL_OT_save_nodes_as_asset

        ctx = _make_node_editor_context(nodes=[])
        assert MELVIL_OT_save_nodes_as_asset.poll(ctx) is False


# ---------------------------------------------------------------------------
# MELVIL_OT_save_nodes_as_asset — invoke
# ---------------------------------------------------------------------------


class TestSaveNodesAsAssetInvoke:
    def test_invoke_delegates_to_save_asset(self):
        """invoke() must call melvil.save_asset(INVOKE_DEFAULT) unconditionally."""
        import bpy
        from melvil.ops.save import MELVIL_OT_save_nodes_as_asset

        ng = MagicMock()
        node = _make_selectable_node(select=True, node_type="GROUP", ng=ng)
        ctx = _make_node_editor_context(nodes=[node])

        with patch.object(bpy.ops, "melvil", create=True) as mock_melvil_ops:
            mock_melvil_ops.save_asset.return_value = {"RUNNING_MODAL"}
            op = MELVIL_OT_save_nodes_as_asset()
            result = op.invoke(ctx, MagicMock())

        mock_melvil_ops.save_asset.assert_called_once_with("INVOKE_DEFAULT")
        assert result == {"RUNNING_MODAL"}


# ---------------------------------------------------------------------------
# execute() — tags property
# ---------------------------------------------------------------------------


class TestExecuteTags:
    """MELVIL_OT_save_asset should apply tags via add_asset_tag after save."""

    def _make_op(self, tags=""):
        from melvil.ops.save import MELVIL_OT_save_asset

        op = MELVIL_OT_save_asset()
        op.save_type = "MESH"
        op.mesh_name = "Cube"
        op.material_name = ""
        op.tags = tags
        return op

    def test_tags_committed_to_db(self, conn):
        """Tags must be committed so they are visible on a new connection."""
        from melvil.db import assets as assets_db
        from melvil.db import tags as tags_db

        asset_id = "dddddddd-0000-4000-8000-000000000001"
        assets_db.insert_asset(conn, id=asset_id, name="Cube", type="MESH", blend_path="cube3.blend")
        conn.commit()  # ensure asset is visible before we close conn below
        op = self._make_op(tags="metal")
        ctx = _make_context(obj=_make_mesh_object())

        with patch("melvil.ops.save.resolve_library_root", return_value="/lib"), \
             patch("melvil.ops.save.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ops.save.open_db", _mock_open_db(conn)), \
             patch("melvil.ops.save.AssetWriter") as MockWriter:
            MockWriter.return_value.write.return_value = asset_id
            op.execute(ctx)

        # Read tags back on the *same* conn but verify they were committed
        # by checking the conn is not in a dirty transaction.
        assert conn.in_transaction is False
        applied = tags_db.get_asset_tags(conn, asset_id)
        assert "metal" in applied

    def test_tags_applied_on_save(self, conn):
        from melvil.db import assets as assets_db
        from melvil.db import tags as tags_db

        asset_id = "eeeeeeee-0000-4000-8000-000000000001"
        # Pre-insert the asset so FK constraints on asset_tags pass.
        assets_db.insert_asset(conn, id=asset_id, name="Cube", type="MESH", blend_path="cube.blend")
        op = self._make_op(tags="metal, shiny")
        ctx = _make_context(obj=_make_mesh_object())

        with patch("melvil.ops.save.resolve_library_root", return_value="/lib"), \
             patch("melvil.ops.save.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ops.save.open_db", _mock_open_db(conn)), \
             patch("melvil.ops.save.AssetWriter") as MockWriter:
            MockWriter.return_value.write.return_value = asset_id
            result = op.execute(ctx)

        assert result == {"FINISHED"}
        applied = tags_db.get_asset_tags(conn, asset_id)
        assert "metal" in applied
        assert "shiny" in applied

    def test_empty_tags_property_does_not_fail(self, conn):
        asset_id = "ffffffff-0000-4000-8000-000000000001"
        op = self._make_op(tags="")
        ctx = _make_context(obj=_make_mesh_object())

        with patch("melvil.ops.save.resolve_library_root", return_value="/lib"), \
             patch("melvil.ops.save.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ops.save.open_db", _mock_open_db(conn)), \
             patch("melvil.ops.save.AssetWriter") as MockWriter:
            MockWriter.return_value.write.return_value = asset_id
            result = op.execute(ctx)

        assert result == {"FINISHED"}

    def test_tags_normalized_on_save(self, conn):
        from melvil.db import assets as assets_db
        from melvil.db import tags as tags_db

        asset_id = "11111111-0000-4000-8000-000000000001"
        # Pre-insert the asset so FK constraints on asset_tags pass.
        assets_db.insert_asset(conn, id=asset_id, name="Cube", type="MESH", blend_path="cube2.blend")
        op = self._make_op(tags="  Metal  , PBR Material")
        ctx = _make_context(obj=_make_mesh_object())

        with patch("melvil.ops.save.resolve_library_root", return_value="/lib"), \
             patch("melvil.ops.save.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ops.save.open_db", _mock_open_db(conn)), \
             patch("melvil.ops.save.AssetWriter") as MockWriter:
            MockWriter.return_value.write.return_value = asset_id
            op.execute(ctx)

        applied = tags_db.get_asset_tags(conn, asset_id)
        assert "metal" in applied
        assert "pbr material" in applied


# ---------------------------------------------------------------------------
# draw() — tags field in save dialog
# ---------------------------------------------------------------------------


class TestDrawSaveDialog:
    """Verify the save dialog renders a Tags field below the Kit selector."""

    def _make_op(self, save_type="MESH"):
        from melvil.ops.save import MELVIL_OT_save_asset

        op = MELVIL_OT_save_asset()
        op.save_type = save_type
        op.mesh_name = "Cube"
        op.material_name = "Iron"
        op.node_group_name = "My Group"
        op.tags = ""
        op.layout = MagicMock()
        return op

    def _prop_calls(self, op):
        """Return list of (prop_name, kwargs) for each layout.prop() call."""
        return [(c[0][1], c[1]) for c in op.layout.prop.call_args_list]

    def test_tags_field_rendered_for_mesh(self):
        op = self._make_op("MESH")
        op.draw(MagicMock())
        prop_names = [c[0][1] for c in op.layout.prop.call_args_list]
        assert "tags" in prop_names

    def test_tags_field_rendered_for_material(self):
        op = self._make_op("MATERIAL")
        op.draw(MagicMock())
        prop_names = [c[0][1] for c in op.layout.prop.call_args_list]
        assert "tags" in prop_names

    def test_tags_field_rendered_for_node_group(self):
        op = self._make_op("NODE_GROUP")
        op.draw(MagicMock())
        prop_names = [c[0][1] for c in op.layout.prop.call_args_list]
        assert "tags" in prop_names

    def test_kit_id_rendered_before_tags(self):
        op = self._make_op("MESH")
        op.draw(MagicMock())
        prop_names = [c[0][1] for c in op.layout.prop.call_args_list]
        assert prop_names.index("kit_id") < prop_names.index("tags")

    def test_tags_field_label_is_tags(self):
        op = self._make_op("MESH")
        op.draw(MagicMock())
        tags_call = next(
            c for c in op.layout.prop.call_args_list if c[0][1] == "tags"
        )
        assert tags_call[1].get("text") == "Tags"

