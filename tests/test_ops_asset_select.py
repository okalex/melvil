"""Tests for ops/asset_select.py — MELVIL_OT_asset_select."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from melvil.ops.asset_select import MELVIL_OT_asset_select

_ASSET_A = "aaaaaaaa-0000-4000-8000-000000000001"
_ASSET_B = "bbbbbbbb-0000-4000-8000-000000000002"


def _make_op(asset_id=""):
    op = MELVIL_OT_asset_select()
    op.asset_id = asset_id
    return op


def _make_ctx(selected=""):
    ctx = MagicMock()
    ctx.window_manager.melvil_selected_asset_id = selected
    return ctx


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


def test_bl_idname():
    assert MELVIL_OT_asset_select.bl_idname == "melvil.asset_select"


def test_bl_label():
    assert MELVIL_OT_asset_select.bl_label == "Asset Details"


# ---------------------------------------------------------------------------
# poll()
# ---------------------------------------------------------------------------


def test_poll_always_true():
    assert MELVIL_OT_asset_select.poll(MagicMock()) is True


# ---------------------------------------------------------------------------
# execute()
# ---------------------------------------------------------------------------


def test_execute_empty_asset_id_returns_cancelled():
    op = _make_op(asset_id="")
    result = op.execute(_make_ctx())
    assert result == {"CANCELLED"}


def test_execute_whitespace_asset_id_returns_cancelled():
    op = _make_op(asset_id="   ")
    result = op.execute(_make_ctx())
    assert result == {"CANCELLED"}


def test_execute_selects_asset_when_none_selected():
    op = _make_op(asset_id=_ASSET_A)
    ctx = _make_ctx(selected="")
    result = op.execute(ctx)
    assert result == {"FINISHED"}
    assert ctx.window_manager.melvil_selected_asset_id == _ASSET_A


def test_execute_selects_asset_when_different_selected():
    op = _make_op(asset_id=_ASSET_A)
    ctx = _make_ctx(selected=_ASSET_B)
    op.execute(ctx)
    assert ctx.window_manager.melvil_selected_asset_id == _ASSET_A


def test_execute_deselects_asset_when_same_already_selected():
    op = _make_op(asset_id=_ASSET_A)
    ctx = _make_ctx(selected=_ASSET_A)
    result = op.execute(ctx)
    assert result == {"FINISHED"}
    assert ctx.window_manager.melvil_selected_asset_id == ""


def test_execute_strips_whitespace_from_asset_id():
    op = _make_op(asset_id=f"  {_ASSET_A}  ")
    ctx = _make_ctx(selected="")
    op.execute(ctx)
    assert ctx.window_manager.melvil_selected_asset_id == _ASSET_A
