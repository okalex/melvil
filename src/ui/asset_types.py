"""
Canonical asset-type metadata.

Centralises the label, icon, and behavioural flags that were previously
scattered across ``draw_helpers``, ``gpu_browser``, and the legacy
``grid_list`` module.  Any new asset type only needs to be registered here.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AssetTypeInfo:
    label: str
    icon: str
    show_load: bool = True


ASSET_TYPES: dict[str, AssetTypeInfo] = {
    "MATERIAL": AssetTypeInfo(label="Material", icon="MATERIAL", show_load=True),
    "MESH": AssetTypeInfo(label="Mesh", icon="MESH_DATA", show_load=True),
    "NODE_GROUP": AssetTypeInfo(label="Node Group", icon="NODETREE", show_load=False),
}


def type_label(asset_type: str) -> str:
    """Return the human-readable label for *asset_type*, falling back to the raw string."""
    info = ASSET_TYPES.get(asset_type)
    return info.label if info else asset_type


def type_icon(asset_type: str) -> str:
    """Return the Blender icon name for *asset_type*, falling back to ``"OBJECT_DATA"``."""
    info = ASSET_TYPES.get(asset_type)
    return info.icon if info else "OBJECT_DATA"


def show_load(asset_type: str) -> bool:
    """Return whether a "Load" button should appear for *asset_type*."""
    info = ASSET_TYPES.get(asset_type)
    return info.show_load if info else True
