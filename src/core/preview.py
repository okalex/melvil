"""
Preview generation for Melvil assets.

Renders a 512×512 Workbench PNG preview image for mesh and material assets.
All ``bpy`` and ``mathutils`` imports are deferred inside function bodies so
this module is importable outside of Blender (e.g. during tests).

Public API
----------
``generate_mesh_preview(context, obj, asset_id, previews_dir)``
    Render the active mesh object using the current viewport camera
    orientation (falls back to a fixed isometric angle if no viewport is
    available).

``generate_material_preview(context, mat, asset_id, previews_dir)``
    Render a UV sphere with the given material applied.

Both functions write a PNG to ``previews_dir / f"{asset_id}.png"`` and return
the absolute path on success, or ``None`` on any failure.  The caller's scene
is never modified.

Implementation notes
--------------------
Each public function creates a disposable ``bpy.data.scenes`` entry, does all
rendering inside it, and removes it unconditionally in a ``finally`` block.
Internal helpers (``_bounding_sphere``, ``_position_camera_zoom_to_fit``,
``_set_isometric_camera``, ``_do_render``, ``_add_uv_sphere``) are module-level
functions so they can be monkeypatched in unit tests without touching bpy.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Optional

_PREVIEW_SIZE = 512
_PADDING_FACTOR = 1.05  # 5 % margin around the bounding sphere


# ---------------------------------------------------------------------------
# Internal helpers — isolated for monkeypatching in tests
# ---------------------------------------------------------------------------


def _configure_scene(scene, output_path: Path) -> None:
    """Apply shared Workbench render settings to *scene*."""
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.film_transparent = True
    scene.render.resolution_x = _PREVIEW_SIZE
    scene.render.resolution_y = _PREVIEW_SIZE
    scene.render.resolution_percentage = 100
    scene.render.filepath = str(output_path)
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.display.shading.type = "MATERIAL"
    scene.display.shading.use_scene_lights = True
    scene.display.shading.use_scene_world = False


def _bounding_sphere(obj) -> tuple:
    """
    Return ``(center, radius)`` of *obj*'s bounding sphere in world space.

    Uses ``obj.bound_box`` (8 corners in local space) transformed by
    ``obj.matrix_world``.  The radius is clamped to at least ``0.001`` to
    avoid divide-by-zero on empty or degenerate meshes.
    """
    import mathutils  # noqa: PLC0415

    corners = [obj.matrix_world @ mathutils.Vector(c) for c in obj.bound_box]
    center = sum(corners, mathutils.Vector((0.0, 0.0, 0.0))) / 8
    radius = max((c - center).length for c in corners)
    return center, max(radius, 0.001)


def _position_camera_zoom_to_fit(camera_obj, center, radius: float) -> None:
    """
    Translate *camera_obj* backwards along its viewing axis so that a sphere
    of *radius* centred at *center* fully fills the frame, with a 5 % margin.

    Assumes *camera_obj.matrix_world* already encodes the desired orientation.
    """
    import mathutils  # noqa: PLC0415

    half_fov = camera_obj.data.angle / 2.0
    distance = (radius / math.tan(half_fov)) * _PADDING_FACTOR

    # Cameras look down their local –Z axis.
    cam_forward = camera_obj.matrix_world.to_3x3() @ mathutils.Vector((0.0, 0.0, -1.0))
    cam_forward.normalize()
    camera_obj.location = center - cam_forward * distance


def _set_isometric_camera(camera_obj, center, radius: float) -> None:
    """
    Orient *camera_obj* to a front-top-right isometric angle and zoom to fit
    a sphere of *radius* centred at *center*.

    Used as a fallback when the save operator is invoked outside a 3D viewport
    (e.g. from the Properties panel) and no ``region_3d`` view matrix is
    available.
    """
    import mathutils  # noqa: PLC0415

    euler = mathutils.Euler((math.radians(60), 0.0, math.radians(45)), "XYZ")
    camera_obj.rotation_euler = euler
    camera_obj.matrix_world = mathutils.Matrix.LocRotScale(
        mathutils.Vector((0.0, 0.0, 0.0)),
        euler.to_quaternion(),
        mathutils.Vector((1.0, 1.0, 1.0)),
    )
    _position_camera_zoom_to_fit(camera_obj, center, radius)


def _do_render(scene) -> None:
    """
    Invoke ``bpy.ops.render.render`` for *scene*.

    Isolated as a module-level function so tests can monkeypatch it without
    importing ``bpy``.
    """
    import bpy  # noqa: PLC0415

    bpy.ops.render.render(write_still=True, scene=scene.name)


def _add_uv_sphere(scene):
    """
    Add a UV sphere (radius 1, 64 segments, 32 rings) to *scene* and return
    the created object.

    Uses ``bpy.context.temp_override`` so the operator runs in *scene* rather
    than the user's active scene.  Isolated for monkeypatching in tests.
    """
    import bpy  # noqa: PLC0415

    with bpy.context.temp_override(scene=scene):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=1.0, segments=64, ring_count=32)
        return bpy.context.active_object


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_mesh_preview(
    context,
    obj,
    asset_id: str,
    previews_dir: Path,
) -> Optional[str]:
    """
    Render a 512×512 Workbench preview of *obj* using the current viewport
    orientation.  Falls back to a fixed front-top-right isometric camera when
    no 3D viewport is available (e.g. called from the Properties editor).

    Parameters
    ----------
    context:
        Blender operator context (``bpy.context``).
    obj:
        The ``bpy.types.Object`` (type ``"MESH"``) to render.
    asset_id:
        UUID of the asset; used as the output filename stem.
    previews_dir:
        Directory in which to write the PNG.  Created if it does not exist.

    Returns
    -------
    str
        Absolute path to the written PNG.
    None
        If preview generation fails for any reason.  The asset is always saved
        regardless; this function never raises.
    """
    import bpy  # noqa: PLC0415

    output_path = previews_dir / f"{asset_id}.png"

    # Resolve viewport transform — may be None when called outside a viewport.
    space_data = getattr(context, "space_data", None)
    region_3d = getattr(space_data, "region_3d", None)
    view_matrix = getattr(region_3d, "view_matrix", None)

    scene = None
    cam_data = None
    cam_obj = None
    try:
        scene = bpy.data.scenes.new("melvil_preview_temp")
        _configure_scene(scene, output_path)

        cam_data = bpy.data.cameras.new("melvil_preview_cam")
        cam_data.type = "PERSP"
        cam_data.lens = 50

        cam_obj = bpy.data.objects.new("melvil_preview_cam", cam_data)

        center, radius = _bounding_sphere(obj)

        if view_matrix is not None:
            cam_obj.matrix_world = view_matrix.inverted()
            _position_camera_zoom_to_fit(cam_obj, center, radius)
        else:
            _set_isometric_camera(cam_obj, center, radius)

        scene.collection.objects.link(obj)
        scene.collection.objects.link(cam_obj)
        scene.camera = cam_obj

        previews_dir.mkdir(parents=True, exist_ok=True)
        _do_render(scene)

        return str(output_path)

    except Exception:  # noqa: BLE001
        return None

    finally:
        if cam_obj is not None:
            bpy.data.objects.remove(cam_obj, do_unlink=True)
        if cam_data is not None:
            bpy.data.cameras.remove(cam_data)
        if scene is not None:
            bpy.data.scenes.remove(scene)


def generate_material_preview(
    context,
    mat,
    asset_id: str,
    previews_dir: Path,
) -> Optional[str]:
    """
    Render a 512×512 Workbench preview of *mat* applied to a UV sphere.

    The camera is placed at a fixed 45°/30° angle so all material previews
    have a consistent framing regardless of save context.

    Parameters
    ----------
    context:
        Blender operator context (unused but accepted for API symmetry with
        ``generate_mesh_preview``).
    mat:
        The ``bpy.types.Material`` to preview.
    asset_id:
        UUID of the asset; used as the output filename stem.
    previews_dir:
        Directory in which to write the PNG.  Created if it does not exist.

    Returns
    -------
    str
        Absolute path to the written PNG.
    None
        If preview generation fails for any reason.
    """
    import bpy  # noqa: PLC0415

    output_path = previews_dir / f"{asset_id}.png"

    scene = None
    cam_data = None
    cam_obj = None
    sphere_obj = None
    try:
        scene = bpy.data.scenes.new("melvil_preview_temp")
        _configure_scene(scene, output_path)

        # --- UV sphere with material applied ---
        sphere_obj = _add_uv_sphere(scene)
        sphere_obj.data.materials.append(mat)

        # --- Camera at a fixed classic 45°/30° preview angle ---
        cam_data = bpy.data.cameras.new("melvil_preview_cam")
        cam_data.type = "PERSP"
        cam_data.lens = 50

        cam_obj = bpy.data.objects.new("melvil_preview_cam", cam_data)
        cam_obj.location = (2.6, -2.6, 1.5)
        cam_obj.rotation_euler = (
            math.radians(75),
            0.0,
            math.radians(45),
        )

        scene.collection.objects.link(cam_obj)
        scene.camera = cam_obj

        previews_dir.mkdir(parents=True, exist_ok=True)
        _do_render(scene)

        return str(output_path)

    except Exception:  # noqa: BLE001
        return None

    finally:
        if sphere_obj is not None:
            sphere_mesh = getattr(sphere_obj, "data", None)
            bpy.data.objects.remove(sphere_obj, do_unlink=True)
            if sphere_mesh is not None:
                bpy.data.meshes.remove(sphere_mesh)
        if cam_obj is not None:
            bpy.data.objects.remove(cam_obj, do_unlink=True)
        if cam_data is not None:
            bpy.data.cameras.remove(cam_data)
        if scene is not None:
            bpy.data.scenes.remove(scene)
