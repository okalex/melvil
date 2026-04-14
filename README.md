# Melvil - Blender Asset Manager

A free, open-source Blender addon for intuitive asset management. Save and load meshes, materials, and node groups directly from your scene without leaving your project.

## Features

- **Save from any context** — Right-click a mesh, material, or node group and save it as a reusable asset in one step.
- **Load without switching editors** — Add saved assets to your scene from the Add menu (Shift+A) or the built-in asset browser.
- **Auto-generated previews** — Thumbnail previews are rendered automatically when you save an asset.
- **Kits & tags** — Organize assets into kits and apply tags for fast filtering and search.
- **Easy access browser** — Open the asset browser with Ctrl+Shift+A to view, search, filter, rename, retag, and delete assets.
- **Local & portable** — All assets and metadata are stored locally in managed `.blend` files and a SQLite database. No external services required.

<img width="899" height="718" alt="image" src="https://github.com/user-attachments/assets/65bdca9f-2957-46f4-8add-540a14fd6637" />

## Installation

Requires **Blender 4.2** or later.

1. Download [melvil-0.1.0.zip](https://github.com/okalex/melvil/releases/download/v0.1.0/melvil-0.1.0.zip) from the releases page.
2. Drag the `.zip` file into an open Blender window — Blender will detect and install the addon automatically.

Alternatively: **Edit → Preferences → Get Extensions → ⏷ (drop-down) → Install from Disk** and select the `.zip` file.

## Usage

### Saving assets

Right-click on an object, material, or node group and select **Melvil → Save as Asset**. You'll be prompted to pick a kit, enter a name, and optionally add comma-separated tags.

| Context | What gets saved |
|---|---|
| 3D Viewport (object selected) | Mesh |
| Material slot / Shader Editor | Material |
| Node Editor (group node selected) | Node Group |

### Loading assets

| Action | How |
|---|---|
| Add a mesh to the scene | **Add menu** (Shift+A) → **Melvil** → select an asset (supports search within the add menu) |
| Apply a material | Right-click a material slot → **Melvil** → **Load Material** |
| Add a node group | **Add menu** (Shift+A) in the Node Editor → **Melvil** → select a node group |

### Asset browser

Press **Ctrl+Shift+A** in the 3D Viewport (or click **Browse Library** in the N-panel) to open the GPU-powered asset browser. From here you can:

- Filter by asset type (meshes, materials, node groups)
- Filter by kit or tags
- Rename, retag, move, or delete assets
- Add assets directly to your scene

### N-Panel

Open the sidebar in the 3D Viewport (N key) and select the **Melvil** tab to access:

- **Browse Library** — Opens the asset browser
- **Active Kit** — Choose which kit's assets appear in the Add menus
- **Preview Generation** — Toggle automatic preview rendering on save
- **Material Preview Object** — Choose the mesh used for material preview thumbnails

### Preferences

**Edit → Preferences → Add-ons → Melvil** to configure:

- **Library Root** — Directory where asset `.blend` files and textures are stored
- **Database Path** — Location of the SQLite metadata database (defaults to `<library_root>/melvil.db`)

## Development

### Prerequisites

- [uv](https://docs.astral.sh/uv/) for Python dependency management

### Setup

```sh
git clone https://github.com/okalex/melvil.git
cd melvil
make sync
```

### Common commands

| Command | Description |
|---|---|
| `make install` | Install the addon into Blender's local extensions directory |
| `make uninstall` | Remove the addon from Blender |
| `make test` | Run the test suite |
| `make package` | Build a distributable `.zip` in `dist/` |
| `make icons` | Rebuild the icon atlas from Blender's SVG source |

## License

[GPL-2.0-or-later](https://www.gnu.org/licenses/gpl-2.0.html)
