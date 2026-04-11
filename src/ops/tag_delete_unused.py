"""MELVIL_OT_tag_delete_unused — delete all tags with zero usage, with confirmation."""

from __future__ import annotations

import bpy

from ..core.library import LibraryNotConfiguredError, resolve_db_path
from ..db import open_db
from ..db.tags import delete_tag, list_tags_with_usage


class MELVIL_OT_tag_delete_unused(bpy.types.Operator):
    """Delete all tags that are not applied to any asset"""

    bl_idname = "melvil.tag_delete_unused"
    bl_label = "Delete Unused Tags"
    bl_options = {"REGISTER"}

    _unused_count: int = 0

    @classmethod
    def poll(cls, context):
        return True

    def invoke(self, context, event):
        try:
            with open_db(resolve_db_path()) as conn:
                rows = list_tags_with_usage(conn)
                self._unused_count = sum(1 for r in rows if r["usage_count"] == 0)
        except LibraryNotConfiguredError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        except Exception as exc:  # noqa: BLE001
            self.report({"ERROR"}, f"Melvil: could not load tags — {exc}")
            return {"CANCELLED"}

        if self._unused_count == 0:
            self.report({"INFO"}, "Melvil: no unused tags to delete.")
            return {"CANCELLED"}

        return context.window_manager.invoke_props_dialog(self, width=340)

    def draw(self, context):
        layout = self.layout
        layout.label(
            text=f"Delete {self._unused_count} unused tag(s)?",
            icon="ERROR",
        )
        layout.label(text="This cannot be undone.")

    def execute(self, context):
        try:
            with open_db(resolve_db_path()) as conn:
                rows = list_tags_with_usage(conn)
                unused = [r["id"] for r in rows if r["usage_count"] == 0]
                for tag_id in unused:
                    delete_tag(conn, tag_id)
                conn.commit()
                deleted = len(unused)
        except LibraryNotConfiguredError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        except Exception as exc:  # noqa: BLE001
            self.report({"ERROR"}, f"Melvil: could not delete unused tags — {exc}")
            return {"CANCELLED"}

        self.report({"INFO"}, f"Melvil: deleted {deleted} unused tag(s).")
        return {"FINISHED"}
