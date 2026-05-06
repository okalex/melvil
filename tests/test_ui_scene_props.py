"""Tests for blammo.ui.scene_props callbacks."""

from __future__ import annotations

from unittest.mock import MagicMock

from blammo.ui import scene_props


class TestUpdateBrowserAssetsIndex:
    """Tests for _update_browser_assets_index callback."""

    def _make_wm(self, items, index):
        wm = MagicMock()
        wm.blammo_browser_assets = items
        wm.blammo_browser_assets_index = index
        wm.blammo_selected_asset_id = ""
        return wm

    def test_sets_selected_asset_id(self):
        item = MagicMock()
        item.asset_id = "abc-123"
        wm = self._make_wm([item], 0)

        scene_props._update_browser_assets_index(wm, MagicMock())

        assert wm.blammo_selected_asset_id == "abc-123"

    def test_sets_correct_item_by_index(self):
        items = [MagicMock(asset_id="a"), MagicMock(asset_id="b"), MagicMock(asset_id="c")]
        wm = self._make_wm(items, 2)

        scene_props._update_browser_assets_index(wm, MagicMock())

        assert wm.blammo_selected_asset_id == "c"

    def test_skipped_when_guard_flag_set(self):
        item = MagicMock()
        item.asset_id = "abc-123"
        wm = self._make_wm([item], 0)

        scene_props._rebuilding_browser_assets = True
        try:
            scene_props._update_browser_assets_index(wm, MagicMock())
        finally:
            scene_props._rebuilding_browser_assets = False

        assert wm.blammo_selected_asset_id == ""

    def test_negative_index_ignored(self):
        wm = self._make_wm([], -1)

        scene_props._update_browser_assets_index(wm, MagicMock())

        assert wm.blammo_selected_asset_id == ""

    def test_out_of_range_index_ignored(self):
        item = MagicMock(asset_id="a")
        wm = self._make_wm([item], 5)

        scene_props._update_browser_assets_index(wm, MagicMock())

        assert wm.blammo_selected_asset_id == ""
