"""BLAMMO_OT_tag_delete — delete a tag globally, with confirmation."""

from __future__ import annotations

import bpy
from bpy.props import StringProperty

from ..core.library import LibraryNotConfiguredError, resolve_db_path
from ..db import open_db
from ..db.tags import delete_tag, get_tag_by_id, list_tags_with_usage


class BLAMMO_OT_tag_delete(bpy.types.Operator):
    """Delete a tag globally from the Blammo library"""

    bl_idname = "blammo.tag_delete"
    bl_label = "Delete Tag"
    bl_options = {"REGISTER"}

    tag_id: StringProperty(
        name="Tag ID",
        description="UUID of the tag to delete",
        default="",
        options={"HIDDEN"},
    )

    # Populated in invoke() for display in the confirmation dialog.
    _tag_name: str = ""
    _usage_count: int = 0

    @classmethod
    def poll(cls, context):
        return True

    def invoke(self, context, event):
        tag_id = self.tag_id.strip()
        if not tag_id:
            self.report({"ERROR"}, "Blammo!: no tag ID provided.")
            return {"CANCELLED"}

        try:
            with open_db(resolve_db_path()) as conn:
                row = get_tag_by_id(conn, tag_id)
                if row is None:
                    self.report({"ERROR"}, "Blammo!: tag not found.")
                    return {"CANCELLED"}
                self._tag_name = row["name"]
                usage_rows = list_tags_with_usage(conn)
                for r in usage_rows:
                    if r["id"] == tag_id:
                        self._usage_count = r["usage_count"]
                        break
        except LibraryNotConfiguredError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        except Exception as exc:  # noqa: BLE001
            self.report({"ERROR"}, f"Blammo!: could not load tag — {exc}")
            return {"CANCELLED"}

        return context.window_manager.invoke_props_dialog(self, width=340)

    def draw(self, context):
        layout = self.layout
        layout.label(
            text=f"Delete tag \"{self._tag_name}\"?",
            icon="ERROR",
        )
        layout.label(
            text=f"Used by {self._usage_count} asset(s). This cannot be undone.",
        )

    def execute(self, context):
        tag_id = self.tag_id.strip()
        if not tag_id:
            self.report({"ERROR"}, "Blammo!: no tag ID provided.")
            return {"CANCELLED"}

        try:
            with open_db(resolve_db_path()) as conn:
                delete_tag(conn, tag_id)
                conn.commit()
        except LibraryNotConfiguredError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        except Exception as exc:  # noqa: BLE001
            self.report({"ERROR"}, f"Blammo!: could not delete tag — {exc}")
            return {"CANCELLED"}

        self.report({"INFO"}, f"Blammo!: tag '{self._tag_name}' deleted.")
        return {"FINISHED"}
