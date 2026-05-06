"""
Blammo submenu for the Node Editor Add menu (Shift-A in any node editor).

``BLAMMO_MT_node_add_submenu`` appears as a "Blammo! ▶" entry in
``NODE_MT_add``.  Its ``draw()`` method queries the database at draw-time
and renders one ``blammo.add_node_group`` operator button per saved
``NODE_GROUP`` asset.

Blender indexes operator *display text* for menu search, so assets are
individually searchable by name inside the Shift-A search box without any
extra work.
"""

from .menus_factory import create_asset_submenu

BLAMMO_MT_node_add_submenu, _draw_node_add_entry, register, unregister = create_asset_submenu(
    bl_idname="BLAMMO_MT_node_add_submenu",
    asset_type="NODE_GROUP",
    operator_id="blammo.add_node_group",
    icon="NODETREE",
    empty_label="No node group assets saved yet",
    host_menu="NODE_MT_add",
)
