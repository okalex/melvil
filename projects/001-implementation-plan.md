## Implementation Plan
**Milestone 1 is deliberately narrow.** Materials and meshes cover 80% of real-world usage, and you get a genuinely useful, shippable tool at the end of it. Node groups and actions being deferred to M3 keeps the first sprint focused.

**The DB layer comes before the UI.** Getting the schema and migration strategy right early prevents painful refactors later. The schema versioning task in M1 Phase 2 is especially worth doing carefully — it's easy to skip and very costly to retrofit.

**Texture handling is called out explicitly in M1.** It's the most footgun-prone part of the whole system and easy to defer into a broken half-implementation. Doing it properly in the first milestone means you're not chasing broken material loads in M2.

**M4 Phase 4 is the cloud bridge.** Adding the nullable `workspace_id`/`owner_id` columns and a no-op sync provider means when you're ready to build the paid tier, you're filling in an existing interface rather than cracking open the schema and every callsite that touches it.

### Milestone 1 - Proof-of-concept

#### Phase 1 - Project scaffolding
- Set up the addon directory structure:`__init__.py`,`ops/`,`ui/`,`db/`,`core/`
- Define`bl_info`and register/unregister hooks
- Add addon preferences panel (library root path, DB path)
- Write a simple smoke-test: register addon, open preferences, confirm no errors

#### Phase 2 · Database layer
- Design initial SQLite schema:`assets`(uuid, name, type, blend_path, created_at, updated_at),`tags`,`asset_tags`
- Write a thin`db.py`module: connect, migrate, CRUD helpers (no ORM)
- Implement schema versioning so future migrations don't break existing libraries
- Write unit tests for DB helpers (runnable outside Blender via`bpy`stubs)

#### Phase 3 · Asset storage core
- Implement`AssetWriter`: uses`bpy.data.libraries.write()`to serialize a datablock to a managed`.blend`file under the library root
- Implement`AssetReader`: loads (append mode) a datablock from a managed`.blend`file by UUID
- Implement texture handling: detect externally referenced images, copy them into a`textures/`subfolder, repoint paths before writing
- Register the asset in the DB after a successful write

#### Phase 4 · Operators
- Write`ASSET_OT_save`: context-aware operator that detects whether selection is a material or mesh and dispatches to the right writer path
- Write`ASSET_OT_load`: takes a UUID, calls`AssetReader`, appends to the current scene
- Write`ASSET_OT_delete`: removes the DB record and the managed`.blend`file

#### Phase 5 · Basic UI
- Create a sidebar panel (N-panel) in the 3D viewport with a scrollable asset list filtered by type
- Add "Save as asset" button that calls`ASSET_OT_save`on the active object/material
- Add "Load" button per list item that calls`ASSET_OT_load`
- Register a hotkey (e.g.`Ctrl+Shift+A`) to focus the panel / invoke a popup

### Milestone 2 - Browsing & organization

#### Phase 1 · Tagging & categorization
- Add tag input to the save dialog (comma-separated, auto-complete against existing tags)
- Add category field:`Material`,`Mesh`,`Node Group`,`Action`(auto-detected, user-overridable)
- Add description field to save dialog and asset DB record
- Add tag/category edit operator for already-saved assets

#### Phase 2 · Search & filtering
- Add a search bar to the panel (queries`assets.name`and joined tags)
- Add type-filter tabs or buttons (All / Materials / Meshes / Node Groups / Actions)
- Add tag-filter pills that narrow results when clicked
- Persist last-used filter state in addon preferences

#### Phase 3 · Thumbnails
- Generate previews at save time using`bpy.ops.wm.previews_ensure()`and store the image as a PNG alongside each managed`.blend`
- Display thumbnails in the browser panel using`UILayout.template_icon()`with a loaded`ImagePreview`
- Add "Regenerate thumbnail" operator for existing assets

#### Phase 4 · Full browser panel
- Design and implement a dedicated popup / floating panel (invoked by hotkey) with a grid thumbnail view
- Add drag-to-viewport support for mesh assets using`ASSET_OT_load`triggered from the panel
- Add context-aware filtering: opening the browser from the shader editor pre-filters to materials; from object mode, pre-filters to meshes

### Milestone 3 - Expanded asset type support

#### Phase 1 · Node groups
- Extend`AssetWriter`and`AssetReader`to handle`bpy.data.node_groups`
- Add node group detection to`ASSET_OT_save`context logic
- Handle nested node groups (groups that reference other groups) — write all dependencies

#### Phase 2 · Actions / animations
- Extend writer/reader for`bpy.data.actions`
- Store armature bone name mapping as metadata so actions can warn on mismatch when loading onto a different rig
- Add action-specific thumbnail generation (first keyframe pose render)

#### Phase 3 · Collections
- Extend writer/reader for`bpy.data.collections`(group of objects as a single asset)
- Handle all child object datablocks (meshes, materials, modifiers) as bundled dependencies
- Add instancing option on load: append as collection instance vs. fully linked objects

#### Phase 4 · Robustness & version tracking
- Store the Blender version at save time in the DB; surface a warning on load if versions differ significantly
- Add an "asset health check" operator that scans all DB records, verifies managed`.blend`files and textures exist, and reports broken assets
- Implement atomic writes for the managed`.blend`files (write to a temp path, rename on success) to prevent corruption

### Milestone 4 - Polish & distribution

#### Phase 1 · UX refinement
- Add undo support to`ASSET_OT_load`using Blender's undo stack (`bpy.ops.ed.undo_push`)
- Add inline rename for assets directly in the browser panel
- Add "recently used" section at the top of the browser
- Implement append-vs-link toggle on the load operator

#### Phase 2 · Library management
- Add import operator: scan a folder or existing`.blend`file and bulk-import datablocks as assets
- Add export operator: package selected assets as a self-contained`.zip`(managed blends + textures + a manifest JSON)
- Add library stats view in preferences (asset counts by type, total disk usage)

#### Phase 3 · Packaging & distribution
- Write a build script that produces a installable`.zip`from the addon source
- Verify compatibility across Blender 4.x LTS versions
- Write a`CHANGELOG.md`and README with install instructions and usage overview
- Set up a CI step (GitHub Actions) that runs the unit tests and builds the release zip on tag push

#### Phase 4 · Architecture prep for cloud
- Add`workspace_id`and`owner_id`columns to the assets schema (nullable, unused in local tier)
- Stub out a`sync/`module with a no-op local provider so the interface exists before the implementation
- Document the sync protocol design (what gets synced, conflict strategy, content-addressed blob storage) for future implementation
