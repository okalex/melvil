"""
Melvil submenu for the Add menu (Shift-A / Object ▸ Add).

``MELVIL_MT_add_submenu`` appears as a "Melvil ▶" entry in
``VIEW3D_MT_add``.  Its ``draw()`` method queries the database at draw-time
and renders one ``melvil.load_asset`` operator button per saved mesh asset.

Blender indexes operator *display text* for menu search, so assets are
individually searchable by name inside the Add menu search box without any
extra work.
"""

from .menus_factory import create_asset_submenu

MELVIL_MT_add_submenu, _draw_add_entry, register, unregister = create_asset_submenu(
    bl_idname="MELVIL_MT_add_submenu",
    asset_type="MESH",
    operator_id="melvil.load_asset",
    icon="MESH_DATA",
    empty_label="No mesh assets saved yet",
    host_menu="VIEW3D_MT_add",
)
