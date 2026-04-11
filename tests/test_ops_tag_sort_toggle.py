"""Tests for ops/tag_sort_toggle.py — MELVIL_OT_tag_sort_toggle."""

from __future__ import annotations

from unittest.mock import MagicMock


def _make_op(sort_by="NAME"):
    from melvil.ops.tag_sort_toggle import MELVIL_OT_tag_sort_toggle

    op = MELVIL_OT_tag_sort_toggle()
    op.sort_by = sort_by
    return op


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


def test_bl_idname():
    from melvil.ops.tag_sort_toggle import MELVIL_OT_tag_sort_toggle

    assert MELVIL_OT_tag_sort_toggle.bl_idname == "melvil.tag_sort_toggle"


def test_bl_options_contains_internal():
    from melvil.ops.tag_sort_toggle import MELVIL_OT_tag_sort_toggle

    assert "INTERNAL" in MELVIL_OT_tag_sort_toggle.bl_options


# ---------------------------------------------------------------------------
# poll()
# ---------------------------------------------------------------------------


def test_poll_always_returns_true():
    from melvil.ops.tag_sort_toggle import MELVIL_OT_tag_sort_toggle

    assert MELVIL_OT_tag_sort_toggle.poll(MagicMock()) is True


# ---------------------------------------------------------------------------
# execute()
# ---------------------------------------------------------------------------


class TestExecute:
    def test_sets_wm_melvil_tag_sort_to_name(self):
        op = _make_op("NAME")
        ctx = MagicMock()
        result = op.execute(ctx)
        assert ctx.window_manager.melvil_tag_sort == "NAME"
        assert result == {"FINISHED"}

    def test_sets_wm_melvil_tag_sort_to_usage(self):
        op = _make_op("USAGE")
        ctx = MagicMock()
        result = op.execute(ctx)
        assert ctx.window_manager.melvil_tag_sort == "USAGE"
        assert result == {"FINISHED"}

    def test_invalid_sort_by_returns_cancelled(self):
        op = _make_op("RANDOM")
        ctx = MagicMock()
        result = op.execute(ctx)
        assert result == {"CANCELLED"}

    def test_invalid_sort_by_does_not_set_wm_property(self):
        op = _make_op("BAD")
        ctx = MagicMock()
        op.execute(ctx)
        assert not hasattr(ctx.window_manager, "melvil_tag_sort") or \
               ctx.window_manager.melvil_tag_sort != "BAD"

    def test_normalises_lowercase_input(self):
        op = _make_op("usage")
        ctx = MagicMock()
        result = op.execute(ctx)
        assert ctx.window_manager.melvil_tag_sort == "USAGE"
        assert result == {"FINISHED"}

    def test_normalises_mixed_case_input(self):
        op = _make_op("Name")
        ctx = MagicMock()
        result = op.execute(ctx)
        assert ctx.window_manager.melvil_tag_sort == "NAME"
        assert result == {"FINISHED"}

    def test_strips_whitespace_from_sort_by(self):
        op = _make_op("  USAGE  ")
        ctx = MagicMock()
        result = op.execute(ctx)
        assert ctx.window_manager.melvil_tag_sort == "USAGE"
        assert result == {"FINISHED"}
