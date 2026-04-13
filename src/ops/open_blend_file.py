"""
MELVIL_OT_open_blend_file — open a managed .blend file in a new Blender window.
MELVIL_OT_reveal_blend_file — reveal a managed .blend file in the OS file explorer.

Both operators accept *blend_path* as an absolute filesystem path.  The asset
detail panel sets this from ``<library_root> / asset["blend_path"]``.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import bpy
from bpy.props import StringProperty


class MELVIL_OT_open_blend_file(bpy.types.Operator):
    """Open a Melvil .blend file in a new Blender window"""

    bl_idname = "melvil.open_blend_file"
    bl_label = "Open in Blender"
    bl_options = {"REGISTER"}

    blend_path: StringProperty(
        name="Blend File Path",
        description="Absolute path to the .blend file to open",
        default="",
        subtype="FILE_PATH",
    )

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        path = self.blend_path.strip()
        if not path:
            self.report({"ERROR"}, "Melvil: no blend file path provided.")
            return {"CANCELLED"}
        if not Path(path).is_file():
            self.report({"ERROR"}, f"Melvil: blend file not found: {path}")
            return {"CANCELLED"}

        try:
            subprocess.Popen([bpy.app.binary_path, path])
        except Exception as exc:  # noqa: BLE001
            self.report({"ERROR"}, f"Melvil: could not open Blender — {exc}")
            return {"CANCELLED"}

        return {"FINISHED"}


class MELVIL_OT_reveal_blend_file(bpy.types.Operator):
    """Reveal a Melvil .blend file in the OS file explorer"""

    bl_idname = "melvil.reveal_blend_file"
    bl_label = "Reveal in File Explorer"
    bl_options = {"REGISTER"}

    blend_path: StringProperty(
        name="Blend File Path",
        description="Absolute path to the .blend file to reveal",
        default="",
        subtype="FILE_PATH",
    )

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        path = self.blend_path.strip()
        if not path:
            self.report({"ERROR"}, "Melvil: no blend file path provided.")
            return {"CANCELLED"}

        try:
            if sys.platform == "darwin":
                subprocess.Popen(["open", "-R", path])
            elif sys.platform == "win32":
                subprocess.Popen(["explorer", f"/select,{path}"])
            else:
                # Linux: open the containing directory
                subprocess.Popen(["xdg-open", str(Path(path).parent)])
        except Exception as exc:  # noqa: BLE001
            self.report({"ERROR"}, f"Melvil: could not reveal file — {exc}")
            return {"CANCELLED"}

        return {"FINISHED"}
