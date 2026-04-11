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
        assert "melvil.delete_asset" in ops

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


class TestDrawAssetSectionKits:
    def test_kits_provided_shows_move_to_kit_button(self):
        from melvil.ui.draw_helpers import draw_asset_section

        layout = MagicMock()
        box = MagicMock()
        layout.box.return_value = box
        row = MagicMock()
        box.row.return_value = row
        fake_kits = [{"id": "kit-1", "name": "General"}]

        draw_asset_section(layout, "Meshes", "MESH_DATA",
                           [_make_asset("1", "Rock", "MESH")], kits=fake_kits)

        ops = [c[0][0] for c in row.operator.call_args_list]
        assert "melvil.asset_set_kit" in ops

    def test_no_kits_omits_move_to_kit_button(self):
        from melvil.ui.draw_helpers import draw_asset_section

        layout = MagicMock()
        box = MagicMock()
        layout.box.return_value = box
        row = MagicMock()
        box.row.return_value = row

        draw_asset_section(layout, "Meshes", "MESH_DATA",
                           [_make_asset("1", "Rock", "MESH")])  # no kits kwarg

        ops = [c[0][0] for c in row.operator.call_args_list]
        assert "melvil.asset_set_kit" not in ops

    def test_move_to_kit_asset_id_is_set(self):
        from melvil.ui.draw_helpers import draw_asset_section

        layout = MagicMock()
        box = MagicMock()
        layout.box.return_value = box
        row = MagicMock()
        box.row.return_value = row
        load_op = MagicMock()
        move_op = MagicMock()
        del_op = MagicMock()
        row.operator.side_effect = [load_op, move_op, del_op]
        fake_kits = [{"id": "kit-1", "name": "General"}]

        draw_asset_section(layout, "Meshes", "MESH_DATA",
                           [_make_asset("asset-xyz", "Rock", "MESH")], kits=fake_kits)

        assert move_op.asset_id == "asset-xyz"


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
# load_tags_with_usage()
# ---------------------------------------------------------------------------


class TestLoadTagsWithUsage:
    def test_returns_all_tags(self, conn):
        from melvil.db import tags as tags_db
        from melvil.ui.draw_helpers import load_tags_with_usage

        tags_db.get_or_create_tag(conn, "metal")
        tags_db.get_or_create_tag(conn, "hard")
        conn.commit()

        with patch("melvil.ui.draw_helpers.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ui.draw_helpers.open_db", _mock_open_db(conn)):
            rows = load_tags_with_usage()

        assert len(rows) == 2
        names = {r["name"] for r in rows}
        assert names == {"metal", "hard"}

    def test_usage_count_reflects_assets(self, conn):
        from melvil.db import assets as assets_db, tags as tags_db
        from melvil.ui.draw_helpers import load_tags_with_usage

        asset_id = "aaaaaaaa-0000-4000-8000-000000000001"
        assets_db.insert_asset(
            conn, id=asset_id, name="Iron", type="MATERIAL", blend_path="iron.blend"
        )
        tags_db.add_asset_tag(conn, asset_id, "metal")
        tags_db.get_or_create_tag(conn, "orphan")
        conn.commit()

        with patch("melvil.ui.draw_helpers.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ui.draw_helpers.open_db", _mock_open_db(conn)):
            rows = load_tags_with_usage()

        by_name = {r["name"]: r for r in rows}
        assert by_name["metal"]["usage_count"] == 1
        assert by_name["orphan"]["usage_count"] == 0

    def test_returns_empty_list_when_no_tags(self, conn):
        from melvil.ui.draw_helpers import load_tags_with_usage

        with patch("melvil.ui.draw_helpers.resolve_db_path", return_value=":memory:"), \
             patch("melvil.ui.draw_helpers.open_db", _mock_open_db(conn)):
            rows = load_tags_with_usage()

        assert rows == []

    def test_raises_on_library_not_configured(self):
        from melvil.core.library import LibraryNotConfiguredError
        from melvil.ui.draw_helpers import load_tags_with_usage

        with patch("melvil.ui.draw_helpers.resolve_db_path",
                   side_effect=LibraryNotConfiguredError("not set")):
            with pytest.raises(LibraryNotConfiguredError):
                load_tags_with_usage()


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
# draw_tag_filter_pills()
# ---------------------------------------------------------------------------


def _make_pill_tag(id: str, name: str) -> dict:
    return {"id": id, "name": name}


class TestDrawTagFilterPills:
    def test_empty_visible_tags_renders_nothing(self):
        from melvil.ui.draw_helpers import draw_tag_filter_pills

        layout = MagicMock()
        draw_tag_filter_pills(layout, [], [])
        layout.row.assert_not_called()

    def test_each_tag_gets_a_button(self):
        from melvil.ui.draw_helpers import draw_tag_filter_pills

        layout = MagicMock()
        row = MagicMock()
        layout.row.return_value = row

        tags = [_make_pill_tag("id1", "metal"), _make_pill_tag("id2", "pbr")]
        draw_tag_filter_pills(layout, tags, [])

        op_ids = [c[0][0] for c in row.operator.call_args_list]
        assert op_ids.count("melvil.tag_filter_toggle") == 2

    def test_active_tag_button_is_depressed(self):
        from melvil.ui.draw_helpers import draw_tag_filter_pills

        layout = MagicMock()
        row = MagicMock()
        layout.row.return_value = row
        active_btn = MagicMock()
        inactive_btn = MagicMock()
        row.operator.side_effect = [active_btn, inactive_btn]

        tags = [_make_pill_tag("id1", "metal"), _make_pill_tag("id2", "pbr")]
        draw_tag_filter_pills(layout, tags, ["id1"])

        _, kwargs0 = row.operator.call_args_list[0]
        _, kwargs1 = row.operator.call_args_list[1]
        assert kwargs0.get("depress") is True
        assert kwargs1.get("depress") is False

    def test_tag_id_set_on_button(self):
        from melvil.ui.draw_helpers import draw_tag_filter_pills

        layout = MagicMock()
        row = MagicMock()
        layout.row.return_value = row
        btn = MagicMock()
        row.operator.return_value = btn

        draw_tag_filter_pills(layout, [_make_pill_tag("uuid-123", "metal")], [])

        assert btn.tag_id == "uuid-123"

    def test_clear_button_shown_when_filters_active(self):
        from melvil.ui.draw_helpers import draw_tag_filter_pills

        layout = MagicMock()
        layout.row.return_value = MagicMock()

        draw_tag_filter_pills(layout, [_make_pill_tag("id1", "metal")], ["id1"])

        op_ids = [c[0][0] for c in layout.operator.call_args_list]
        assert "melvil.tag_filter_clear" in op_ids

    def test_clear_button_not_shown_when_no_filters_active(self):
        from melvil.ui.draw_helpers import draw_tag_filter_pills

        layout = MagicMock()
        layout.row.return_value = MagicMock()

        draw_tag_filter_pills(layout, [_make_pill_tag("id1", "metal")], [])

        op_ids = [c[0][0] for c in layout.operator.call_args_list]
        assert "melvil.tag_filter_clear" not in op_ids


# ---------------------------------------------------------------------------
# draw_tag_management_section()
# ---------------------------------------------------------------------------


def _make_tag(id: str, name: str, usage_count: int) -> dict:
    return {"id": id, "name": name, "usage_count": usage_count}


class TestDrawTagManagementSection:
    def _make_layout(self):
        layout = MagicMock()
        header_row = MagicMock()
        sort_row = MagicMock()
        header_row.row.return_value = sort_row
        layout.row.return_value = header_row
        box = MagicMock()
        box.row.return_value = MagicMock()
        layout.box.return_value = box
        return layout, box, header_row, sort_row

    def _simple_layout(self):
        """Convenience: returns only layout and box for tests that don't inspect the header row."""
        layout, box, _header, _sort = self._make_layout()
        return layout, box

    def test_empty_tag_list_shows_placeholder(self):
        from melvil.ui.draw_helpers import draw_tag_management_section

        layout, box = self._simple_layout()
        draw_tag_management_section(layout, [])
        box.label.assert_called_with(text="No tags in library")

    def test_sort_buttons_rendered(self):
        from melvil.ui.draw_helpers import draw_tag_management_section

        layout, box, header_row, sort_row = self._make_layout()

        draw_tag_management_section(layout, [], sort_by="NAME")

        op_ids = [c[0][0] for c in sort_row.operator.call_args_list]
        assert op_ids.count("melvil.tag_sort_toggle") == 2

    def test_new_tag_button_rendered(self):
        from melvil.ui.draw_helpers import draw_tag_management_section

        layout, box, header_row, sort_row = self._make_layout()

        draw_tag_management_section(layout, [], sort_by="NAME")

        op_ids = [c[0][0] for c in header_row.operator.call_args_list]
        assert "melvil.tag_create" in op_ids

    def test_name_sort_button_depressed_when_sort_by_name(self):
        from melvil.ui.draw_helpers import draw_tag_management_section

        layout, box, header_row, sort_row = self._make_layout()
        name_btn = MagicMock()
        usage_btn = MagicMock()
        sort_row.operator.side_effect = [name_btn, usage_btn]

        draw_tag_management_section(layout, [], sort_by="NAME")

        _, kwargs = sort_row.operator.call_args_list[0]
        assert kwargs.get("depress") is True
        _, kwargs2 = sort_row.operator.call_args_list[1]
        assert kwargs2.get("depress") is False

    def test_usage_sort_button_depressed_when_sort_by_usage(self):
        from melvil.ui.draw_helpers import draw_tag_management_section

        layout, box, header_row, sort_row = self._make_layout()
        name_btn = MagicMock()
        usage_btn = MagicMock()
        sort_row.operator.side_effect = [name_btn, usage_btn]

        draw_tag_management_section(layout, [], sort_by="USAGE")

        _, kwargs = sort_row.operator.call_args_list[0]
        assert kwargs.get("depress") is False
        _, kwargs2 = sort_row.operator.call_args_list[1]
        assert kwargs2.get("depress") is True

    def test_each_tag_gets_rename_and_delete_buttons(self):
        from melvil.ui.draw_helpers import draw_tag_management_section

        layout, box = self._simple_layout()
        tag_row = MagicMock()
        box.row.return_value = tag_row

        tags = [_make_tag("id1", "metal", 2)]
        draw_tag_management_section(layout, tags)

        op_ids = [c[0][0] for c in tag_row.operator.call_args_list]
        assert "melvil.tag_rename" in op_ids
        assert "melvil.tag_delete" in op_ids

    def test_rename_op_receives_tag_id(self):
        from melvil.ui.draw_helpers import draw_tag_management_section

        layout, box = self._simple_layout()
        tag_row = MagicMock()
        box.row.return_value = tag_row
        rename_op = MagicMock()
        del_op = MagicMock()
        tag_row.operator.side_effect = [rename_op, del_op]

        tags = [_make_tag("uuid-abc", "metal", 2)]
        draw_tag_management_section(layout, tags)

        assert rename_op.tag_id == "uuid-abc"

    def test_zero_usage_tag_name_column_is_disabled(self):
        from melvil.ui.draw_helpers import draw_tag_management_section

        layout, box = self._simple_layout()
        tag_row = MagicMock()
        name_col = MagicMock()
        tag_row.column.return_value = name_col
        box.row.return_value = tag_row

        tags = [_make_tag("id1", "orphan", 0)]
        draw_tag_management_section(layout, tags)

        assert name_col.enabled is False

    def test_used_tag_name_column_is_enabled(self):
        from melvil.ui.draw_helpers import draw_tag_management_section

        layout, box = self._simple_layout()
        tag_row = MagicMock()
        name_col = MagicMock()
        tag_row.column.return_value = name_col
        box.row.return_value = tag_row

        tags = [_make_tag("id1", "metal", 3)]
        draw_tag_management_section(layout, tags)

        assert name_col.enabled is True

    def test_delete_unused_button_shown_when_unused_exist(self):
        from melvil.ui.draw_helpers import draw_tag_management_section

        layout, box = self._simple_layout()
        tags = [_make_tag("id1", "metal", 1), _make_tag("id2", "orphan", 0)]
        draw_tag_management_section(layout, tags)

        op_ids = [c[0][0] for c in layout.operator.call_args_list]
        assert "melvil.tag_delete_unused" in op_ids

    def test_delete_unused_button_not_shown_when_all_used(self):
        from melvil.ui.draw_helpers import draw_tag_management_section

        layout, box = self._simple_layout()
        tags = [_make_tag("id1", "metal", 1), _make_tag("id2", "hard", 2)]
        draw_tag_management_section(layout, tags)

        op_ids = [c[0][0] for c in layout.operator.call_args_list]
        assert "melvil.tag_delete_unused" not in op_ids

    def test_sort_by_name_orders_alphabetically(self):
        from melvil.ui.draw_helpers import draw_tag_management_section

        layout, box = self._simple_layout()

        row_mocks = []

        def make_row(**kw):
            rm = MagicMock()
            rm.column.return_value = MagicMock()
            row_mocks.append(rm)
            return rm

        box.row.side_effect = make_row

        tags = [
            _make_tag("c", "Zinc", 1),
            _make_tag("a", "Aluminium", 1),
            _make_tag("b", "Iron", 1),
        ]
        draw_tag_management_section(layout, tags, sort_by="NAME")

        name_texts = []
        for rm in row_mocks:
            col = rm.column.return_value
            if col.label.call_args_list:
                name_texts.append(col.label.call_args_list[0][1].get("text", ""))

        assert name_texts == ["Aluminium", "Iron", "Zinc"]

    def test_sort_by_usage_orders_by_descending_count(self):
        from melvil.ui.draw_helpers import draw_tag_management_section

        layout, box = self._simple_layout()

        row_mocks = []

        def make_row(**kw):
            rm = MagicMock()
            rm.column.return_value = MagicMock()
            row_mocks.append(rm)
            return rm

        box.row.side_effect = make_row

        tags = [
            _make_tag("a", "rare", 1),
            _make_tag("b", "common", 5),
            _make_tag("c", "medium", 3),
        ]
        draw_tag_management_section(layout, tags, sort_by="USAGE")

        name_texts = []
        for rm in row_mocks:
            col = rm.column.return_value
            if col.label.call_args_list:
                name_texts.append(col.label.call_args_list[0][1].get("text", ""))

        assert name_texts == ["common", "medium", "rare"]


# ---------------------------------------------------------------------------
# draw_asset_section — asset_tags parameter (inline tag pills)
# ---------------------------------------------------------------------------


class TestDrawAssetSectionAssetTags:
    """Tests for the optional asset_tags and active_tag_ids parameters."""

    def _draw(self, assets, asset_tags=None, active_tag_ids=()):
        from melvil.ui.draw_helpers import draw_asset_section

        layout = MagicMock()
        box = MagicMock()
        layout.box.return_value = box
        # box.row() returns a new mock each time so we can inspect per-row calls.
        box.row.side_effect = lambda **kwargs: MagicMock()
        draw_asset_section(
            layout, "Meshes", "MESH_DATA", assets,
            asset_tags=asset_tags, active_tag_ids=active_tag_ids,
        )
        return layout, box

    def test_no_tag_row_when_asset_tags_is_none(self):
        """Without asset_tags each asset only gets one row."""
        from melvil.ui.draw_helpers import draw_asset_section

        layout = MagicMock()
        box = MagicMock()
        layout.box.return_value = box
        box.row.return_value = MagicMock()

        draw_asset_section(layout, "Meshes", "MESH_DATA",
                           [_make_asset("a1", "Rock", "MESH")])

        # One row per asset
        assert box.row.call_count == 1

    def test_tag_row_added_per_asset_when_asset_tags_provided(self):
        """With asset_tags, each asset gets a main row + a tag sub-row."""
        layout, box = self._draw(
            [_make_asset("a1", "Rock", "MESH")],
            asset_tags={"a1": [{"id": "t1", "name": "outdoor"}]},
        )
        # 2 rows for 1 asset: main + tag
        assert box.row.call_count == 2

    def test_tag_pill_operator_invoked_for_each_tag(self):
        from melvil.ui.draw_helpers import draw_asset_section

        layout = MagicMock()
        box = MagicMock()
        layout.box.return_value = box
        main_row = MagicMock()
        tag_row = MagicMock()
        box.row.side_effect = [main_row, tag_row]

        draw_asset_section(
            layout, "Meshes", "MESH_DATA",
            [_make_asset("a1", "Rock", "MESH")],
            asset_tags={"a1": [{"id": "t1", "name": "outdoor"}, {"id": "t2", "name": "pbr"}]},
        )

        ops = [c[0][0] for c in tag_row.operator.call_args_list]
        assert ops.count("melvil.tag_filter_toggle") == 2

    def test_tag_pill_depress_reflects_active_tag_ids(self):
        from melvil.ui.draw_helpers import draw_asset_section

        layout = MagicMock()
        box = MagicMock()
        layout.box.return_value = box
        main_row = MagicMock()
        tag_row = MagicMock()
        pill = MagicMock()
        tag_row.operator.return_value = pill
        box.row.side_effect = [main_row, tag_row]

        draw_asset_section(
            layout, "Meshes", "MESH_DATA",
            [_make_asset("a1", "Rock", "MESH")],
            asset_tags={"a1": [{"id": "active-id", "name": "active"}]},
            active_tag_ids=["active-id"],
        )

        # call_args_list[0] is the pill; call_args_list[-1] is the edit button
        _op_id, kwargs = tag_row.operator.call_args_list[0]
        assert kwargs.get("depress") is True

    def test_inactive_tag_pill_not_depressed(self):
        from melvil.ui.draw_helpers import draw_asset_section

        layout = MagicMock()
        box = MagicMock()
        layout.box.return_value = box
        main_row = MagicMock()
        tag_row = MagicMock()
        pill = MagicMock()
        tag_row.operator.return_value = pill
        box.row.side_effect = [main_row, tag_row]

        draw_asset_section(
            layout, "Meshes", "MESH_DATA",
            [_make_asset("a1", "Rock", "MESH")],
            asset_tags={"a1": [{"id": "inactive-id", "name": "rare"}]},
            active_tag_ids=[],
        )

        # call_args_list[0] is the pill; call_args_list[-1] is the edit button
        _op_id, kwargs = tag_row.operator.call_args_list[0]
        assert kwargs.get("depress") is False

    def test_edit_button_always_shown_in_tag_row(self):
        from melvil.ui.draw_helpers import draw_asset_section

        layout = MagicMock()
        box = MagicMock()
        layout.box.return_value = box
        main_row = MagicMock()
        tag_row = MagicMock()
        box.row.side_effect = [main_row, tag_row]

        draw_asset_section(
            layout, "Meshes", "MESH_DATA",
            [_make_asset("a1", "Rock", "MESH")],
            asset_tags={"a1": []},  # no tags
        )

        ops = [c[0][0] for c in tag_row.operator.call_args_list]
        assert "melvil.asset_edit_tags" in ops

    def test_edit_button_asset_id_and_name_set(self):
        from melvil.ui.draw_helpers import draw_asset_section

        layout = MagicMock()
        box = MagicMock()
        layout.box.return_value = box
        main_row = MagicMock()
        tag_row = MagicMock()
        edit_op = MagicMock()
        tag_row.operator.return_value = edit_op
        box.row.side_effect = [main_row, tag_row]

        draw_asset_section(
            layout, "Meshes", "MESH_DATA",
            [_make_asset("asset-99", "Big Rock", "MESH")],
            asset_tags={"asset-99": []},
        )

        assert edit_op.asset_id == "asset-99"
        assert edit_op.asset_name == "Big Rock"

    def test_no_tags_shows_disabled_no_tags_label(self):
        from melvil.ui.draw_helpers import draw_asset_section

        layout = MagicMock()
        box = MagicMock()
        layout.box.return_value = box
        main_row = MagicMock()
        tag_row = MagicMock()
        sub_row = MagicMock()
        tag_row.row.return_value = sub_row
        box.row.side_effect = [main_row, tag_row]

        draw_asset_section(
            layout, "Meshes", "MESH_DATA",
            [_make_asset("a1", "Rock", "MESH")],
            asset_tags={"a1": []},
        )

        sub_row.label.assert_called_once_with(text="No tags")
        assert sub_row.enabled is False


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
