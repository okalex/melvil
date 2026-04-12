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

        layout.label.assert_any_call(text="Meshes", icon="MESH_DATA")

    def test_each_asset_gets_load_and_details_buttons(self):
        from melvil.ui.draw_helpers import draw_asset_section

        layout = MagicMock()
        box = MagicMock()
        layout.box.return_value = box
        row = MagicMock()
        box.row.return_value = row

        draw_asset_section(layout, "Meshes", "MESH_DATA", [_make_asset("1", "Rock", "MESH")])

        ops = [c[0][0] for c in row.operator.call_args_list]
        assert "melvil.load_asset" in ops
        assert "melvil.asset_select" in ops

    def test_load_button_asset_id_is_set(self):
        from melvil.ui.draw_helpers import draw_asset_section

        layout = MagicMock()
        box = MagicMock()
        layout.box.return_value = box
        row = MagicMock()
        box.row.return_value = row
        load_op = MagicMock()
        detail_op = MagicMock()
        row.operator.side_effect = [load_op, detail_op]

        draw_asset_section(layout, "Meshes", "MESH_DATA", [_make_asset("abc-123", "Rock", "MESH")])

        assert load_op.asset_id == "abc-123"

    def test_show_load_false_omits_load_button(self):
        from melvil.ui.draw_helpers import draw_asset_section

        layout = MagicMock()
        box = MagicMock()
        layout.box.return_value = box
        row = MagicMock()
        box.row.return_value = row

        draw_asset_section(layout, "Node Groups", "NODETREE", [_make_asset("1", "My Group", "NODE_GROUP")], show_load=False)

        ops = [c[0][0] for c in row.operator.call_args_list]
        assert "melvil.load_asset" not in ops
        assert "melvil.asset_select" in ops

    def test_multiple_assets_each_get_a_row(self):
        from melvil.ui.draw_helpers import draw_asset_section

        layout = MagicMock()
        box = MagicMock()
        layout.box.return_value = box

        assets = [_make_asset(f"id{i}", f"Asset {i}", "MESH") for i in range(3)]
        draw_asset_section(layout, "Meshes", "MESH_DATA", assets)

        assert box.row.call_count == 3


# ---------------------------------------------------------------------------
# draw_unified_asset_section()
# ---------------------------------------------------------------------------


class TestDrawUnifiedAssetSection:
    def test_empty_shows_placeholder(self):
        from melvil.ui.draw_helpers import draw_unified_asset_section

        layout = MagicMock()
        box = MagicMock()
        layout.box.return_value = box

        draw_unified_asset_section(layout, [])

        box.label.assert_any_call(text="No assets saved yet")

    def test_header_label_is_assets(self):
        from melvil.ui.draw_helpers import draw_unified_asset_section

        layout = MagicMock()
        box = MagicMock()
        layout.box.return_value = box
        box.row.return_value = MagicMock()

        draw_unified_asset_section(layout, [_make_asset("1", "Cube", "MESH")])

        layout.label.assert_any_call(text="Assets", icon="ASSET_MANAGER")

    def test_each_asset_row_has_type_icon(self):
        from melvil.ui.draw_helpers import draw_unified_asset_section

        layout = MagicMock()
        box = MagicMock()
        layout.box.return_value = box
        row = MagicMock()
        box.row.return_value = row

        draw_unified_asset_section(layout, [_make_asset("1", "Cube", "MESH")])

        row.label.assert_called_once_with(text="Cube", icon="MESH_DATA")

    def test_material_uses_material_icon(self):
        from melvil.ui.draw_helpers import draw_unified_asset_section

        layout = MagicMock()
        box = MagicMock()
        layout.box.return_value = box
        row = MagicMock()
        box.row.return_value = row

        draw_unified_asset_section(layout, [_make_asset("1", "Red", "MATERIAL")])

        row.label.assert_called_once_with(text="Red", icon="MATERIAL")

    def test_node_group_uses_nodetree_icon(self):
        from melvil.ui.draw_helpers import draw_unified_asset_section

        layout = MagicMock()
        box = MagicMock()
        layout.box.return_value = box
        row = MagicMock()
        box.row.return_value = row

        draw_unified_asset_section(layout, [_make_asset("1", "MyGroup", "NODE_GROUP")])

        row.label.assert_called_once_with(text="MyGroup", icon="NODETREE")

    def test_mesh_and_material_show_load_button(self):
        from melvil.ui.draw_helpers import draw_unified_asset_section

        for asset_type in ("MESH", "MATERIAL"):
            layout = MagicMock()
            box = MagicMock()
            layout.box.return_value = box
            row = MagicMock()
            box.row.return_value = row

            draw_unified_asset_section(layout, [_make_asset("1", "Asset", asset_type)])

            ops = [c[0][0] for c in row.operator.call_args_list]
            assert "melvil.load_asset" in ops, f"Expected load button for {asset_type}"

    def test_node_group_omits_load_button(self):
        from melvil.ui.draw_helpers import draw_unified_asset_section

        layout = MagicMock()
        box = MagicMock()
        layout.box.return_value = box
        row = MagicMock()
        box.row.return_value = row

        draw_unified_asset_section(layout, [_make_asset("1", "MyGroup", "NODE_GROUP")])

        ops = [c[0][0] for c in row.operator.call_args_list]
        assert "melvil.load_asset" not in ops
        assert "melvil.asset_select" in ops

    def test_selected_asset_detail_button_is_depressed(self):
        from melvil.ui.draw_helpers import draw_unified_asset_section

        layout = MagicMock()
        box = MagicMock()
        layout.box.return_value = box
        row = MagicMock()
        box.row.return_value = row
        load_op = MagicMock()
        detail_op = MagicMock()
        row.operator.side_effect = [load_op, detail_op]

        draw_unified_asset_section(layout, [_make_asset("abc", "Cube", "MESH")], selected_asset_id="abc")

        detail_call_kwargs = [c[1] for c in row.operator.call_args_list if c[0][0] == "melvil.asset_select"]
        assert any(kw.get("depress") is True for kw in detail_call_kwargs)

    def test_multiple_assets_each_get_a_row(self):
        from melvil.ui.draw_helpers import draw_unified_asset_section

        layout = MagicMock()
        box = MagicMock()
        layout.box.return_value = box

        assets = [
            _make_asset("1", "Cube", "MESH"),
            _make_asset("2", "Red", "MATERIAL"),
            _make_asset("3", "Group", "NODE_GROUP"),
        ]
        draw_unified_asset_section(layout, assets)

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

    def test_filters_by_kit_id(self, conn):
        from melvil.ui.draw_helpers import load_assets
        from melvil.db.kits import DEFAULT_KIT_ID
        from melvil.db import kits as kits_db

        kit_b_id = "bbbbbbbb-0000-4000-8000-000000000099"
        kits_db.insert_kit(conn, id=kit_b_id, name="Game Kit")
        assets_db.insert_asset(conn, **SAMPLE_MATERIAL, kit_id=DEFAULT_KIT_ID)
        mesh_in_b = {**SAMPLE_MESH, "kit_id": kit_b_id}
        assets_db.insert_asset(conn, **mesh_in_b)

        with patch("melvil.ui.draw_helpers.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ui.draw_helpers.open_db", _mock_open_db(conn)):
            rows = load_assets(kit_id=kit_b_id)

        assert len(rows) == 1
        assert rows[0]["kit_id"] == kit_b_id


class TestLoadKits:
    def test_returns_all_kits(self, conn):
        from melvil.ui.draw_helpers import load_kits
        from melvil.db import kits as kits_db

        kits_db.insert_kit(conn, id="cccccccc-0000-4000-8000-000000000001", name="Game Kit")

        with patch("melvil.ui.draw_helpers.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ui.draw_helpers.open_db", _mock_open_db(conn)):
            rows = load_kits()

        assert len(rows) == 2  # General (from migration) + Game Kit

    def test_raises_on_db_error(self):
        from melvil.ui.draw_helpers import load_kits
        from melvil.core.library import LibraryNotConfiguredError

        with patch("melvil.ui.draw_helpers.resolve_db_path",
                   side_effect=LibraryNotConfiguredError("not set")):
            with pytest.raises(LibraryNotConfiguredError):
                load_kits()



# ---------------------------------------------------------------------------
# filter_assets()
# ---------------------------------------------------------------------------


class TestFilterAssets:
    def _assets(self, *names):
        return [{"id": str(i), "name": n} for i, n in enumerate(names)]

    def test_empty_query_returns_all(self):
        from melvil.ui.draw_helpers import filter_assets

        assets = self._assets("Iron", "Plastic", "Glass")
        assert filter_assets(assets, "") == assets

    def test_blank_query_returns_all(self):
        from melvil.ui.draw_helpers import filter_assets

        assets = self._assets("Iron", "Plastic", "Glass")
        assert filter_assets(assets, "   ") == assets

    def test_exact_match_returns_asset(self):
        from melvil.ui.draw_helpers import filter_assets

        assets = self._assets("Iron", "Plastic")
        result = filter_assets(assets, "Iron")
        assert [a["name"] for a in result] == ["Iron"]

    def test_partial_match_returns_matching_assets(self):
        from melvil.ui.draw_helpers import filter_assets

        assets = self._assets("Plastic", "Plaster", "Glass")
        result = filter_assets(assets, "pla")
        assert [a["name"] for a in result] == ["Plastic", "Plaster"]

    def test_case_insensitive(self):
        from melvil.ui.draw_helpers import filter_assets

        assets = self._assets("Iron", "IRON OXIDE", "Rubber")
        result = filter_assets(assets, "iron")
        assert len(result) == 2
        assert {a["name"] for a in result} == {"Iron", "IRON OXIDE"}

    def test_ignores_whitespace_in_query(self):
        from melvil.ui.draw_helpers import filter_assets

        assets = self._assets("IronOxide", "Rubber")
        result = filter_assets(assets, "iron oxide")
        assert [a["name"] for a in result] == ["IronOxide"]

    def test_ignores_whitespace_in_asset_name(self):
        from melvil.ui.draw_helpers import filter_assets

        assets = self._assets("Iron Oxide", "Rubber")
        result = filter_assets(assets, "ironoxide")
        assert [a["name"] for a in result] == ["Iron Oxide"]

    def test_no_match_returns_empty(self):
        from melvil.ui.draw_helpers import filter_assets

        assets = self._assets("Iron", "Plastic", "Glass")
        result = filter_assets(assets, "zzz")
        assert result == []


# ---------------------------------------------------------------------------
# load_tags_for_asset_ids()
# ---------------------------------------------------------------------------


class TestLoadTagsForAssetIds:
    def test_returns_tags_for_given_assets(self, conn):
        from melvil.db import assets as assets_db, tags as tags_db
        from melvil.ui.draw_helpers import load_tags_for_asset_ids

        asset_id = "aaaaaaaa-0000-4000-8000-000000000001"
        assets_db.insert_asset(
            conn, id=asset_id, name="Iron", type="MATERIAL", blend_path="iron.blend"
        )
        tags_db.add_asset_tag(conn, asset_id, "metal")
        tags_db.add_asset_tag(conn, asset_id, "pbr")
        conn.commit()

        with patch("melvil.ui.draw_helpers.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ui.draw_helpers.open_db", _mock_open_db(conn)):
            rows = load_tags_for_asset_ids([asset_id])

        assert {r["name"] for r in rows} == {"metal", "pbr"}

    def test_empty_asset_ids_returns_empty(self, conn):
        from melvil.ui.draw_helpers import load_tags_for_asset_ids

        # Should short-circuit without a DB call
        rows = load_tags_for_asset_ids([])
        assert rows == []

    def test_raises_on_library_not_configured(self):
        from melvil.core.library import LibraryNotConfiguredError
        from melvil.ui.draw_helpers import load_tags_for_asset_ids

        with patch("melvil.ui.draw_helpers.resolve_db_path",
                   side_effect=LibraryNotConfiguredError("not set")):
            with pytest.raises(LibraryNotConfiguredError):
                load_tags_for_asset_ids(["some-id"])


# ---------------------------------------------------------------------------
# load_asset_tag_names()
# ---------------------------------------------------------------------------


class TestLoadAssetTagNames:
    def test_returns_tag_names_per_asset(self, conn):
        from melvil.ui.draw_helpers import load_asset_tag_names

        assets_db.insert_asset(conn, **SAMPLE_MATERIAL)
        from melvil.db import tags as tags_db
        tags_db.add_asset_tag(conn, SAMPLE_MATERIAL["id"], "metal")
        tags_db.add_asset_tag(conn, SAMPLE_MATERIAL["id"], "pbr")
        conn.commit()

        with patch("melvil.ui.draw_helpers.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ui.draw_helpers.open_db", _mock_open_db(conn)):
            result = load_asset_tag_names([SAMPLE_MATERIAL["id"]])

        assert SAMPLE_MATERIAL["id"] in result
        assert sorted(result[SAMPLE_MATERIAL["id"]]) == ["metal", "pbr"]

    def test_empty_asset_ids_returns_empty(self):
        from melvil.ui.draw_helpers import load_asset_tag_names

        result = load_asset_tag_names([])
        assert result == {}

    def test_raises_on_library_not_configured(self):
        from melvil.ui.draw_helpers import load_asset_tag_names
        from melvil.core.library import LibraryNotConfiguredError

        with patch("melvil.ui.draw_helpers.resolve_db_path",
                   side_effect=LibraryNotConfiguredError("not set")):
            with pytest.raises(LibraryNotConfiguredError):
                load_asset_tag_names(["some-id"])


# ---------------------------------------------------------------------------
# filter_assets() — tag name matching
# ---------------------------------------------------------------------------


class TestFilterAssetsTagNames:
    def _assets(self, *names):
        return [{"id": str(i), "name": n} for i, n in enumerate(names)]

    def test_matches_asset_by_tag_name(self):
        from melvil.ui.draw_helpers import filter_assets

        assets = self._assets("Iron", "Glass")
        tag_names = {"0": ["metal"], "1": ["transparent"]}

        result = filter_assets(assets, "metal", tag_names)
        assert [a["name"] for a in result] == ["Iron"]

    def test_name_match_still_works_with_tag_names_provided(self):
        from melvil.ui.draw_helpers import filter_assets

        assets = self._assets("Iron", "Glass")
        tag_names = {"0": ["metal"]}

        result = filter_assets(assets, "Glass", tag_names)
        assert [a["name"] for a in result] == ["Glass"]

    def test_tag_search_case_insensitive(self):
        from melvil.ui.draw_helpers import filter_assets

        assets = self._assets("Rock")
        tag_names = {"0": ["Outdoor"]}

        result = filter_assets(assets, "outdoor", tag_names)
        assert len(result) == 1

    def test_tag_search_whitespace_collapsed(self):
        from melvil.ui.draw_helpers import filter_assets

        assets = self._assets("Rock")
        tag_names = {"0": ["pbr material"]}

        # Query collapses spaces — "pbrmaterial" should still match "pbr material"
        result = filter_assets(assets, "pbrmaterial", tag_names)
        assert len(result) == 1

    def test_asset_not_duplicated_when_name_and_tag_both_match(self):
        from melvil.ui.draw_helpers import filter_assets

        assets = self._assets("Metal Rock")
        tag_names = {"0": ["metal"]}

        # "metal" matches both asset name and tag — should appear only once
        result = filter_assets(assets, "metal", tag_names)
        assert len(result) == 1

    def test_no_tag_names_provided_behaves_as_before(self):
        from melvil.ui.draw_helpers import filter_assets

        assets = self._assets("Iron", "Glass")
        # "metal" doesn't match any asset name → no results without tag_names
        result = filter_assets(assets, "metal")
        assert result == []

    def test_empty_query_returns_all_regardless_of_tag_names(self):
        from melvil.ui.draw_helpers import filter_assets

        assets = self._assets("Iron", "Glass")
        tag_names = {"0": ["metal"]}

        assert filter_assets(assets, "", tag_names) == assets
