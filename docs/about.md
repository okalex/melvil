A free, open-source Blender addon for intuitive, local-first asset management

### Overview

Blender Asset Library is a Blender addon that replaces the built-in asset browser workflow with a streamlined, keyboard-driven alternative. It lets artists save any datablock — a material, mesh, node group, animation, or collection — directly from their active scene without interrupting their workflow, and retrieve it just as quickly. All assets are stored in a structured local library managed entirely by the addon; users never need to manually organize `.blend` files or configure Blender's asset library directories.

The addon is free for local use and licensed under the GNU General Public License v3. A future paid tier will add cloud sync and shared team workspaces, but the full local feature set will always remain free and open source.

### Motivation

#### The problem with Blender's built-in asset browser

Blender ships with an asset browser introduced in version 3.0. While functional, its design imposes significant friction on artists who want to build and use a personal asset library as part of a natural creative workflow. Three pain points stand out in particular:

**Tedious save flow.** Saving an asset requires opening a second editor pane, switching it to the Outliner, right-clicking a datablock to mark it as an asset, and then saving the file to a pre-configured asset library directory. If the artist is already working inside a project file, they must first copy the datablock, open or create a separate library `.blend` file, paste the datablock, mark it as an asset, and save. This multi-step process breaks focus and discourages artists from building their library incrementally.

**No quick-access hotkey.** Opening the asset browser requires precisely targeting a narrow edge strip on an existing editor pane, dragging to create a new panel, then selecting the asset browser from a dropdown menu. There is no hotkey to bring it up directly, and no way to have it appear contextually based on what the artist is currently working on.

**Unintuitive storage model.** Assets are stored as datablocks inside user-managed `.blend` files. Many artists maintain a single large library file (e.g. `materials_library.blend`) which becomes unwieldy over time and provides no metadata, search, or tagging capabilities beyond what Blender's limited asset properties allow.

#### The opportunity

Blender's Python API provides all the primitives needed to build a better experience: programmatic datablock serialization via `bpy.data.libraries`, keymap registration for global hotkeys, and flexible panel and popup APIs for custom UI. The missing piece is not capability — it is a well-designed tool that assembles those capabilities into a cohesive, low-friction workflow.

There is clear community demand for this. Forum threads, Reddit posts, and YouTube comments about Blender's asset browser consistently surface the same frustrations described above. Several paid addons address parts of the problem but none provide a fully open, local-first solution with a clean architecture designed for future extensibility.

### Project Goals

#### Primary goals

- Reduce the friction of saving an asset to a single operator call, invokable from a hotkey or right-click menu, from any context within Blender.
- Provide a keyboard-accessible browser panel that opens instantly and filters contextually — showing materials when the shader editor is active, meshes and collections when in object mode, and so on.
- Store all assets in a structured, addon-managed library so users never need to think about where files live or how they are organized.
- Support the most common asset types: materials, meshes, node groups, actions, and collections.
- Ship as a GPL v3 addon that is free to use, inspect, and modify.

#### Secondary goals

- Provide rich metadata support: tags, categories, descriptions, and creation dates, all queryable via a fast search interface.
- Generate and display asset thumbnails automatically at save time.
- Support bulk import from existing `.blend` files and export of assets as a portable archive.
- Lay the architectural groundwork for a future cloud sync and shared team workspace feature without requiring a schema or interface overhaul.

### Technical Considerations

#### Platform and API constraints

The addon targets Blender 4.x and is built entirely on Blender's Python API (`bpy`). Because Blender ships with its own embedded Python interpreter, all dependencies must either be part of the Python standard library or bundled with the addon. This constraint rules out heavy third-party packages and motivates the choice of `sqlite3`, which ships with Python's standard library and requires no installation.

#### Storage architecture

Assets are stored using a two-layer approach:

**Managed `.blend` files** handle the actual datablock serialization. `bpy.data.libraries.write()` is used to write each asset to a small, addon-managed `.blend` file under a configurable library root directory. These files are never exposed directly to the user; the addon is the sole interface for reading and writing them. On load, `bpy.data.libraries.load()` appends or links the datablock into the active scene.

**SQLite** stores all metadata: asset names, types, tags, categories, descriptions, file paths, creation and modification timestamps, and the Blender version at save time. Because SQLite is the source of metadata rather than the `.blend` files themselves, the library is fully searchable and filterable without opening any `.blend` file. If the SQLite database is ever lost or corrupted, it can be rebuilt by scanning the managed `.blend` files.

#### Texture handling

Materials that reference external image textures require special handling. At save time, the addon detects all externally referenced images, copies them into a `textures/` subdirectory within the library root, and repoints the image paths before writing the `.blend` file. This keeps the library self-contained and portable without relying on image packing, which inflates file sizes unnecessarily.

#### Dependency tracking

Some asset types carry implicit dependencies. Node groups may reference other node groups. Collections contain objects that reference meshes, materials, and modifiers. The `AssetWriter` component is responsible for resolving and bundling these dependencies at write time so that assets load correctly in isolation.

#### Blender version compatibility

Blender's node tree structures and internal `.blend` format evolve between major versions. The Blender version is recorded in the SQLite database at save time, and the load operator surfaces a warning when the saved version differs significantly from the running version. This does not block loading but gives the user relevant context if something renders incorrectly.

#### Keymap and UI integration

Operators are registered into Blender's keymap system via `addon_keymaps`, making them invocable globally or scoped to specific editor types. The browser panel is implemented as a modal popup (`bpy.context.window_manager.invoke_popup`) so it can be triggered from a single hotkey without requiring the user to first position their cursor in a specific part of the interface. Context-aware filtering is implemented by checking `bpy.context.area.type` and `bpy.context.mode` at panel draw time.

#### Forward compatibility with cloud sync

The SQLite schema includes `workspace_id` and `owner_id` columns from the initial version, both nullable and unused in the local tier. A `sync/` module is stubbed with a no-op local provider so the interface exists before the implementation. Assets are assigned UUIDs (not auto-increment integers) at creation time to ensure stable identity across clients when the sync feature is introduced. Managed `.blend` files use content-addressed filenames (a hash of the file contents) to avoid redundant uploads and deduplicate identical assets across users.

#### Licensing

Because the addon imports `bpy` and executes within Blender's Python interpreter, it is considered a derivative work of Blender under the GPL and must be distributed under GPL v3 or a compatible license. This applies to the addon code only; a future server-side backend for cloud sync is a separate work communicating over a network and is not subject to the GPL's copyleft provisions.
