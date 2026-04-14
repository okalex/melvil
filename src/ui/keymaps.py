"""
Keymap registration for Melvil.

Registers ``Ctrl+Shift+A`` in the 3D View to invoke
``melvil.open_browser``, which opens the Melvil asset browser.

The ``_keymaps`` list holds ``(KeyMap, KeyMapItem)`` pairs so that
``unregister()`` can cleanly remove only the items we added, without
disturbing other addons' keymaps.

Architecture note
-----------------
Additional hotkeys should be added here rather than inline at the operator
level, keeping all keymap state in one place.
"""

from __future__ import annotations

import bpy

_keymaps: list[tuple] = []


def register() -> None:
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc is None:
        # Running in background/headless mode — skip keymap registration.
        return

    km = kc.keymaps.new(name="3D View", space_type="VIEW_3D")
    kmi = km.keymap_items.new(
        "melvil.open_browser",
        type="A",
        value="PRESS",
        ctrl=True,
        shift=True,
    )
    _keymaps.append((km, kmi))


def unregister() -> None:
    for km, kmi in _keymaps:
        km.keymap_items.remove(kmi)
    _keymaps.clear()
