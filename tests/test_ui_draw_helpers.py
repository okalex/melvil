"""Tests for ui/draw_helpers.py — shared draw_asset_section helper."""

from __future__ import annotations

from unittest.mock import MagicMock


def _make_asset(id: str, name: str, type: str) -> dict:
    return {"id": id, "name": name, "type": type}


class TestDrawAssetSection:
    def test_empty_shows_placeholder(self):
        from melvil.ui.draw_helpers import draw_asset_section

        layout = MagicMock()
        box = MagicMock()
        layout.box.return_value = box

        draw_asset_section(layout, "Meshes", "MESH_DATA", [])

        box.label.assert_any_call(text="No meshes saved yet")

    def test_header_label_uses_title_and_icon(self):
        from melvil.ui.draw_helpers import draw_asset_section

        layout = MagicMock()
        box = MagicMock()
        layout.box.return_value = box
        box.row.return_value = MagicMock()

        draw_asset_section(layout, "Meshes", "MESH_DATA", [_make_asset("1", "Rock", "MESH")])

        box.label.assert_any_call(text="Meshes", icon="MESH_DATA")

    def test_each_asset_gets_load_and_delete_buttons(self):
        from melvil.ui.draw_helpers import draw_asset_section

        layout = MagicMock()
        box = MagicMock()
        layout.box.return_value = box
        row = MagicMock()
        box.row.return_value = row

        draw_asset_section(layout, "Meshes", "MESH_DATA", [_make_asset("1", "Rock", "MESH")])

        ops = [c[0][0] for c in row.operator.call_args_list]
        assert "melvil.load_asset" in ops
        assert "melvil.delete_asset" in ops

    def test_load_button_asset_id_is_set(self):
        from melvil.ui.draw_helpers import draw_asset_section

        layout = MagicMock()
        box = MagicMock()
        layout.box.return_value = box
        row = MagicMock()
        box.row.return_value = row
        load_op = MagicMock()
        del_op = MagicMock()
        row.operator.side_effect = [load_op, del_op]

        draw_asset_section(layout, "Meshes", "MESH_DATA", [_make_asset("abc-123", "Rock", "MESH")])

        assert load_op.asset_id == "abc-123"

    def test_multiple_assets_each_get_a_row(self):
        from melvil.ui.draw_helpers import draw_asset_section

        layout = MagicMock()
        box = MagicMock()
        layout.box.return_value = box

        assets = [_make_asset(f"id{i}", f"Asset {i}", "MESH") for i in range(3)]
        draw_asset_section(layout, "Meshes", "MESH_DATA", assets)

        assert box.row.call_count == 3
