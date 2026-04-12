"""Tests for core/preview.py — preview image generation."""

from __future__ import annotations

import math
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_context(has_viewport: bool = True) -> MagicMock:
    """Return a minimal context mock.

    When *has_viewport* is True, ``context.space_data.region_3d.view_matrix``
    is a MagicMock so ``view_matrix is not None`` evaluates True.
    When False, ``space_data`` is None so the viewport path is skipped.
    """
    ctx = MagicMock()
    if not has_viewport:
        ctx.space_data = None
    return ctx


def _make_obj() -> MagicMock:
    return MagicMock()


def _make_mat() -> MagicMock:
    return MagicMock()


# ---------------------------------------------------------------------------
# _configure_scene
# ---------------------------------------------------------------------------


class TestConfigureScene:
    def _call(self, tmp_path):
        from melvil.core.preview import _configure_scene

        scene = MagicMock()
        _configure_scene(scene, tmp_path / "out.png")
        return scene

    def test_sets_workbench_engine(self, tmp_path):
        scene = self._call(tmp_path)
        assert scene.render.engine == "BLENDER_WORKBENCH"

    def test_sets_transparent_background(self, tmp_path):
        scene = self._call(tmp_path)
        assert scene.render.film_transparent is True

    def test_sets_512x512_resolution(self, tmp_path):
        scene = self._call(tmp_path)
        assert scene.render.resolution_x == 512
        assert scene.render.resolution_y == 512

    def test_sets_resolution_percentage(self, tmp_path):
        scene = self._call(tmp_path)
        assert scene.render.resolution_percentage == 100

    def test_filepath_matches_output_path(self, tmp_path):
        output = tmp_path / "out.png"
        scene = MagicMock()
        from melvil.core.preview import _configure_scene

        _configure_scene(scene, output)
        assert scene.render.filepath == str(output)

    def test_sets_png_rgba(self, tmp_path):
        scene = self._call(tmp_path)
        assert scene.render.image_settings.file_format == "PNG"
        assert scene.render.image_settings.color_mode == "RGBA"

    def test_sets_material_shading(self, tmp_path):
        scene = self._call(tmp_path)
        assert scene.display.shading.type == "MATERIAL"
        assert scene.display.shading.use_scene_lights is True
        assert scene.display.shading.use_scene_world is False


# ---------------------------------------------------------------------------
# generate_mesh_preview — success paths
# ---------------------------------------------------------------------------


ASSET_ID = "aaaaaaaa-0000-4000-8000-000000000001"
_MOCK_CENTER = MagicMock()


def _mesh_patches(extra_patches=None):
    """Return the stack of patches common to all mesh preview tests."""
    return [
        patch("melvil.core.preview._bounding_sphere", return_value=(_MOCK_CENTER, 1.5)),
        patch("melvil.core.preview._position_camera_zoom_to_fit"),
        patch("melvil.core.preview._set_isometric_camera"),
        patch("melvil.core.preview._do_render"),
    ]


class TestGenerateMeshPreviewSuccess:
    def test_returns_absolute_path_to_png(self, tmp_path):
        from melvil.core.preview import generate_mesh_preview

        previews_dir = tmp_path / "previews"
        ctx = _make_context()
        obj = _make_obj()

        with patch("melvil.core.preview._bounding_sphere", return_value=(_MOCK_CENTER, 1.5)), \
             patch("melvil.core.preview._position_camera_zoom_to_fit"), \
             patch("melvil.core.preview._do_render"):

            result = generate_mesh_preview(ctx, obj, ASSET_ID, previews_dir)

        assert result == str(previews_dir / f"{ASSET_ID}.png")

    def test_creates_previews_dir(self, tmp_path):
        from melvil.core.preview import generate_mesh_preview

        previews_dir = tmp_path / "previews"
        assert not previews_dir.exists()

        with patch("melvil.core.preview._bounding_sphere", return_value=(_MOCK_CENTER, 1.5)), \
             patch("melvil.core.preview._position_camera_zoom_to_fit"), \
             patch("melvil.core.preview._do_render"):

            generate_mesh_preview(_make_context(), _make_obj(), ASSET_ID, previews_dir)

        assert previews_dir.exists()

    def test_uses_viewport_view_matrix(self, tmp_path):
        """When a viewport is available, the camera matrix comes from view_matrix.inverted()."""
        import bpy
        from melvil.core.preview import generate_mesh_preview

        previews_dir = tmp_path / "previews"
        ctx = _make_context(has_viewport=True)
        cam_obj = MagicMock()
        bpy.data.objects.new.return_value = cam_obj

        with patch("melvil.core.preview._bounding_sphere", return_value=(_MOCK_CENTER, 1.5)), \
             patch("melvil.core.preview._position_camera_zoom_to_fit") as mock_zoom, \
             patch("melvil.core.preview._set_isometric_camera") as mock_iso, \
             patch("melvil.core.preview._do_render"):

            generate_mesh_preview(ctx, _make_obj(), ASSET_ID, previews_dir)

        # viewport path: matrix set from view_matrix and zoom called, isometric skipped
        expected_matrix = ctx.space_data.region_3d.view_matrix.inverted()
        assert cam_obj.matrix_world == expected_matrix
        mock_zoom.assert_called_once_with(cam_obj, _MOCK_CENTER, 1.5)
        mock_iso.assert_not_called()

    def test_falls_back_to_isometric_when_no_viewport(self, tmp_path):
        """When space_data is None, _set_isometric_camera is called instead."""
        import bpy
        from melvil.core.preview import generate_mesh_preview

        previews_dir = tmp_path / "previews"
        ctx = _make_context(has_viewport=False)
        cam_obj = MagicMock()
        bpy.data.objects.new.return_value = cam_obj

        with patch("melvil.core.preview._bounding_sphere", return_value=(_MOCK_CENTER, 1.5)), \
             patch("melvil.core.preview._position_camera_zoom_to_fit") as mock_zoom, \
             patch("melvil.core.preview._set_isometric_camera") as mock_iso, \
             patch("melvil.core.preview._do_render"):

            generate_mesh_preview(ctx, _make_obj(), ASSET_ID, previews_dir)

        mock_iso.assert_called_once_with(cam_obj, _MOCK_CENTER, 1.5)
        mock_zoom.assert_not_called()

    def test_calls_bounding_sphere_on_obj(self, tmp_path):
        from melvil.core.preview import generate_mesh_preview

        previews_dir = tmp_path / "previews"
        obj = _make_obj()

        with patch("melvil.core.preview._bounding_sphere", return_value=(_MOCK_CENTER, 1.5)) as mock_bs, \
             patch("melvil.core.preview._position_camera_zoom_to_fit"), \
             patch("melvil.core.preview._do_render"):

            generate_mesh_preview(_make_context(), obj, ASSET_ID, previews_dir)

        mock_bs.assert_called_once_with(obj)

    def test_links_obj_to_temp_scene(self, tmp_path):
        import bpy
        from melvil.core.preview import generate_mesh_preview

        previews_dir = tmp_path / "previews"
        obj = _make_obj()
        scene = MagicMock()
        bpy.data.scenes.new.return_value = scene

        with patch("melvil.core.preview._bounding_sphere", return_value=(_MOCK_CENTER, 1.5)), \
             patch("melvil.core.preview._position_camera_zoom_to_fit"), \
             patch("melvil.core.preview._do_render"):

            generate_mesh_preview(_make_context(), obj, ASSET_ID, previews_dir)

        scene.collection.objects.link.assert_any_call(obj)

    def test_sets_scene_camera(self, tmp_path):
        import bpy
        from melvil.core.preview import generate_mesh_preview

        previews_dir = tmp_path / "previews"
        scene = MagicMock()
        cam_obj = MagicMock()
        bpy.data.scenes.new.return_value = scene
        bpy.data.objects.new.return_value = cam_obj

        with patch("melvil.core.preview._bounding_sphere", return_value=(_MOCK_CENTER, 1.5)), \
             patch("melvil.core.preview._position_camera_zoom_to_fit"), \
             patch("melvil.core.preview._do_render"):

            generate_mesh_preview(_make_context(), _make_obj(), ASSET_ID, previews_dir)

        assert scene.camera == cam_obj

    def test_calls_do_render_with_scene(self, tmp_path):
        import bpy
        from melvil.core.preview import generate_mesh_preview

        previews_dir = tmp_path / "previews"
        scene = MagicMock()
        bpy.data.scenes.new.return_value = scene

        with patch("melvil.core.preview._bounding_sphere", return_value=(_MOCK_CENTER, 1.5)), \
             patch("melvil.core.preview._position_camera_zoom_to_fit"), \
             patch("melvil.core.preview._do_render") as mock_render:

            generate_mesh_preview(_make_context(), _make_obj(), ASSET_ID, previews_dir)

        mock_render.assert_called_once_with(scene)

    def test_configures_scene(self, tmp_path):
        import bpy
        from melvil.core.preview import generate_mesh_preview

        previews_dir = tmp_path / "previews"
        scene = MagicMock()
        bpy.data.scenes.new.return_value = scene

        with patch("melvil.core.preview._bounding_sphere", return_value=(_MOCK_CENTER, 1.5)), \
             patch("melvil.core.preview._position_camera_zoom_to_fit"), \
             patch("melvil.core.preview._do_render"):

            generate_mesh_preview(_make_context(), _make_obj(), ASSET_ID, previews_dir)

        assert scene.render.engine == "BLENDER_WORKBENCH"
        assert scene.render.resolution_x == 512


# ---------------------------------------------------------------------------
# generate_mesh_preview — failure & cleanup paths
# ---------------------------------------------------------------------------


class TestGenerateMeshPreviewCleanup:
    def test_returns_none_on_render_failure(self, tmp_path):
        from melvil.core.preview import generate_mesh_preview

        previews_dir = tmp_path / "previews"

        with patch("melvil.core.preview._bounding_sphere", return_value=(_MOCK_CENTER, 1.5)), \
             patch("melvil.core.preview._position_camera_zoom_to_fit"), \
             patch("melvil.core.preview._do_render", side_effect=RuntimeError("GPU unavailable")):

            result = generate_mesh_preview(_make_context(), _make_obj(), ASSET_ID, previews_dir)

        assert result is None

    def test_scene_removed_on_success(self, tmp_path):
        import bpy
        from melvil.core.preview import generate_mesh_preview

        previews_dir = tmp_path / "previews"
        scene = MagicMock()
        bpy.data.scenes.new.return_value = scene

        with patch("melvil.core.preview._bounding_sphere", return_value=(_MOCK_CENTER, 1.5)), \
             patch("melvil.core.preview._position_camera_zoom_to_fit"), \
             patch("melvil.core.preview._do_render"):

            generate_mesh_preview(_make_context(), _make_obj(), ASSET_ID, previews_dir)

        bpy.data.scenes.remove.assert_called_with(scene)

    def test_scene_removed_on_failure(self, tmp_path):
        import bpy
        from melvil.core.preview import generate_mesh_preview

        previews_dir = tmp_path / "previews"
        scene = MagicMock()
        bpy.data.scenes.new.return_value = scene

        with patch("melvil.core.preview._bounding_sphere", return_value=(_MOCK_CENTER, 1.5)), \
             patch("melvil.core.preview._position_camera_zoom_to_fit"), \
             patch("melvil.core.preview._do_render", side_effect=RuntimeError("failed")):

            generate_mesh_preview(_make_context(), _make_obj(), ASSET_ID, previews_dir)

        bpy.data.scenes.remove.assert_called_with(scene)

    def test_camera_removed_on_failure(self, tmp_path):
        import bpy
        from melvil.core.preview import generate_mesh_preview

        previews_dir = tmp_path / "previews"
        cam_obj = MagicMock()
        bpy.data.objects.new.return_value = cam_obj

        with patch("melvil.core.preview._bounding_sphere", return_value=(_MOCK_CENTER, 1.5)), \
             patch("melvil.core.preview._position_camera_zoom_to_fit"), \
             patch("melvil.core.preview._do_render", side_effect=RuntimeError("failed")):

            generate_mesh_preview(_make_context(), _make_obj(), ASSET_ID, previews_dir)

        bpy.data.objects.remove.assert_any_call(cam_obj, do_unlink=True)

    def test_returns_none_on_unexpected_exception_during_setup(self, tmp_path):
        from melvil.core.preview import generate_mesh_preview

        previews_dir = tmp_path / "previews"

        with patch("melvil.core.preview._bounding_sphere", side_effect=ValueError("boom")), \
             patch("melvil.core.preview._do_render"):

            result = generate_mesh_preview(_make_context(), _make_obj(), ASSET_ID, previews_dir)

        assert result is None


# ---------------------------------------------------------------------------
# generate_material_preview — success paths
# ---------------------------------------------------------------------------


class TestGenerateMaterialPreviewSuccess:
    def test_returns_absolute_path_to_png(self, tmp_path):
        from melvil.core.preview import generate_material_preview

        previews_dir = tmp_path / "previews"

        with patch("melvil.core.preview._add_uv_sphere", return_value=MagicMock()), \
             patch("melvil.core.preview._do_render"):

            result = generate_material_preview(MagicMock(), _make_mat(), ASSET_ID, previews_dir)

        assert result == str(previews_dir / f"{ASSET_ID}.png")

    def test_creates_previews_dir(self, tmp_path):
        from melvil.core.preview import generate_material_preview

        previews_dir = tmp_path / "previews"
        assert not previews_dir.exists()

        with patch("melvil.core.preview._add_uv_sphere", return_value=MagicMock()), \
             patch("melvil.core.preview._do_render"):

            generate_material_preview(MagicMock(), _make_mat(), ASSET_ID, previews_dir)

        assert previews_dir.exists()

    def test_adds_uv_sphere_to_temp_scene(self, tmp_path):
        import bpy
        from melvil.core.preview import generate_material_preview

        previews_dir = tmp_path / "previews"
        scene = MagicMock()
        bpy.data.scenes.new.return_value = scene

        with patch("melvil.core.preview._add_uv_sphere", return_value=MagicMock()) as mock_sphere, \
             patch("melvil.core.preview._do_render"):

            generate_material_preview(MagicMock(), _make_mat(), ASSET_ID, previews_dir)

        mock_sphere.assert_called_once_with(scene)

    def test_applies_material_to_sphere(self, tmp_path):
        from melvil.core.preview import generate_material_preview

        previews_dir = tmp_path / "previews"
        mat = _make_mat()
        sphere_obj = MagicMock()

        with patch("melvil.core.preview._add_uv_sphere", return_value=sphere_obj), \
             patch("melvil.core.preview._do_render"):

            generate_material_preview(MagicMock(), mat, ASSET_ID, previews_dir)

        sphere_obj.data.materials.append.assert_called_once_with(mat)

    def test_camera_at_fixed_location(self, tmp_path):
        import bpy
        from melvil.core.preview import generate_material_preview

        previews_dir = tmp_path / "previews"
        cam_obj = MagicMock()
        bpy.data.objects.new.return_value = cam_obj

        with patch("melvil.core.preview._add_uv_sphere", return_value=MagicMock()), \
             patch("melvil.core.preview._do_render"):

            generate_material_preview(MagicMock(), _make_mat(), ASSET_ID, previews_dir)

        assert cam_obj.location == (2.6, -2.6, 1.5)

    def test_camera_at_fixed_rotation(self, tmp_path):
        import bpy
        from melvil.core.preview import generate_material_preview

        previews_dir = tmp_path / "previews"
        cam_obj = MagicMock()
        bpy.data.objects.new.return_value = cam_obj

        with patch("melvil.core.preview._add_uv_sphere", return_value=MagicMock()), \
             patch("melvil.core.preview._do_render"):

            generate_material_preview(MagicMock(), _make_mat(), ASSET_ID, previews_dir)

        expected = (math.radians(75), 0.0, math.radians(45))
        assert cam_obj.rotation_euler == expected

    def test_sets_scene_camera(self, tmp_path):
        import bpy
        from melvil.core.preview import generate_material_preview

        previews_dir = tmp_path / "previews"
        scene = MagicMock()
        cam_obj = MagicMock()
        bpy.data.scenes.new.return_value = scene
        bpy.data.objects.new.return_value = cam_obj

        with patch("melvil.core.preview._add_uv_sphere", return_value=MagicMock()), \
             patch("melvil.core.preview._do_render"):

            generate_material_preview(MagicMock(), _make_mat(), ASSET_ID, previews_dir)

        assert scene.camera == cam_obj

    def test_calls_do_render_with_scene(self, tmp_path):
        import bpy
        from melvil.core.preview import generate_material_preview

        previews_dir = tmp_path / "previews"
        scene = MagicMock()
        bpy.data.scenes.new.return_value = scene

        with patch("melvil.core.preview._add_uv_sphere", return_value=MagicMock()), \
             patch("melvil.core.preview._do_render") as mock_render:

            generate_material_preview(MagicMock(), _make_mat(), ASSET_ID, previews_dir)

        mock_render.assert_called_once_with(scene)

    def test_configures_scene(self, tmp_path):
        import bpy
        from melvil.core.preview import generate_material_preview

        previews_dir = tmp_path / "previews"
        scene = MagicMock()
        bpy.data.scenes.new.return_value = scene

        with patch("melvil.core.preview._add_uv_sphere", return_value=MagicMock()), \
             patch("melvil.core.preview._do_render"):

            generate_material_preview(MagicMock(), _make_mat(), ASSET_ID, previews_dir)

        assert scene.render.engine == "BLENDER_WORKBENCH"
        assert scene.render.film_transparent is True


# ---------------------------------------------------------------------------
# generate_material_preview — failure & cleanup paths
# ---------------------------------------------------------------------------


class TestGenerateMaterialPreviewCleanup:
    def test_returns_none_on_render_failure(self, tmp_path):
        from melvil.core.preview import generate_material_preview

        previews_dir = tmp_path / "previews"

        with patch("melvil.core.preview._add_uv_sphere", return_value=MagicMock()), \
             patch("melvil.core.preview._do_render", side_effect=RuntimeError("GPU unavailable")):

            result = generate_material_preview(MagicMock(), _make_mat(), ASSET_ID, previews_dir)

        assert result is None

    def test_scene_removed_on_success(self, tmp_path):
        import bpy
        from melvil.core.preview import generate_material_preview

        previews_dir = tmp_path / "previews"
        scene = MagicMock()
        bpy.data.scenes.new.return_value = scene

        with patch("melvil.core.preview._add_uv_sphere", return_value=MagicMock()), \
             patch("melvil.core.preview._do_render"):

            generate_material_preview(MagicMock(), _make_mat(), ASSET_ID, previews_dir)

        bpy.data.scenes.remove.assert_called_with(scene)

    def test_scene_removed_on_failure(self, tmp_path):
        import bpy
        from melvil.core.preview import generate_material_preview

        previews_dir = tmp_path / "previews"
        scene = MagicMock()
        bpy.data.scenes.new.return_value = scene

        with patch("melvil.core.preview._add_uv_sphere", return_value=MagicMock()), \
             patch("melvil.core.preview._do_render", side_effect=RuntimeError("failed")):

            generate_material_preview(MagicMock(), _make_mat(), ASSET_ID, previews_dir)

        bpy.data.scenes.remove.assert_called_with(scene)

    def test_sphere_and_mesh_removed_on_failure(self, tmp_path):
        import bpy
        from melvil.core.preview import generate_material_preview

        previews_dir = tmp_path / "previews"
        sphere_obj = MagicMock()
        sphere_mesh = MagicMock()
        sphere_obj.data = sphere_mesh

        with patch("melvil.core.preview._add_uv_sphere", return_value=sphere_obj), \
             patch("melvil.core.preview._do_render", side_effect=RuntimeError("failed")):

            generate_material_preview(MagicMock(), _make_mat(), ASSET_ID, previews_dir)

        bpy.data.objects.remove.assert_any_call(sphere_obj, do_unlink=True)
        bpy.data.meshes.remove.assert_any_call(sphere_mesh)

    def test_returns_none_on_sphere_creation_failure(self, tmp_path):
        from melvil.core.preview import generate_material_preview

        previews_dir = tmp_path / "previews"

        with patch("melvil.core.preview._add_uv_sphere", side_effect=RuntimeError("ops failed")), \
             patch("melvil.core.preview._do_render"):

            result = generate_material_preview(MagicMock(), _make_mat(), ASSET_ID, previews_dir)

        assert result is None


# ---------------------------------------------------------------------------
# _do_render
# ---------------------------------------------------------------------------


class TestDoRender:
    def test_calls_bpy_ops_render_with_write_still(self):
        import bpy
        from melvil.core.preview import _do_render

        scene = MagicMock()
        scene.name = "melvil_preview_temp"

        _do_render(scene)

        bpy.ops.render.render.assert_called_with(write_still=True, scene="melvil_preview_temp")
