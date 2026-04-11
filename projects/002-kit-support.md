# Feature Spec: Kits

**Status:** Draft  
**Author:** —  
**Created:** 2025  
**Addon:** Blender Asset Library

---

## Overview

Kits are named groups that allow users to organize assets by context — for example, keeping meshes and materials for a video game project separate from those for an ad campaign. Every asset belongs to exactly one kit. A default kit named **General** is created automatically when the library is first initialized, ensuring the addon works out of the box without requiring any setup.

---

## Motivation

As a user's asset library grows, a flat list of all assets becomes unwieldy. Without a grouping mechanism, users are forced to rely entirely on tags and search to locate assets, which requires discipline and forethought at save time. Kits provide a lightweight first-class organizational layer that maps naturally to how creative professionals already think about their work — in terms of the project or context an asset was made for.

The concept is intentionally lightweight. Kits are not workspaces, not Blender projects, and not folder hierarchies. They are simple named buckets that sit above the asset level and below the library level.

---

## Goals

- Allow users to create and rename kits from within the addon UI.
- Allow users to assign any asset to a kit at save time, with the option to reassign later.
- Allow users to filter the asset browser by kit, so only assets belonging to the selected kit are shown.
- Provide a sensible default so new users are never confronted with an empty or unconfigured state.
- Keep the kit concept simple enough that it does not add meaningful friction to the core save/load workflow.
- Allow users to set a kit within a given blender project so all load/save operations occur on that kit by default

## Non-goals

- Kits are not folders on disk. They are a metadata concept stored in the database only; the managed `.blend` file storage structure is not affected.
- Kits do not have permissions, visibility settings, or sharing semantics. Those concerns belong to the future cloud/team tier.
- Assets cannot belong to more than one kit. If cross-kit organization is needed, tags are the appropriate tool.
- There is no kit hierarchy (no nested kits or sub-kits).

---

## Schema Changes

A `kits` table is added to the SQLite database. The `assets` table receives a `kit_id` foreign key.

```sql
CREATE TABLE kits (
    id          TEXT PRIMARY KEY,   -- UUID
    name        TEXT NOT NULL,
    description TEXT,
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    workspace_id TEXT,              -- nullable, reserved for cloud tier
    owner_id     TEXT               -- nullable, reserved for cloud tier
);

-- Insert default "General" kit here

ALTER TABLE assets
    ADD COLUMN kit_id TEXT REFERENCES kits(id) DEFAULT(default_kit_id) NOT NULL;
```

### Default kit

On first run (or when no kits exist), the addon creates a default kit:

```sql
INSERT INTO kits (id, name)
VALUES ('<generated-uuid>', 'General');
```

The default kit is treated as a regular kit in all respects. It has no special flag in the schema; it is simply the kit that is pre-selected in the UI on first run. Users may rename it.

### Existing assets on migration

When this feature is introduced to an existing library, a schema migration runs that creates the `General` default and assigns all existing assets to it. This ensures no asset is left with a null `kit_id` after migration.

---

## Data Model

```
Library
└── Kit (1 or more)
    └── Asset (0 or more)
```

A kit has a name, an optional description, and timestamps. A name must be non-empty and unique within the library. Names are not case-sensitive for uniqueness purposes (`general` and `General` are considered the same name).

---

## New Operators

### `ASSET_OT_kit_create`

Creates a new kit. Presents a dialog prompting for a name. Rejects empty names and duplicates with an inline error message. On success, the new kit becomes the active kit in the browser.

| Property | Type | Notes |
|---|---|---|
| `name` | `StringProperty` | Required, max 64 chars |
| `description` | `StringProperty` | Optional, max 256 chars |

### `ASSET_OT_kit_rename`

Renames the specified kit. Validates against empty names and duplicates. Operates on the kit identified by `kit_id`.

| Property | Type | Notes |
|---|---|---|
| `kit_id` | `StringProperty` | UUID of the target kit |
| `name` | `StringProperty` | New name, required |

### `ASSET_OT_asset_set_kit`

Reassigns an existing asset to a different kit.

| Property | Type | Notes |
|---|---|---|
| `asset_id` | `StringProperty` | UUID of the asset |
| `kit_id` | `StringProperty` | UUID of the destination kit |

### Changes to `ASSET_OT_save`

The save operator gains a `kit_id` property. When invoked, the kit selector is pre-populated with the currently active kit in the browser (if any), or `General` otherwise. The user may change the selection before confirming.

---

## UI Changes

### Browser panel

#### Kit selector

A list selector (similar to asset types) is added to the left side of the asset browser panel, below the asset types selector. It lists all kits by name. Selecting a kit filters the asset list to show only assets belonging to that kit. An "All Kits" option is available at the top of the list to show the unfiltered library. This is combined with the asset type selector, so if the user selects just meshes, then it will only display meshes from the selected kit for instance.

#### Kit management menu

A small menu button (e.g. a gear icon) adjacent to the kit selector exposes kit management actions:

- New Kit — invokes `ASSET_OT_kit_create`
- Rename Kit — invokes `ASSET_OT_kit_rename` on the selected kit

#### Asset detail / right-click menu

The right-click context menu on an asset in the browser gains a "Move to Kit" submenu listing all available kits. Selecting one invokes `ASSET_OT_asset_set_kit`.

### N-panel

The N-panel gains an "Active Kit" dropdown populated with the names of the available kits. The first option should be "All kits", which is the default value. This setting affects which items are populated in the shift+a add item submenu. For instance if it's set to "General", then only assets in the general kit will appear in the melvil submenu when the user adds a new object, material, node group, etc. If it is set to "All kits" then these menus will be populated with items from all of the user's kits.

### Menus

#### Save dialog

The save dialog (invoked by `ASSET_OT_save`) gains a "Kit" field showing a dropdown of all kits, pre-populated with the active kit.

---

## Behavior Details

**Renaming.** Renaming a kit updates `kits.name` and `kits.updated_at`. All assets belonging to the kit are unaffected; they reference the kit by UUID, not by name.

**Name uniqueness.** Kit names must be unique within the library (case-insensitive). If the user attempts to create or rename a kit to a name that already exists, the operator reports an error and does not proceed.

**"All Kits" filter.** When the active kit (from the N-panel) is set to "All Kits", the kit field in the save dialog still defaults to the most recently used kit, or the default kit if none has been used.

---

## Migration Plan

This feature introduces a breaking schema change (new table, new column on `assets`). The migration is handled by the existing schema versioning system and runs automatically on addon load if the current schema version predates this feature.

Migration steps:
1. Increment the schema version.
2. Create the `kits` table.
3. Insert the `General` default kit.
4. Add the `kit_id` column to `assets`, allowing it to be nullable.
5. Set `kit_id` on all existing assets to the default kit UUID.
6. Make the `kit_id` column non-nullable.

The migration runs inside a transaction. If any step fails, the transaction is rolled back and the addon reports the error to the user without modifying the database.
