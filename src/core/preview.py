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
import traceback
from pathlib import Path
from typing import Optional

_PREVIEW_SIZE = 512
_PADDING_FACTOR = 1.05  # 5 % margin around the bounding sphere


# ---------------------------------------------------------------------------
# Internal helpers — isolated for monkeypatching in tests
# ---------------------------------------------------------------------------


def _configure_scene(
    scene,
    output_path: Path,
    engine: str = "BLENDER_WORKBENCH",
) -> None:
    """Apply shared render settings to *scene*.

    *engine* should be ``"BLENDER_WORKBENCH"`` (mesh previews) or
    ``"BLENDER_EEVEE_NEXT"`` (material previews).  The Workbench-specific
    display shading block is skipped for Eevee, which uses the material's
    own shader instead.
    """
    scene.render.engine = engine
    scene.render.film_transparent = True
    scene.render.resolution_x = _PREVIEW_SIZE
    scene.render.resolution_y = _PREVIEW_SIZE
    scene.render.resolution_percentage = 100
    scene.render.filepath = str(output_path)
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    if engine == "BLENDER_WORKBENCH":
        scene.display.shading.type = "SOLID"
        scene.display.shading.light = "MATCAP"
        scene.display.shading.color_type = "MATERIAL"


def _bounding_sphere(obj) -> tuple:
    """
    Return ``(center, radius)`` of *obj*'s bounding sphere in world space.

    Computes bounds directly from the object's mesh vertex positions
    (transformed by ``obj.matrix_world``) rather than the cached
    ``bound_box`` property, which can be stale for freshly-created mesh
    objects that have not yet been evaluated by Blender's dependency graph.

    The radius is clamped to at least ``0.001`` to avoid divide-by-zero on
    empty or degenerate meshes.
    """
    import mathutils  # noqa: PLC0415

    vertices = obj.data.vertices
    if not vertices:
        return mathutils.Vector((0.0, 0.0, 0.0)), 0.001

    mat = obj.matrix_world
    world_verts = [mat @ v.co for v in vertices]
    xs = [v.x for v in world_verts]
    ys = [v.y for v in world_verts]
    zs = [v.z for v in world_verts]
    center = mathutils.Vector((
        (max(xs) + min(xs)) / 2,
        (max(ys) + min(ys)) / 2,
        (max(zs) + min(zs)) / 2,
    ))
    radius = max((v - center).length for v in world_verts)
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
    available, and also for all material previews.

    Computes the camera position analytically from the Euler rotation rather
    than reading back ``matrix_world`` after assignment.  Reading
    ``matrix_world`` immediately after writing it is unreliable for objects
    that have not yet been evaluated by Blender's dependency graph (unlinked
    objects), which caused the camera to be placed at the wrong distance,
    producing a tiny preview.
    """
    import mathutils  # noqa: PLC0415

    euler = mathutils.Euler((math.radians(60), 0.0, math.radians(45)), "XYZ")
    # Camera looks down its local -Z axis; transform (0, 0, -1) into world
    # space using the rotation matrix derived directly from the Euler angles.
    cam_forward = euler.to_matrix() @ mathutils.Vector((0.0, 0.0, -1.0))

    half_fov = camera_obj.data.angle / 2.0
    distance = (radius / math.tan(half_fov)) * _PADDING_FACTOR

    # Set location and rotation_euler directly — no matrix_world round-trip.
    camera_obj.location = center - cam_forward * distance
    camera_obj.rotation_euler = euler


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
    Create a UV sphere (radius 1, 64 longitudinal segments, 32 latitudinal
    rings) and link it to *scene*'s root collection.  Returns the created
    object.

    Uses ``bmesh.ops.create_uvsphere`` rather than a context-dependent
    operator so the sphere is reliably placed in *scene* regardless of the
    user's active context.  Isolated for monkeypatching in tests.
    """
    import bmesh as _bmesh  # noqa: PLC0415
    import bpy  # noqa: PLC0415

    mesh = bpy.data.meshes.new("melvil_sphere_mesh")
    bm = _bmesh.new()
    _bmesh.ops.create_uvsphere(bm, u_segments=64, v_segments=32, radius=1.0)
    bm.to_mesh(mesh)
    bm.free()

    # Enable smooth shading on every polygon.
    for poly in mesh.polygons:
        poly.use_smooth = True

    sphere_obj = bpy.data.objects.new("melvil_sphere", mesh)
    scene.collection.objects.link(sphere_obj)
    return sphere_obj


def _add_builtin_cube(scene):
    """
    Create a unit cube (side length 2) and link it to *scene*.
    Returns the created object.  Isolated for monkeypatching in tests.
    """
    import bmesh as _bmesh  # noqa: PLC0415
    import bpy  # noqa: PLC0415

    mesh = bpy.data.meshes.new("melvil_cube_mesh")
    bm = _bmesh.new()
    _bmesh.ops.create_cube(bm, size=2.0)
    bm.to_mesh(mesh)
    bm.free()

    for poly in mesh.polygons:
        poly.use_smooth = True

    cube_obj = bpy.data.objects.new("melvil_cube", mesh)
    scene.collection.objects.link(cube_obj)
    return cube_obj


def _add_builtin_torus(scene):
    """
    Create a torus (major radius 1.0, minor radius 0.3, 48 × 12 segments)
    and link it to *scene*.  Returns the created object.
    Isolated for monkeypatching in tests.
    """
    import bpy  # noqa: PLC0415

    major_r, minor_r = 1.0, 0.3
    major_seg, minor_seg = 48, 12

    mesh = bpy.data.meshes.new("melvil_torus_mesh")

    import bmesh as _bmesh  # noqa: PLC0415
    bm = _bmesh.new()

    for i in range(major_seg):
        theta = 2.0 * math.pi * i / major_seg
        cos_t, sin_t = math.cos(theta), math.sin(theta)
        for j in range(minor_seg):
            phi = 2.0 * math.pi * j / minor_seg
            r = major_r + minor_r * math.cos(phi)
            bm.verts.new((r * cos_t, r * sin_t, minor_r * math.sin(phi)))

    bm.verts.ensure_lookup_table()
    for i in range(major_seg):
        for j in range(minor_seg):
            v00 = bm.verts[i * minor_seg + j]
            v01 = bm.verts[i * minor_seg + (j + 1) % minor_seg]
            v10 = bm.verts[((i + 1) % major_seg) * minor_seg + j]
            v11 = bm.verts[((i + 1) % major_seg) * minor_seg + (j + 1) % minor_seg]
            bm.faces.new((v00, v10, v11, v01))

    bm.to_mesh(mesh)
    bm.free()

    for poly in mesh.polygons:
        poly.use_smooth = True

    torus_obj = bpy.data.objects.new("melvil_torus", mesh)
    scene.collection.objects.link(torus_obj)
    return torus_obj


def _add_builtin_monkey(scene):
    """
    Create a Suzanne monkey head and link it to *scene*.
    Returns the created object.  Isolated for monkeypatching in tests.
    """
    import bmesh as _bmesh  # noqa: PLC0415
    import bpy  # noqa: PLC0415

    mesh = bpy.data.meshes.new("melvil_monkey_mesh")
    bm = _bmesh.new()
    _bmesh.ops.create_monkey(bm)
    bm.to_mesh(mesh)
    bm.free()

    for poly in mesh.polygons:
        poly.use_smooth = True

    monkey_obj = bpy.data.objects.new("melvil_monkey", mesh)
    scene.collection.objects.link(monkey_obj)
    return monkey_obj


def _add_user_mesh_asset(scene, blend_path: str, obj_name: str):
    """
    Append a saved MESH asset from *blend_path* and link it into *scene*.
    Returns the appended object, or ``None`` if it could not be loaded.

    The appended object is a fresh copy owned by *bpy.data*; the caller is
    responsible for removing it (and its mesh datablock) in the ``finally``
    block.  Isolated for monkeypatching in tests.
    """
    import bpy  # noqa: PLC0415

    with bpy.data.libraries.load(blend_path, link=False) as (data_from, data_to):
        if obj_name in data_from.objects:
            data_to.objects = [obj_name]

    if not data_to.objects or data_to.objects[0] is None:
        return None

    obj = data_to.objects[0]
    # Reset the world transform so the object is placed at the origin,
    # matching the behaviour of all built-in primitive helpers.  The
    # original position from the user's scene is irrelevant for a
    # material preview and would otherwise cause the bounding-sphere
    # calculation and camera placement to disagree with where Blender
    # actually renders the object after depsgraph evaluation.
    obj.location = (0.0, 0.0, 0.0)
    obj.rotation_euler = (0.0, 0.0, 0.0)
    obj.scale = (1.0, 1.0, 1.0)
    scene.collection.objects.link(obj)
    return obj


def _add_preview_mesh(scene, preview_mesh_id: str, blend_path=None, obj_name=None):
    """
    Create the preview mesh in *scene* based on *preview_mesh_id*.

    Built-in primitives are generated via bmesh (no side effects on the
    user's scene).  For user assets, *blend_path* and *obj_name* must be
    provided; the object is appended from the .blend file.

    Returns the created object, or ``None`` when a user asset cannot be
    loaded.  Isolated so individual primitive helpers can still be
    monkeypatched in tests.
    """
    if preview_mesh_id == "BUILTIN_CUBE":
        return _add_builtin_cube(scene)
    if preview_mesh_id == "BUILTIN_TORUS":
        return _add_builtin_torus(scene)
    if preview_mesh_id == "BUILTIN_MONKEY":
        return _add_builtin_monkey(scene)
    if preview_mesh_id == "BUILTIN_UV_SPHERE":
        return _add_uv_sphere(scene)
    # User asset — load from .blend.
    if blend_path is not None and obj_name is not None:
        return _add_user_mesh_asset(scene, blend_path, obj_name)
    return None


def _make_material_preview_lighting(scene):
    """
    Add a key sun light and a dim ambient world to *scene* for Eevee material
    previews.

    The sun is oriented so its rays come from the upper-right of the camera's
    view (camera is positioned at (2.6, -2.6, 1.5) looking at the origin).
    Returns *(light_obj, light_data, world)*; callers are responsible for
    cleaning up all three datablocks in a ``finally`` block.

    Isolated for monkeypatching in tests.
    """
    import bpy  # noqa: PLC0415
    import mathutils  # noqa: PLC0415

    light_data = bpy.data.lights.new("melvil_preview_key", type="SUN")
    light_data.energy = 3.0
    light_obj = bpy.data.objects.new("melvil_preview_key", light_data)
    # Upper-right of the camera's view with a slight forward (-Y) lean so
    # the light grazes the front-facing side without being head-on.
    # X > 0 = right, Z > 0 = up, Y < 0 = toward camera.
    light_dir = mathutils.Vector((2.0, -0.3, 2.0))
    light_obj.rotation_euler = light_dir.to_track_quat("Z", "Y").to_euler()
    scene.collection.objects.link(light_obj)

    # Dim ambient fill so shadowed areas are not pure black.
    world = bpy.data.worlds.new("melvil_preview_world")
    world.use_nodes = False
    world.color = (0.05, 0.05, 0.05)
    scene.world = world

    return light_obj, light_data, world


def _aim_at_origin(cam_obj, location) -> None:
    """
    Rotate *cam_obj* so its local -Z axis (camera look direction) points at
    the world origin from *location*.

    *location* is accepted as a 3-tuple rather than reading ``cam_obj.location``
    directly so the value is always well-typed and the function is easy to test.

    Isolated for monkeypatching in tests.
    """
    import mathutils  # noqa: PLC0415

    direction = mathutils.Vector((0.0, 0.0, 0.0)) - mathutils.Vector(location)
    cam_obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


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
        cam_data.clip_start = max(radius * 1e-3, 1e-6)

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
        print("Melvil: mesh preview generation failed:")
        traceback.print_exc()
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
    *,
    preview_mesh_id: str = "BUILTIN_UV_SPHERE",
    preview_mesh_blend_path: Optional[str] = None,
    preview_mesh_obj_name: Optional[str] = None,
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
    light_obj = None
    light_data = None
    world = None
    try:
        scene = bpy.data.scenes.new("melvil_preview_temp")
        _configure_scene(scene, output_path, engine="BLENDER_EEVEE")

        # --- Preview mesh with material applied ---
        sphere_obj = _add_preview_mesh(
            scene, preview_mesh_id, preview_mesh_blend_path, preview_mesh_obj_name
        )
        sphere_obj.data.materials.append(mat)

        # --- Key light + ambient world ---
        light_obj, light_data, world = _make_material_preview_lighting(scene)

        # --- Camera zoomed to fit the preview mesh at the canonical 45°/30° angle ---
        cam_data = bpy.data.cameras.new("melvil_preview_cam")
        cam_data.type = "PERSP"
        cam_data.lens = 50

        cam_obj = bpy.data.objects.new("melvil_preview_cam", cam_data)

        center, radius = _bounding_sphere(sphere_obj)
        cam_data.clip_start = max(radius * 1e-3, 1e-6)
        _set_isometric_camera(cam_obj, center, radius)

        scene.collection.objects.link(cam_obj)
        scene.camera = cam_obj

        previews_dir.mkdir(parents=True, exist_ok=True)
        _do_render(scene)

        return str(output_path)

    except Exception:  # noqa: BLE001
        print("Melvil: material preview generation failed:")
        traceback.print_exc()
        return None

    finally:
        if light_obj is not None:
            bpy.data.objects.remove(light_obj, do_unlink=True)
        if light_data is not None:
            bpy.data.lights.remove(light_data)
        if world is not None:
            bpy.data.worlds.remove(world)
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
