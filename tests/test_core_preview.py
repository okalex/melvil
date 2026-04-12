"""Tests for core/preview.py — preview image generation."""

from __future__ import annotations

import math
from pathlib import Path
from unittest.mock import ANY, MagicMock, call, patch

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
    def _call(self, tmp_path, engine="BLENDER_WORKBENCH"):
        from melvil.core.preview import _configure_scene

        scene = MagicMock()
        _configure_scene(scene, tmp_path / "out.png", engine=engine)
        return scene

    def test_workbench_engine_is_default(self, tmp_path):
        scene = self._call(tmp_path)
        assert scene.render.engine == "BLENDER_WORKBENCH"

    def test_eevee_engine_accepted(self, tmp_path):
        scene = self._call(tmp_path, engine="BLENDER_EEVEE")
        assert scene.render.engine == "BLENDER_EEVEE"

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

    def test_workbench_sets_solid_shading(self, tmp_path):
        scene = self._call(tmp_path, engine="BLENDER_WORKBENCH")
        assert scene.display.shading.type == "SOLID"
        assert scene.display.shading.light == "MATCAP"
        assert scene.display.shading.color_type == "MATERIAL"

    def test_eevee_does_not_set_workbench_shading(self, tmp_path):
        from melvil.core.preview import _configure_scene

        scene = MagicMock()
        _configure_scene(scene, tmp_path / "out.png", engine="BLENDER_EEVEE")
        scene.display.shading.type.__set__ = MagicMock()  # type: ignore[assignment]
        # display.shading should not have been written to for Eevee
        scene.display.shading.type.assert_not_called()


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
# _aim_at_origin / _make_material_preview_lighting helpers
# ---------------------------------------------------------------------------

_LIGHT_MOCKS = (MagicMock(), MagicMock(), MagicMock())
_LIGHTING_PATCH = patch(
    "melvil.core.preview._make_material_preview_lighting",
    return_value=_LIGHT_MOCKS,
)
_AIM_PATCH = patch("melvil.core.preview._aim_at_origin")


class TestAimAtOrigin:
    def test_sets_rotation_euler_on_cam_obj(self):
        import sys
        from melvil.core.preview import _aim_at_origin

        cam_obj = MagicMock()
        with patch.dict(sys.modules, {"mathutils": MagicMock()}):
            _aim_at_origin(cam_obj, (2.6, -2.6, 1.5))

        # rotation_euler is set; the exact value comes from to_track_quat.
        assert cam_obj.rotation_euler is not None

    def test_direction_to_track_quat_called(self):
        import sys
        from melvil.core.preview import _aim_at_origin

        cam_obj = MagicMock()
        mathutils_mock = MagicMock()
        with patch.dict(sys.modules, {"mathutils": mathutils_mock}):
            _aim_at_origin(cam_obj, (2.6, -2.6, 1.5))

        # Vector must have been constructed with the origin and with the location.
        calls = [c.args[0] for c in mathutils_mock.Vector.call_args_list]
        assert (0.0, 0.0, 0.0) in calls
        assert (2.6, -2.6, 1.5) in calls


class TestMakeMaterialPreviewLighting:
    def test_creates_sun_light(self, tmp_path):
        import bpy
        import sys
        from melvil.core.preview import _make_material_preview_lighting

        scene = MagicMock()
        with patch.dict(sys.modules, {"mathutils": MagicMock()}):
            _make_material_preview_lighting(scene)

        bpy.data.lights.new.assert_called_with("melvil_preview_key", type="SUN")

    def test_creates_world_ambient(self, tmp_path):
        import bpy
        import sys
        from melvil.core.preview import _make_material_preview_lighting

        scene = MagicMock()
        world = MagicMock()
        bpy.data.worlds.new.return_value = world

        with patch.dict(sys.modules, {"mathutils": MagicMock()}):
            _make_material_preview_lighting(scene)

        assert scene.world is world
        assert world.use_nodes is False

    def test_links_light_to_scene(self, tmp_path):
        import bpy
        import sys
        from melvil.core.preview import _make_material_preview_lighting

        scene = MagicMock()
        light_obj = MagicMock()
        bpy.data.objects.new.return_value = light_obj

        with patch.dict(sys.modules, {"mathutils": MagicMock()}):
            _make_material_preview_lighting(scene)

        scene.collection.objects.link.assert_called_with(light_obj)

    def test_returns_light_obj_data_world(self, tmp_path):
        import bpy
        import sys
        from melvil.core.preview import _make_material_preview_lighting

        scene = MagicMock()
        light_obj = MagicMock()
        light_data = MagicMock()
        world = MagicMock()
        bpy.data.objects.new.return_value = light_obj
        bpy.data.lights.new.return_value = light_data
        bpy.data.worlds.new.return_value = world

        with patch.dict(sys.modules, {"mathutils": MagicMock()}):
            result_light_obj, result_light_data, result_world = (
                _make_material_preview_lighting(scene)
            )

        assert result_light_obj is light_obj
        assert result_light_data is light_data
        assert result_world is world


# ---------------------------------------------------------------------------
# _add_preview_mesh & builtin helpers
# ---------------------------------------------------------------------------


class TestAddPreviewMesh:
    def test_dispatches_to_uv_sphere(self):
        from melvil.core.preview import _add_preview_mesh

        scene = MagicMock()
        expected = MagicMock()
        with patch("melvil.core.preview._add_uv_sphere", return_value=expected) as mock:
            result = _add_preview_mesh(scene, "BUILTIN_UV_SPHERE")
        mock.assert_called_once_with(scene)
        assert result is expected

    def test_dispatches_to_cube(self):
        from melvil.core.preview import _add_preview_mesh

        scene = MagicMock()
        expected = MagicMock()
        with patch("melvil.core.preview._add_builtin_cube", return_value=expected) as mock:
            result = _add_preview_mesh(scene, "BUILTIN_CUBE")
        mock.assert_called_once_with(scene)
        assert result is expected

    def test_dispatches_to_torus(self):
        from melvil.core.preview import _add_preview_mesh

        scene = MagicMock()
        expected = MagicMock()
        with patch("melvil.core.preview._add_builtin_torus", return_value=expected) as mock:
            result = _add_preview_mesh(scene, "BUILTIN_TORUS")
        mock.assert_called_once_with(scene)
        assert result is expected

    def test_dispatches_to_monkey(self):
        from melvil.core.preview import _add_preview_mesh

        scene = MagicMock()
        expected = MagicMock()
        with patch("melvil.core.preview._add_builtin_monkey", return_value=expected) as mock:
            result = _add_preview_mesh(scene, "BUILTIN_MONKEY")
        mock.assert_called_once_with(scene)
        assert result is expected

    def test_dispatches_to_user_asset_when_uuid(self):
        from melvil.core.preview import _add_preview_mesh

        scene = MagicMock()
        expected = MagicMock()
        uuid = "aaaaaaaa-0000-4000-8000-000000000001"
        with patch("melvil.core.preview._add_user_mesh_asset", return_value=expected) as mock:
            result = _add_preview_mesh(
                scene, uuid, blend_path="/lib/mesh.blend", obj_name="Cube"
            )
        mock.assert_called_once_with(scene, "/lib/mesh.blend", "Cube")
        assert result is expected

    def test_returns_none_for_user_asset_without_blend_path(self):
        from melvil.core.preview import _add_preview_mesh

        uuid = "aaaaaaaa-0000-4000-8000-000000000001"
        result = _add_preview_mesh(MagicMock(), uuid)
        assert result is None


# ---------------------------------------------------------------------------
# generate_material_preview — success paths
# ---------------------------------------------------------------------------


class TestGenerateMaterialPreviewSuccess:
    def test_returns_absolute_path_to_png(self, tmp_path):
        from melvil.core.preview import generate_material_preview

        previews_dir = tmp_path / "previews"

        with patch("melvil.core.preview._add_preview_mesh", return_value=MagicMock()), \
             _LIGHTING_PATCH, _AIM_PATCH, \
             patch("melvil.core.preview._do_render"):

            result = generate_material_preview(MagicMock(), _make_mat(), ASSET_ID, previews_dir)

        assert result == str(previews_dir / f"{ASSET_ID}.png")

    def test_creates_previews_dir(self, tmp_path):
        from melvil.core.preview import generate_material_preview

        previews_dir = tmp_path / "previews"
        assert not previews_dir.exists()

        with patch("melvil.core.preview._add_preview_mesh", return_value=MagicMock()), \
             _LIGHTING_PATCH, _AIM_PATCH, \
             patch("melvil.core.preview._do_render"):

            generate_material_preview(MagicMock(), _make_mat(), ASSET_ID, previews_dir)

        assert previews_dir.exists()

    def test_adds_uv_sphere_to_temp_scene(self, tmp_path):
        import bpy
        from melvil.core.preview import generate_material_preview

        previews_dir = tmp_path / "previews"
        scene = MagicMock()
        bpy.data.scenes.new.return_value = scene

        with patch("melvil.core.preview._add_preview_mesh", return_value=MagicMock()) as mock_sphere, \
             _LIGHTING_PATCH, _AIM_PATCH, \
             patch("melvil.core.preview._do_render"):

            generate_material_preview(MagicMock(), _make_mat(), ASSET_ID, previews_dir)

        mock_sphere.assert_called_once_with(scene, "BUILTIN_UV_SPHERE", None, None)

    def test_applies_material_to_sphere(self, tmp_path):
        from melvil.core.preview import generate_material_preview

        previews_dir = tmp_path / "previews"
        mat = _make_mat()
        sphere_obj = MagicMock()

        with patch("melvil.core.preview._add_preview_mesh", return_value=sphere_obj), \
             _LIGHTING_PATCH, _AIM_PATCH, \
             patch("melvil.core.preview._do_render"):

            generate_material_preview(MagicMock(), mat, ASSET_ID, previews_dir)

        sphere_obj.data.materials.append.assert_called_once_with(mat)

    def test_creates_lighting_for_scene(self, tmp_path):
        import bpy
        from melvil.core.preview import generate_material_preview

        previews_dir = tmp_path / "previews"
        scene = MagicMock()
        bpy.data.scenes.new.return_value = scene

        with patch("melvil.core.preview._add_preview_mesh", return_value=MagicMock()), \
             patch("melvil.core.preview._make_material_preview_lighting",
                   return_value=_LIGHT_MOCKS) as mock_lighting, \
             _AIM_PATCH, \
             patch("melvil.core.preview._do_render"):

            generate_material_preview(MagicMock(), _make_mat(), ASSET_ID, previews_dir)

        mock_lighting.assert_called_once_with(scene)

    def test_camera_at_fixed_location(self, tmp_path):
        import bpy
        from melvil.core.preview import generate_material_preview

        previews_dir = tmp_path / "previews"
        cam_obj = MagicMock()
        bpy.data.objects.new.return_value = cam_obj

        with patch("melvil.core.preview._add_preview_mesh", return_value=MagicMock()), \
             _LIGHTING_PATCH, _AIM_PATCH, \
             patch("melvil.core.preview._do_render"):

            generate_material_preview(MagicMock(), _make_mat(), ASSET_ID, previews_dir)

        assert cam_obj.location == (2.6, -2.6, 1.5)

    def test_aims_camera_at_origin(self, tmp_path):
        from melvil.core.preview import generate_material_preview

        previews_dir = tmp_path / "previews"

        with patch("melvil.core.preview._add_preview_mesh", return_value=MagicMock()), \
             _LIGHTING_PATCH, \
             patch("melvil.core.preview._aim_at_origin") as mock_aim, \
             patch("melvil.core.preview._do_render"):

            generate_material_preview(MagicMock(), _make_mat(), ASSET_ID, previews_dir)

        mock_aim.assert_called_once_with(ANY, (2.6, -2.6, 1.5))

    def test_sets_scene_camera(self, tmp_path):
        import bpy
        from melvil.core.preview import generate_material_preview

        previews_dir = tmp_path / "previews"
        scene = MagicMock()
        cam_obj = MagicMock()
        bpy.data.scenes.new.return_value = scene
        bpy.data.objects.new.return_value = cam_obj

        with patch("melvil.core.preview._add_preview_mesh", return_value=MagicMock()), \
             _LIGHTING_PATCH, _AIM_PATCH, \
             patch("melvil.core.preview._do_render"):

            generate_material_preview(MagicMock(), _make_mat(), ASSET_ID, previews_dir)

        assert scene.camera == cam_obj

    def test_calls_do_render_with_scene(self, tmp_path):
        import bpy
        from melvil.core.preview import generate_material_preview

        previews_dir = tmp_path / "previews"
        scene = MagicMock()
        bpy.data.scenes.new.return_value = scene

        with patch("melvil.core.preview._add_preview_mesh", return_value=MagicMock()), \
             _LIGHTING_PATCH, _AIM_PATCH, \
             patch("melvil.core.preview._do_render") as mock_render:

            generate_material_preview(MagicMock(), _make_mat(), ASSET_ID, previews_dir)

        mock_render.assert_called_once_with(scene)

    def test_configures_scene(self, tmp_path):
        import bpy
        from melvil.core.preview import generate_material_preview

        previews_dir = tmp_path / "previews"
        scene = MagicMock()
        bpy.data.scenes.new.return_value = scene

        with patch("melvil.core.preview._add_preview_mesh", return_value=MagicMock()), \
             _LIGHTING_PATCH, _AIM_PATCH, \
             patch("melvil.core.preview._do_render"):

            generate_material_preview(MagicMock(), _make_mat(), ASSET_ID, previews_dir)

        assert scene.render.engine == "BLENDER_EEVEE"
        assert scene.render.film_transparent is True


# ---------------------------------------------------------------------------
# generate_material_preview — failure & cleanup paths
# ---------------------------------------------------------------------------


class TestGenerateMaterialPreviewCleanup:
    def test_returns_none_on_render_failure(self, tmp_path):
        from melvil.core.preview import generate_material_preview

        previews_dir = tmp_path / "previews"

        with patch("melvil.core.preview._add_preview_mesh", return_value=MagicMock()), \
             _LIGHTING_PATCH, _AIM_PATCH, \
             patch("melvil.core.preview._do_render", side_effect=RuntimeError("GPU unavailable")):

            result = generate_material_preview(MagicMock(), _make_mat(), ASSET_ID, previews_dir)

        assert result is None

    def test_scene_removed_on_success(self, tmp_path):
        import bpy
        from melvil.core.preview import generate_material_preview

        previews_dir = tmp_path / "previews"
        scene = MagicMock()
        bpy.data.scenes.new.return_value = scene

        with patch("melvil.core.preview._add_preview_mesh", return_value=MagicMock()), \
             _LIGHTING_PATCH, _AIM_PATCH, \
             patch("melvil.core.preview._do_render"):

            generate_material_preview(MagicMock(), _make_mat(), ASSET_ID, previews_dir)

        bpy.data.scenes.remove.assert_called_with(scene)

    def test_scene_removed_on_failure(self, tmp_path):
        import bpy
        from melvil.core.preview import generate_material_preview

        previews_dir = tmp_path / "previews"
        scene = MagicMock()
        bpy.data.scenes.new.return_value = scene

        with patch("melvil.core.preview._add_preview_mesh", return_value=MagicMock()), \
             _LIGHTING_PATCH, _AIM_PATCH, \
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

        with patch("melvil.core.preview._add_preview_mesh", return_value=sphere_obj), \
             _LIGHTING_PATCH, _AIM_PATCH, \
             patch("melvil.core.preview._do_render", side_effect=RuntimeError("failed")):

            generate_material_preview(MagicMock(), _make_mat(), ASSET_ID, previews_dir)

        bpy.data.objects.remove.assert_any_call(sphere_obj, do_unlink=True)
        bpy.data.meshes.remove.assert_any_call(sphere_mesh)

    def test_light_and_world_removed_on_success(self, tmp_path):
        import bpy
        from melvil.core.preview import generate_material_preview

        previews_dir = tmp_path / "previews"
        light_obj = MagicMock()
        light_data = MagicMock()
        world = MagicMock()

        with patch("melvil.core.preview._add_preview_mesh", return_value=MagicMock()), \
             patch("melvil.core.preview._make_material_preview_lighting",
                   return_value=(light_obj, light_data, world)), \
             _AIM_PATCH, \
             patch("melvil.core.preview._do_render"):

            generate_material_preview(MagicMock(), _make_mat(), ASSET_ID, previews_dir)

        bpy.data.objects.remove.assert_any_call(light_obj, do_unlink=True)
        bpy.data.lights.remove.assert_called_with(light_data)
        bpy.data.worlds.remove.assert_called_with(world)

    def test_light_and_world_removed_on_failure(self, tmp_path):
        import bpy
        from melvil.core.preview import generate_material_preview

        previews_dir = tmp_path / "previews"
        light_obj = MagicMock()
        light_data = MagicMock()
        world = MagicMock()

        with patch("melvil.core.preview._add_preview_mesh", return_value=MagicMock()), \
             patch("melvil.core.preview._make_material_preview_lighting",
                   return_value=(light_obj, light_data, world)), \
             _AIM_PATCH, \
             patch("melvil.core.preview._do_render", side_effect=RuntimeError("failed")):

            generate_material_preview(MagicMock(), _make_mat(), ASSET_ID, previews_dir)

        bpy.data.objects.remove.assert_any_call(light_obj, do_unlink=True)
        bpy.data.lights.remove.assert_called_with(light_data)
        bpy.data.worlds.remove.assert_called_with(world)

    def test_returns_none_on_sphere_creation_failure(self, tmp_path):
        from melvil.core.preview import generate_material_preview

        previews_dir = tmp_path / "previews"

        with patch("melvil.core.preview._add_preview_mesh", side_effect=RuntimeError("ops failed")), \
             _LIGHTING_PATCH, _AIM_PATCH, \
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
