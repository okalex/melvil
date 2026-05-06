"""Tests for ops/tag_filter_clear.py — BLAMMO_OT_tag_filter_clear."""

from __future__ import annotations

from unittest.mock import MagicMock

from blammo.ops.tag_filter_toggle import get_active_tag_filters, set_active_tag_filters

TAG_A = "aaaaaaaa-0000-4000-8000-000000000001"
TAG_B = "bbbbbbbb-0000-4000-8000-000000000001"


def _make_context(active=""):
    ctx = MagicMock()
    ctx.window_manager.blammo_active_tag_filters = active
    return ctx


def _make_op():
    from blammo.ops.tag_filter_clear import BLAMMO_OT_tag_filter_clear

    return BLAMMO_OT_tag_filter_clear()


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


def test_bl_idname():
    from blammo.ops.tag_filter_clear import BLAMMO_OT_tag_filter_clear

    assert BLAMMO_OT_tag_filter_clear.bl_idname == "blammo.tag_filter_clear"


def test_bl_options_contains_internal():
    from blammo.ops.tag_filter_clear import BLAMMO_OT_tag_filter_clear

    assert "INTERNAL" in BLAMMO_OT_tag_filter_clear.bl_options


# ---------------------------------------------------------------------------
# poll()
# ---------------------------------------------------------------------------


def test_poll_always_returns_true():
    from blammo.ops.tag_filter_clear import BLAMMO_OT_tag_filter_clear

    assert BLAMMO_OT_tag_filter_clear.poll(MagicMock()) is True


# ---------------------------------------------------------------------------
# execute()
# ---------------------------------------------------------------------------


class TestExecute:
    def test_clears_active_filters(self):
        op = _make_op()
        ctx = _make_context(active=f"{TAG_A},{TAG_B}")
        result = op.execute(ctx)
        assert result == {"FINISHED"}
        assert get_active_tag_filters(ctx.window_manager) == []

    def test_clears_when_already_empty(self):
        op = _make_op()
        ctx = _make_context(active="")
        result = op.execute(ctx)
        assert result == {"FINISHED"}
        assert get_active_tag_filters(ctx.window_manager) == []

    def test_clears_single_active_filter(self):
        op = _make_op()
        ctx = _make_context(active=TAG_A)
        op.execute(ctx)
        assert get_active_tag_filters(ctx.window_manager) == []
