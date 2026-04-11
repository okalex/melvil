"""Tests for ops/add_node_group.py — MELVIL_OT_add_node_group."""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import MagicMock, call, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_context(
    area_type: str = "NODE_EDITOR",
    tree_type: str = "SHADER",
    nodes: list | None = None,
):
    ctx = MagicMock()
    area = MagicMock()
    area.type = area_type
    ctx.area = area

    # Use a MagicMock for `nodes` so `.new()` and iteration both work.
    # If a specific list of nodes is provided, make the mock iterable over them.
    nt = MagicMock()
    nt.type = tree_type
    node_list = nodes if nodes is not None else []
    nt.nodes.__iter__ = MagicMock(return_value=iter(node_list))
    ctx.space_data.node_tree = nt

    # Simulate the area containing a WINDOW region at screen offset (50, 80).
    # Absolute mouse coords will be offset by those values in tests.
    canvas = MagicMock()
    canvas.type = "WINDOW"
    canvas.x = 50
    canvas.y = 80
    canvas.view2d.region_to_view.return_value = (100.0, 200.0)
    ctx.area.regions = [canvas]

    # Mirror Blender's UI_SCALE_FAC; tests use 1.0 so location == region_to_view result.
    ctx.preferences.system.ui_scale = 1.0

    return ctx


def _make_event(mx: int = 400, my: int = 300):
    event = MagicMock()
    event.mouse_x = mx
    event.mouse_y = my
    return event


def _mock_open_db(ng_mock):
    """Return an open_db replacement that yields a conn whose reader returns ng_mock."""
    @contextmanager
    def _cm(_path):
        yield MagicMock()
    return _cm


# ---------------------------------------------------------------------------
# poll()
# ---------------------------------------------------------------------------


class TestPoll:
    def test_poll_true_in_node_editor_with_node_tree(self):
        from melvil.ops.add_node_group import MELVIL_OT_add_node_group
        assert MELVIL_OT_add_node_group.poll(_make_context()) is True

    def test_poll_false_outside_node_editor(self):
        from melvil.ops.add_node_group import MELVIL_OT_add_node_group
        assert MELVIL_OT_add_node_group.poll(_make_context(area_type="VIEW_3D")) is False

    def test_poll_false_when_no_node_tree(self):
        from melvil.ops.add_node_group import MELVIL_OT_add_node_group
        ctx = _make_context()
        ctx.space_data.node_tree = None
        assert MELVIL_OT_add_node_group.poll(ctx) is False

    def test_poll_false_when_no_space_data(self):
        from melvil.ops.add_node_group import MELVIL_OT_add_node_group
        ctx = _make_context()
        ctx.space_data = None
        assert MELVIL_OT_add_node_group.poll(ctx) is False


# ---------------------------------------------------------------------------
# invoke()
# ---------------------------------------------------------------------------


class TestInvoke:
    def _make_op(self, asset_id: str = "aaaaaaaa-0000-4000-8000-000000000001"):
        from melvil.ops.add_node_group import MELVIL_OT_add_node_group
        op = MELVIL_OT_add_node_group()
        op.asset_id = asset_id
        return op

    def _make_ng(self, name: str = "Noise FX", ng_type: str = "SHADER"):
        ng = MagicMock()
        ng.name = name
        ng.type = ng_type
        return ng

    def test_returns_running_modal_on_success(self):
        import bpy
        ng = self._make_ng()
        ctx = _make_context()
        op = self._make_op()

        with patch("melvil.ops.add_node_group.resolve_library_root", return_value="/lib"), \
             patch("melvil.ops.add_node_group.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ops.add_node_group.open_db") as mock_db, \
             patch("melvil.ops.add_node_group.AssetReader") as MockReader:
            mock_db.return_value.__enter__ = lambda s: MagicMock()
            mock_db.return_value.__exit__ = MagicMock(return_value=False)
            MockReader.return_value.read.return_value = ng
            bpy.ops.node.translate_attach.return_value = {"FINISHED"}

            result = op.invoke(ctx, _make_event())

        assert result == {"RUNNING_MODAL"}

    def test_creates_group_node_with_correct_type_for_shader_tree(self):
        import bpy
        ng = self._make_ng(ng_type="SHADER")
        ctx = _make_context(tree_type="SHADER")
        op = self._make_op()

        with patch("melvil.ops.add_node_group.resolve_library_root", return_value="/lib"), \
             patch("melvil.ops.add_node_group.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ops.add_node_group.open_db") as mock_db, \
             patch("melvil.ops.add_node_group.AssetReader") as MockReader:
            mock_db.return_value.__enter__ = lambda s: MagicMock()
            mock_db.return_value.__exit__ = MagicMock(return_value=False)
            MockReader.return_value.read.return_value = ng
            bpy.ops.node.translate_attach.return_value = {"FINISHED"}

            op.invoke(ctx, _make_event())

        ctx.space_data.node_tree.nodes.new.assert_called_once_with(type="ShaderNodeGroup")

    def test_creates_group_node_with_correct_type_for_geometry_tree(self):
        import bpy
        ng = self._make_ng(ng_type="GEOMETRY")
        ctx = _make_context(tree_type="GEOMETRY")
        op = self._make_op()

        with patch("melvil.ops.add_node_group.resolve_library_root", return_value="/lib"), \
             patch("melvil.ops.add_node_group.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ops.add_node_group.open_db") as mock_db, \
             patch("melvil.ops.add_node_group.AssetReader") as MockReader:
            mock_db.return_value.__enter__ = lambda s: MagicMock()
            mock_db.return_value.__exit__ = MagicMock(return_value=False)
            MockReader.return_value.read.return_value = ng
            bpy.ops.node.translate_attach.return_value = {"FINISHED"}

            op.invoke(ctx, _make_event())

        ctx.space_data.node_tree.nodes.new.assert_called_once_with(type="GeometryNodeGroup")

    def test_assigns_node_tree_to_group_node(self):
        import bpy
        ng = self._make_ng()
        ctx = _make_context()
        group_node = MagicMock()
        ctx.space_data.node_tree.nodes.new.return_value = group_node
        op = self._make_op()

        with patch("melvil.ops.add_node_group.resolve_library_root", return_value="/lib"), \
             patch("melvil.ops.add_node_group.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ops.add_node_group.open_db") as mock_db, \
             patch("melvil.ops.add_node_group.AssetReader") as MockReader:
            mock_db.return_value.__enter__ = lambda s: MagicMock()
            mock_db.return_value.__exit__ = MagicMock(return_value=False)
            MockReader.return_value.read.return_value = ng
            bpy.ops.node.translate_attach.return_value = {"FINISHED"}

            op.invoke(ctx, _make_event())

        assert group_node.node_tree is ng

    def test_positions_node_at_mouse_in_node_space(self):
        """location = region_to_view(abs_mouse - region_origin) / ui_scale."""
        import bpy
        ng = self._make_ng()
        ctx = _make_context()
        canvas = ctx.area.regions[0]
        # region_to_view returns (512, 256); ui_scale=1.0 → final location=(512, 256).
        canvas.view2d.region_to_view.return_value = (512.0, 256.0)
        canvas.x = 50
        canvas.y = 80
        ctx.preferences.system.ui_scale = 1.0

        group_node = MagicMock()
        ctx.space_data.node_tree.nodes.new.return_value = group_node
        op = self._make_op()

        with patch("melvil.ops.add_node_group.resolve_library_root", return_value="/lib"), \
             patch("melvil.ops.add_node_group.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ops.add_node_group.open_db") as mock_db, \
             patch("melvil.ops.add_node_group.AssetReader") as MockReader:
            mock_db.return_value.__enter__ = lambda s: MagicMock()
            mock_db.return_value.__exit__ = MagicMock(return_value=False)
            MockReader.return_value.read.return_value = ng
            bpy.ops.node.translate_attach.return_value = {"FINISHED"}

            op.invoke(ctx, _make_event(mx=400, my=300))

        # region_to_view must receive region-local coords: abs_mouse - region_origin.
        canvas.view2d.region_to_view.assert_called_once_with(350, 220)  # 400-50, 300-80
        # location = raw_view_coords / ui_scale = (512/1.0, 256/1.0)
        assert group_node.location == (512.0, 256.0)

    def test_ui_scale_applied_to_location(self):
        """On HiDPI (ui_scale=2.0) the location is halved relative to region_to_view output."""
        import bpy
        ng = self._make_ng()
        ctx = _make_context()
        canvas = ctx.area.regions[0]
        canvas.view2d.region_to_view.return_value = (400.0, 200.0)
        ctx.preferences.system.ui_scale = 2.0  # HiDPI

        group_node = MagicMock()
        ctx.space_data.node_tree.nodes.new.return_value = group_node
        op = self._make_op()

        with patch("melvil.ops.add_node_group.resolve_library_root", return_value="/lib"), \
             patch("melvil.ops.add_node_group.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ops.add_node_group.open_db") as mock_db, \
             patch("melvil.ops.add_node_group.AssetReader") as MockReader:
            mock_db.return_value.__enter__ = lambda s: MagicMock()
            mock_db.return_value.__exit__ = MagicMock(return_value=False)
            MockReader.return_value.read.return_value = ng
            bpy.ops.node.translate_attach.return_value = {"FINISHED"}

            op.invoke(ctx, _make_event())

        # 400/2.0 = 200.0, 200/2.0 = 100.0
        assert group_node.location == (200.0, 100.0)

    def test_deselects_all_existing_nodes(self):
        import bpy
        ng = self._make_ng()
        existing_a = MagicMock()
        existing_b = MagicMock()
        ctx = _make_context(nodes=[existing_a, existing_b])
        op = self._make_op()

        with patch("melvil.ops.add_node_group.resolve_library_root", return_value="/lib"), \
             patch("melvil.ops.add_node_group.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ops.add_node_group.open_db") as mock_db, \
             patch("melvil.ops.add_node_group.AssetReader") as MockReader:
            mock_db.return_value.__enter__ = lambda s: MagicMock()
            mock_db.return_value.__exit__ = MagicMock(return_value=False)
            MockReader.return_value.read.return_value = ng
            bpy.ops.node.translate_attach.return_value = {"FINISHED"}

            op.invoke(ctx, _make_event())

        assert existing_a.select is False
        assert existing_b.select is False

    def test_calls_translate_attach_invoke_default(self):
        import bpy
        ng = self._make_ng()
        ctx = _make_context()
        op = self._make_op()

        with patch("melvil.ops.add_node_group.resolve_library_root", return_value="/lib"), \
             patch("melvil.ops.add_node_group.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ops.add_node_group.open_db") as mock_db, \
             patch("melvil.ops.add_node_group.AssetReader") as MockReader:
            mock_db.return_value.__enter__ = lambda s: MagicMock()
            mock_db.return_value.__exit__ = MagicMock(return_value=False)
            MockReader.return_value.read.return_value = ng
            bpy.ops.node.translate_attach.reset_mock()
            bpy.ops.node.translate_attach.return_value = {"FINISHED"}

            op.invoke(ctx, _make_event())

        bpy.ops.node.translate_attach.assert_called_once_with("INVOKE_DEFAULT")

    def test_returns_cancelled_when_library_not_configured(self):
        from melvil.core.library import LibraryNotConfiguredError
        op = self._make_op()
        ctx = _make_context()

        with patch("melvil.ops.add_node_group.resolve_library_root",
                   side_effect=LibraryNotConfiguredError("not set")):
            result = op.invoke(ctx, _make_event())

        assert result == {"CANCELLED"}

    def test_returns_cancelled_when_asset_not_found(self):
        from melvil.core.asset_reader import AssetNotFoundError
        op = self._make_op()
        ctx = _make_context()

        with patch("melvil.ops.add_node_group.resolve_library_root", return_value="/lib"), \
             patch("melvil.ops.add_node_group.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ops.add_node_group.open_db") as mock_db, \
             patch("melvil.ops.add_node_group.AssetReader") as MockReader:
            mock_db.return_value.__enter__ = lambda s: MagicMock()
            mock_db.return_value.__exit__ = MagicMock(return_value=False)
            MockReader.return_value.read.side_effect = AssetNotFoundError("gone")

            result = op.invoke(ctx, _make_event())

        assert result == {"CANCELLED"}

    def test_returns_cancelled_for_unsupported_tree_type(self):
        import bpy
        ng = self._make_ng(ng_type="SHADER")
        ctx = _make_context(tree_type="TEXTURE")  # not in _TREE_TYPE_TO_GROUP_NODE
        op = self._make_op()

        with patch("melvil.ops.add_node_group.resolve_library_root", return_value="/lib"), \
             patch("melvil.ops.add_node_group.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ops.add_node_group.open_db") as mock_db, \
             patch("melvil.ops.add_node_group.AssetReader") as MockReader:
            mock_db.return_value.__enter__ = lambda s: MagicMock()
            mock_db.return_value.__exit__ = MagicMock(return_value=False)
            MockReader.return_value.read.return_value = ng

            result = op.invoke(ctx, _make_event())

        assert result == {"CANCELLED"}

    def test_returns_cancelled_for_incompatible_ng_type(self):
        """A geometry node group cannot be added to a shader tree."""
        import bpy
        ng = self._make_ng(ng_type="GEOMETRY")
        ctx = _make_context(tree_type="SHADER")
        op = self._make_op()

        with patch("melvil.ops.add_node_group.resolve_library_root", return_value="/lib"), \
             patch("melvil.ops.add_node_group.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ops.add_node_group.open_db") as mock_db, \
             patch("melvil.ops.add_node_group.AssetReader") as MockReader:
            mock_db.return_value.__enter__ = lambda s: MagicMock()
            mock_db.return_value.__exit__ = MagicMock(return_value=False)
            MockReader.return_value.read.return_value = ng

            result = op.invoke(ctx, _make_event())

        assert result == {"CANCELLED"}

    def test_returns_cancelled_when_ng_is_none(self):
        import bpy
        ctx = _make_context()
        op = self._make_op()

        with patch("melvil.ops.add_node_group.resolve_library_root", return_value="/lib"), \
             patch("melvil.ops.add_node_group.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ops.add_node_group.open_db") as mock_db, \
             patch("melvil.ops.add_node_group.AssetReader") as MockReader:
            mock_db.return_value.__enter__ = lambda s: MagicMock()
            mock_db.return_value.__exit__ = MagicMock(return_value=False)
            MockReader.return_value.read.return_value = None

            result = op.invoke(ctx, _make_event())

        assert result == {"CANCELLED"}
