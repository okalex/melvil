"""Tests for ui/draw_helpers.py — shared draw_asset_section and load_assets helpers."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest

from melvil.db.connection import migrate
from melvil.db import assets as assets_db


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


# ---------------------------------------------------------------------------
# load_assets()
# ---------------------------------------------------------------------------


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.execute("PRAGMA foreign_keys = ON")
    c.row_factory = sqlite3.Row
    migrate(c)
    yield c
    c.close()


def _mock_open_db(conn):
    @contextmanager
    def _cm(_path):
        yield conn
    return _cm


SAMPLE_MATERIAL = dict(
    id="aaaaaaaa-0000-4000-8000-000000000001",
    name="Iron",
    type="MATERIAL",
    blend_path="iron_aaa.blend",
)

SAMPLE_MESH = dict(
    id="bbbbbbbb-0000-4000-8000-000000000002",
    name="Rock",
    type="MESH",
    blend_path="rock_bbb.blend",
)


class TestLoadAssets:
    def test_returns_all_assets_when_no_type_filter(self, conn):
        from melvil.ui.draw_helpers import load_assets

        assets_db.insert_asset(conn, **SAMPLE_MATERIAL)
        assets_db.insert_asset(conn, **SAMPLE_MESH)

        with patch("melvil.ui.draw_helpers.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ui.draw_helpers.open_db", _mock_open_db(conn)):
            rows = load_assets()

        assert len(rows) == 2

    def test_filters_by_type(self, conn):
        from melvil.ui.draw_helpers import load_assets

        assets_db.insert_asset(conn, **SAMPLE_MATERIAL)
        assets_db.insert_asset(conn, **SAMPLE_MESH)

        with patch("melvil.ui.draw_helpers.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ui.draw_helpers.open_db", _mock_open_db(conn)):
            rows = load_assets("MATERIAL")

        assert len(rows) == 1
        assert rows[0]["type"] == "MATERIAL"

    def test_returns_empty_list_for_empty_db(self, conn):
        from melvil.ui.draw_helpers import load_assets

        with patch("melvil.ui.draw_helpers.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ui.draw_helpers.open_db", _mock_open_db(conn)):
            rows = load_assets("MATERIAL")

        assert rows == []

    def test_raises_on_db_error(self):
        from melvil.ui.draw_helpers import load_assets
        from melvil.core.library import LibraryNotConfiguredError

        with patch("melvil.ui.draw_helpers.resolve_db_path",
                   side_effect=LibraryNotConfiguredError("not set")):
            with pytest.raises(LibraryNotConfiguredError):
                load_assets("MATERIAL")
