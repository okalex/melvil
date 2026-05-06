"""
Default items registered into ``BLAMMO_MT_context_submenu``.

Each public ``_draw_*`` function is registered/unregistered by this module's
``register()`` / ``unregister()`` hooks, which are called from
``ui/registry.py``.  Adding a new submenu item anywhere in the addon means:

1. Write a ``_draw_<name>(self, context)`` function.
2. Call ``menus.register_item`` / ``menus.unregister_item`` in this module
   (or in any other module that owns the feature).
"""

from __future__ import annotations

from . import menus


def _draw_save_asset(self, context):
    """'Save as Asset' entry in the Blammo submenu."""
    self.layout.operator("blammo.save_asset", icon="EXPORT")


def register() -> None:
    menus.register_item(_draw_save_asset)


def unregister() -> None:
    menus.unregister_item(_draw_save_asset)
