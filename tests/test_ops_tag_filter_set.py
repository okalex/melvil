"""Tests for ops/tag_filter_set.py — BLAMMO_OT_tag_filter_set."""

from __future__ import annotations

from unittest.mock import MagicMock

from blammo.ops.tag_filter_set import BLAMMO_OT_tag_filter_set

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
    op = BLAMMO_OT_tag_filter_set()
    op.tag_id = tag_id
    op.report = MagicMock()
    return op


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


def test_bl_idname():
    assert BLAMMO_OT_tag_filter_set.bl_idname == "blammo.tag_filter_set"


def test_bl_label():
    assert BLAMMO_OT_tag_filter_set.bl_label == "Set Tag Filter"


def test_poll_always_true():
    assert BLAMMO_OT_tag_filter_set.poll(MagicMock()) is True


# ---------------------------------------------------------------------------
# execute()
# ---------------------------------------------------------------------------


def test_empty_tag_id_returns_cancelled():
    op = _make_op("")
    result = op.execute(_make_context())
    assert result == {"CANCELLED"}


def test_whitespace_tag_id_returns_cancelled():
    op = _make_op("   ")
    result = op.execute(_make_context())
    assert result == {"CANCELLED"}


def test_sets_tag_as_sole_active_filter():
    op = _make_op(TAG_A)
    ctx = _make_context(active="")
    op.execute(ctx)
    assert ctx.window_manager.blammo_active_tag_filters == TAG_A


def test_replaces_existing_filter_with_new_tag():
    op = _make_op(TAG_B)
    ctx = _make_context(active=TAG_A)
    op.execute(ctx)
    assert ctx.window_manager.blammo_active_tag_filters == TAG_B


def test_clears_filter_when_sole_active_tag_clicked_again():
    op = _make_op(TAG_A)
    ctx = _make_context(active=TAG_A)
    op.execute(ctx)
    assert ctx.window_manager.blammo_active_tag_filters == ""


def test_replaces_multi_filter_with_single_tag():
    op = _make_op(TAG_A)
    ctx = _make_context(active=f"{TAG_A},{TAG_B}")
    op.execute(ctx)
    assert ctx.window_manager.blammo_active_tag_filters == TAG_A


def test_returns_finished_on_success():
    op = _make_op(TAG_A)
    result = op.execute(_make_context())
    assert result == {"FINISHED"}
