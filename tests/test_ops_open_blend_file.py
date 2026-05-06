"""Tests for ops/open_blend_file.py."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# BLAMMO_OT_open_blend_file
# ---------------------------------------------------------------------------


class TestOpenBlendFileMetadata:
    def test_bl_idname(self):
        from blammo.ops.open_blend_file import BLAMMO_OT_open_blend_file

        assert BLAMMO_OT_open_blend_file.bl_idname == "blammo.open_blend_file"

    def test_bl_label(self):
        from blammo.ops.open_blend_file import BLAMMO_OT_open_blend_file

        assert "Blender" in BLAMMO_OT_open_blend_file.bl_label


class TestOpenBlendFileExecute:
    def _make_op(self, blend_path=""):
        from blammo.ops.open_blend_file import BLAMMO_OT_open_blend_file

        op = BLAMMO_OT_open_blend_file()
        op.blend_path = blend_path
        return op

    def test_returns_cancelled_when_path_empty(self):
        op = self._make_op("")
        result = op.execute(MagicMock())
        assert result == {"CANCELLED"}

    def test_returns_cancelled_when_file_not_found(self, tmp_path):
        op = self._make_op(str(tmp_path / "missing.blend"))
        result = op.execute(MagicMock())
        assert result == {"CANCELLED"}

    def test_spawns_blender_process_with_file(self, tmp_path):
        blend = tmp_path / "asset.blend"
        blend.touch()
        op = self._make_op(str(blend))

        import bpy
        bpy.app.binary_path = "/usr/bin/blender"

        with patch("blammo.ops.open_blend_file.subprocess.Popen") as mock_popen:
            result = op.execute(MagicMock())

        assert result == {"FINISHED"}
        mock_popen.assert_called_once_with(["/usr/bin/blender", str(blend)])

    def test_returns_cancelled_on_popen_error(self, tmp_path):
        blend = tmp_path / "asset.blend"
        blend.touch()
        op = self._make_op(str(blend))

        import bpy
        bpy.app.binary_path = "/usr/bin/blender"

        with patch("blammo.ops.open_blend_file.subprocess.Popen", side_effect=OSError("not found")):
            result = op.execute(MagicMock())

        assert result == {"CANCELLED"}


# ---------------------------------------------------------------------------
# BLAMMO_OT_reveal_blend_file
# ---------------------------------------------------------------------------


class TestRevealBlendFileMetadata:
    def test_bl_idname(self):
        from blammo.ops.open_blend_file import BLAMMO_OT_reveal_blend_file

        assert BLAMMO_OT_reveal_blend_file.bl_idname == "blammo.reveal_blend_file"


class TestRevealBlendFileExecute:
    def _make_op(self, blend_path=""):
        from blammo.ops.open_blend_file import BLAMMO_OT_reveal_blend_file

        op = BLAMMO_OT_reveal_blend_file()
        op.blend_path = blend_path
        return op

    def test_returns_cancelled_when_path_empty(self):
        op = self._make_op("")
        result = op.execute(MagicMock())
        assert result == {"CANCELLED"}

    def test_macos_uses_open_reveal(self, tmp_path):
        blend = tmp_path / "asset.blend"
        op = self._make_op(str(blend))

        with patch("blammo.ops.open_blend_file.sys.platform", "darwin"), \
             patch("blammo.ops.open_blend_file.subprocess.Popen") as mock_popen:
            op.execute(MagicMock())

        mock_popen.assert_called_once_with(["open", "-R", str(blend)])

    def test_windows_uses_explorer_select(self, tmp_path):
        blend = tmp_path / "asset.blend"
        op = self._make_op(str(blend))

        with patch("blammo.ops.open_blend_file.sys.platform", "win32"), \
             patch("blammo.ops.open_blend_file.subprocess.Popen") as mock_popen:
            op.execute(MagicMock())

        mock_popen.assert_called_once_with(["explorer", f"/select,{blend}"])

    def test_linux_opens_parent_directory(self, tmp_path):
        blend = tmp_path / "asset.blend"
        op = self._make_op(str(blend))

        with patch("blammo.ops.open_blend_file.sys.platform", "linux"), \
             patch("blammo.ops.open_blend_file.subprocess.Popen") as mock_popen:
            op.execute(MagicMock())

        mock_popen.assert_called_once_with(["xdg-open", str(tmp_path)])

    def test_returns_finished_on_success(self, tmp_path):
        blend = tmp_path / "asset.blend"
        op = self._make_op(str(blend))

        with patch("blammo.ops.open_blend_file.sys.platform", "darwin"), \
             patch("blammo.ops.open_blend_file.subprocess.Popen"):
            result = op.execute(MagicMock())

        assert result == {"FINISHED"}

    def test_returns_cancelled_on_popen_error(self, tmp_path):
        blend = tmp_path / "asset.blend"
        op = self._make_op(str(blend))

        with patch("blammo.ops.open_blend_file.sys.platform", "darwin"), \
             patch("blammo.ops.open_blend_file.subprocess.Popen", side_effect=OSError("no open")):
            result = op.execute(MagicMock())

        assert result == {"CANCELLED"}
