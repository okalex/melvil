"""Tests for ops/tag_filter_toggle.py — BLAMMO_OT_tag_filter_toggle."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from blammo.ops.tag_filter_toggle import (
    BLAMMO_OT_tag_filter_toggle,
    get_active_tag_filters,
    set_active_tag_filters,
)

TAG_A = "aaaaaaaa-0000-4000-8000-000000000001"
TAG_B = "bbbbbbbb-0000-4000-8000-000000000001"


def _make_wm(active=""):
    wm = MagicMock()
    wm.blammo_active_tag_filters = active
    return wm


def _make_context(active=""):
    ctx = MagicMock()
    ctx.window_manager = _make_wm(active)
    return ctx


def _make_op(tag_id=""):
    op = BLAMMO_OT_tag_filter_toggle()
    op.tag_id = tag_id
    return op


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


def test_bl_idname():
    assert BLAMMO_OT_tag_filter_toggle.bl_idname == "blammo.tag_filter_toggle"


def test_poll_always_true():
    assert BLAMMO_OT_tag_filter_toggle.poll(MagicMock()) is True


# ---------------------------------------------------------------------------
# get_active_tag_filters / set_active_tag_filters helpers
# ---------------------------------------------------------------------------


def test_get_active_tag_filters_empty():
    wm = _make_wm("")
    assert get_active_tag_filters(wm) == []


def test_get_active_tag_filters_single():
    wm = _make_wm(TAG_A)
    assert get_active_tag_filters(wm) == [TAG_A]


def test_get_active_tag_filters_multiple():
    wm = _make_wm(f"{TAG_A},{TAG_B}")
    assert get_active_tag_filters(wm) == [TAG_A, TAG_B]


def test_set_active_tag_filters():
    wm = _make_wm()
    set_active_tag_filters(wm, [TAG_A, TAG_B])
    assert wm.blammo_active_tag_filters == f"{TAG_A},{TAG_B}"


# ---------------------------------------------------------------------------
# execute()
# ---------------------------------------------------------------------------


class TestExecute:
    def test_no_tag_id_returns_cancelled(self):
        op = _make_op(tag_id="")
        result = op.execute(_make_context())
        assert result == {"CANCELLED"}

    def test_adds_tag_when_not_active(self):
        op = _make_op(tag_id=TAG_A)
        ctx = _make_context(active="")
        result = op.execute(ctx)
        assert result == {"FINISHED"}
        assert TAG_A in get_active_tag_filters(ctx.window_manager)

    def test_removes_tag_when_already_active(self):
        op = _make_op(tag_id=TAG_A)
        ctx = _make_context(active=TAG_A)
        result = op.execute(ctx)
        assert result == {"FINISHED"}
        assert TAG_A not in get_active_tag_filters(ctx.window_manager)

    def test_toggle_does_not_affect_other_active_tags(self):
        op = _make_op(tag_id=TAG_A)
        ctx = _make_context(active=f"{TAG_A},{TAG_B}")
        op.execute(ctx)
        assert TAG_B in get_active_tag_filters(ctx.window_manager)

    def test_second_toggle_re_adds_tag(self):
        op = _make_op(tag_id=TAG_A)
        ctx = _make_context(active="")
        op.execute(ctx)  # add
        op.execute(ctx)  # remove
        op.execute(ctx)  # add again
        assert TAG_A in get_active_tag_filters(ctx.window_manager)
