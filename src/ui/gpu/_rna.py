"""RNA introspection helpers for the GPU UI toolkit.

Centralizes ``_PropertyDeferred`` annotation inspection so that
``layout.py`` and ``dropdown.py`` share a single implementation for
resolving dynamic enum items from Blender RNA.
"""

from __future__ import annotations

import sys
from typing import Any

from ._logger import _logger


def _normalize_enum_items(
    raw: Any,
) -> list[tuple[str, str, str, str]]:
    """Normalize raw enum items to 4-tuples ``(id, name, desc, icon)``."""
    result: list[tuple[str, str, str, str]] = []
    for entry in raw:
        if len(entry) >= 4:
            result.append((entry[0], entry[1], entry[2], entry[3]))
        else:
            result.append((entry[0], entry[1], "", "NONE"))
    return result


def resolve_prop_enum_items(
    data: object, property_name: str,
) -> list[tuple[str, str, str, str]]:
    """Resolve items for a dynamic-callback EnumProperty on *data*.

    Blender's ``_PropertyDeferred`` stores the keyword arguments passed to
    ``EnumProperty()``.  If ``items`` is a callable we invoke it with
    ``(data, context)`` to retrieve the current item list.
    """
    try:
        import bpy

        ann = getattr(type(data), "__annotations__", {}).get(property_name)
        if ann is None:
            return []
        kw = getattr(ann, "keywords", None)
        if kw is None:
            return []
        items_src = kw.get("items")
        if items_src is None:
            return []
        if callable(items_src):
            raw = items_src(data, bpy.context)
        else:
            raw = items_src
        return _normalize_enum_items(raw)
    except Exception as exc:
        _logger.log(f"resolve_prop_enum_items({property_name!r}): {exc}")
        return []


def resolve_operator_enum_items(
    operator_id: str, property_name: str,
) -> list[tuple[str, str, str, str]]:
    """Resolve enum items for an operator's property at runtime.

    Dynamic enum callbacks require an operator instance.  This method
    looks up the callback from the operator class's ``__annotations__``
    (for modules without ``from __future__ import annotations``) or
    from the module-level function referenced in the
    ``_PropertyDeferred``.
    """
    import bpy

    items: list[tuple[str, str, str, str]] = []
    try:
        parts = operator_id.split(".", 1)
        if len(parts) != 2:
            return items
        cls_name = f"{parts[0].upper()}_OT_{parts[1]}"
        op_cls = getattr(bpy.types, cls_name, None)
        if op_cls is None:
            return items

        ann = getattr(op_cls, "__annotations__", {}).get(property_name)
        kw = getattr(ann, "keywords", None) if ann else None
        items_src = kw.get("items") if kw else None

        if items_src is None:
            mod_name = getattr(op_cls, "__module__", None)
            mod = sys.modules.get(mod_name) if mod_name else None
            if mod is not None:
                for stem in (property_name, property_name.removesuffix("_id")):
                    fn_name = f"_get_{stem}_items"
                    items_src = getattr(mod, fn_name, None)
                    if callable(items_src):
                        break

        if callable(items_src):
            raw = items_src(None, bpy.context)
            return _normalize_enum_items(raw)
    except Exception:  # noqa: BLE001
        pass
    return items
