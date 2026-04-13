"""Tests for ui/gpu_ui.py — GPU UI toolkit foundation."""

from __future__ import annotations

import math
import sys
import types
from unittest.mock import MagicMock, call, patch

import pytest


# ---------------------------------------------------------------------------
# ThemeColors
# ---------------------------------------------------------------------------


class TestThemeColorsFallback:
    def test_returns_valid_instance(self):
        from melvil.ui.gpu_ui import ThemeColors

        tc = ThemeColors.fallback()
        assert tc is not None

    def test_all_fields_are_4_element_float_tuples(self):
        from melvil.ui.gpu_ui import ThemeColors

        tc = ThemeColors.fallback()
        for field_name in ThemeColors.__dataclass_fields__:
            value = getattr(tc, field_name)
            assert isinstance(value, tuple), f"{field_name} is not a tuple"
            assert len(value) == 4, f"{field_name} has {len(value)} elements"
            for i, v in enumerate(value):
                assert isinstance(v, float), (
                    f"{field_name}[{i}] = {v!r} is not a float"
                )

    def test_all_values_in_zero_one_range(self):
        from melvil.ui.gpu_ui import ThemeColors

        tc = ThemeColors.fallback()
        for field_name in ThemeColors.__dataclass_fields__:
            value = getattr(tc, field_name)
            for i, v in enumerate(value):
                assert 0.0 <= v <= 1.0, (
                    f"{field_name}[{i}] = {v} out of [0, 1] range"
                )

    def test_text_secondary_is_primary_at_lower_alpha(self):
        from melvil.ui.gpu_ui import ThemeColors

        tc = ThemeColors.fallback()
        assert tc.text_secondary[:3] == tc.text_primary[:3]
        assert tc.text_secondary[3] < tc.text_primary[3]

    def test_text_disabled_is_primary_at_lower_alpha(self):
        from melvil.ui.gpu_ui import ThemeColors

        tc = ThemeColors.fallback()
        assert tc.text_disabled[:3] == tc.text_primary[:3]
        assert tc.text_disabled[3] < tc.text_secondary[3]


class TestThemeColorsFromBlender:
    def _make_mock_ui(self):
        """Build a mock theme UI with wcol_* attributes."""
        ui = MagicMock()

        def _make_wcol(**overrides):
            wcol = MagicMock()
            wcol.inner = overrides.get("inner", (0.2, 0.2, 0.2, 1.0))
            wcol.inner_sel = overrides.get("inner_sel", (0.3, 0.3, 0.3, 1.0))
            wcol.text = overrides.get("text", (0.9, 0.9, 0.9, 1.0))
            wcol.text_sel = overrides.get("text_sel", (1.0, 1.0, 1.0, 1.0))
            wcol.outline = overrides.get("outline", (0.4, 0.4, 0.4, 1.0))
            wcol.item = overrides.get("item", (0.5, 0.5, 0.5, 1.0))
            return wcol

        ui.wcol_regular = _make_wcol(text=(0.88, 0.88, 0.88, 1.0))
        ui.wcol_box = _make_wcol(inner=(0.15, 0.15, 0.15, 0.8))
        ui.wcol_tool = _make_wcol()
        ui.wcol_option = _make_wcol(inner_sel=(0.2, 0.5, 0.8, 1.0))
        ui.wcol_text = _make_wcol()
        ui.wcol_list_item = _make_wcol()
        ui.wcol_scroll = _make_wcol()
        return ui

    def test_produces_correct_rgba_tuples(self):
        import bpy
        from melvil.ui.gpu_ui import ThemeColors

        mock_ui = self._make_mock_ui()
        mock_theme = MagicMock()
        mock_theme.user_interface = mock_ui
        bpy.context.preferences.themes.__getitem__ = MagicMock(
            return_value=mock_theme,
        )

        tc = ThemeColors.from_blender()

        # panel_bg should come from wcol_regular.inner
        assert tc.panel_bg == (0.2, 0.2, 0.2, 1.0)
        # text_primary from wcol_regular.text
        assert tc.text_primary == (0.88, 0.88, 0.88, 1.0)
        # text_secondary is text_primary at 0.6 alpha
        assert tc.text_secondary == (0.88, 0.88, 0.88, 0.6)
        # widget_bg from wcol_tool.inner
        assert tc.widget_bg == (0.2, 0.2, 0.2, 1.0)
        # selection_bg from wcol_list_item.inner_sel
        assert tc.selection_bg == (0.3, 0.3, 0.3, 1.0)

    def test_all_fields_are_4_floats(self):
        import bpy
        from melvil.ui.gpu_ui import ThemeColors

        mock_ui = self._make_mock_ui()
        mock_theme = MagicMock()
        mock_theme.user_interface = mock_ui
        bpy.context.preferences.themes.__getitem__ = MagicMock(
            return_value=mock_theme,
        )

        tc = ThemeColors.from_blender()
        for field_name in ThemeColors.__dataclass_fields__:
            value = getattr(tc, field_name)
            assert isinstance(value, tuple), f"{field_name} is not a tuple"
            assert len(value) == 4, f"{field_name} len={len(value)}"

    def test_panel_header_bg_has_boosted_alpha(self):
        import bpy
        from melvil.ui.gpu_ui import ThemeColors

        mock_ui = self._make_mock_ui()
        mock_theme = MagicMock()
        mock_theme.user_interface = mock_ui
        bpy.context.preferences.themes.__getitem__ = MagicMock(
            return_value=mock_theme,
        )

        tc = ThemeColors.from_blender()
        # wcol_box.inner alpha is 0.8, boosted by 0.1 → 0.9
        assert tc.panel_header_bg[3] == pytest.approx(0.9)


# ---------------------------------------------------------------------------
# DPI helpers
# ---------------------------------------------------------------------------


class TestGetUiScale:
    def test_returns_mocked_value(self):
        import bpy
        from melvil.ui.gpu_ui import get_ui_scale

        bpy.context.preferences.system.ui_scale = 1.5
        assert get_ui_scale() == 1.5
        bpy.context.preferences.system.ui_scale = 1.0  # restore

    def test_returns_1_on_exception(self):
        import bpy
        from melvil.ui.gpu_ui import get_ui_scale

        original = bpy.context.preferences.system.ui_scale
        # Make the attribute access raise
        bpy.context.preferences.system = MagicMock(
            spec=[],  # empty spec → no ui_scale attr
        )
        assert get_ui_scale() == 1.0
        # Restore
        bpy.context.preferences.system = MagicMock()
        bpy.context.preferences.system.ui_scale = original


class TestScaled:
    def test_multiplies_correctly(self):
        from melvil.ui.gpu_ui import scaled

        assert scaled(20, 1.5) == 30.0

    def test_identity_at_scale_1(self):
        from melvil.ui.gpu_ui import scaled

        assert scaled(42, 1.0) == 42.0

    def test_zero_px(self):
        from melvil.ui.gpu_ui import scaled

        assert scaled(0, 2.0) == 0.0


# ---------------------------------------------------------------------------
# Drawing primitives
# ---------------------------------------------------------------------------


class TestDrawRect:
    def test_calls_shader_and_batch(self):
        from melvil.ui.gpu_ui import draw_rect

        draw_rect(10, 20, 100, 50, (1.0, 0.0, 0.0, 1.0))

    def test_draws_with_given_color(self):
        import gpu
        from melvil.ui.gpu_ui import draw_rect, _get_uniform_shader

        shader_mock = _get_uniform_shader()
        shader_mock.uniform_float.reset_mock()

        color = (0.5, 0.5, 0.5, 1.0)
        draw_rect(0, 0, 10, 10, color)

        shader_mock.uniform_float.assert_called_with("color", color)


class TestDrawRectOutline:
    def test_calls_shader_and_batch(self):
        from melvil.ui.gpu_ui import draw_rect_outline

        draw_rect_outline(10, 20, 100, 50, (1.0, 1.0, 1.0, 1.0))

    def test_thickness_parameter_accepted(self):
        from melvil.ui.gpu_ui import draw_rect_outline

        draw_rect_outline(0, 0, 50, 50, (1.0, 1.0, 1.0, 1.0), thickness=2)


class TestDrawRectRounded:
    def test_zero_radius_falls_back_to_plain_rect(self):
        import gpu
        from melvil.ui.gpu_ui import draw_rect_rounded, _get_uniform_shader

        shader_mock = _get_uniform_shader()
        shader_mock.uniform_float.reset_mock()

        color = (1.0, 0.0, 0.0, 1.0)
        draw_rect_rounded(10, 20, 100, 50, 0, color)

        shader_mock.uniform_float.assert_called_with("color", color)

    def test_positive_radius_generates_vertices(self):
        from gpu_extras.batch import batch_for_shader
        from melvil.ui.gpu_ui import draw_rect_rounded

        batch_for_shader.reset_mock()
        draw_rect_rounded(0, 0, 100, 50, 5, (1.0, 1.0, 1.0, 1.0), segments=4)

        # Should have been called to draw the rounded shape.
        assert batch_for_shader.called
        call_args = batch_for_shader.call_args
        verts = call_args[1]["pos"] if "pos" in (call_args[1] or {}) else call_args[0][2]["pos"]
        # 4 corners × (4+1) perimeter verts + 1 centre = 21
        assert len(verts) == 4 * (4 + 1) + 1

    def test_radius_clamped_to_half_shortest_side(self):
        from gpu_extras.batch import batch_for_shader
        from melvil.ui.gpu_ui import draw_rect_rounded

        batch_for_shader.reset_mock()
        # Radius 100 on a 20×10 rect → clamped to 5.
        draw_rect_rounded(0, 0, 20, 10, 100, (1.0, 1.0, 1.0, 1.0))

        assert batch_for_shader.called

    def test_custom_segments(self):
        from gpu_extras.batch import batch_for_shader
        from melvil.ui.gpu_ui import draw_rect_rounded

        batch_for_shader.reset_mock()
        draw_rect_rounded(0, 0, 100, 50, 5, (1.0, 1.0, 1.0, 1.0), segments=8)

        call_args = batch_for_shader.call_args
        verts = call_args[1]["pos"] if "pos" in (call_args[1] or {}) else call_args[0][2]["pos"]
        # 4 corners × (8+1) perimeter verts + 1 centre = 37
        assert len(verts) == 4 * (8 + 1) + 1


class TestDrawTexture:
    def test_calls_image_shader(self):
        from melvil.ui.gpu_ui import draw_texture, _get_image_shader

        shader_mock = _get_image_shader()
        shader_mock.uniform_sampler.reset_mock()

        texture_mock = MagicMock()
        draw_texture(texture_mock, 0, 0, 64, 64)

        shader_mock.uniform_sampler.assert_called_with("image", texture_mock)


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------


class TestDrawText:
    def test_calls_blf_functions(self):
        import blf
        from melvil.ui.gpu_ui import draw_text

        blf.position.reset_mock()
        blf.size.reset_mock()
        blf.color.reset_mock()
        blf.draw.reset_mock()

        draw_text("Hello", 10, 20, 14, (1.0, 1.0, 1.0, 1.0))

        blf.size.assert_called_once_with(0, 14)
        blf.color.assert_called_once_with(0, 1.0, 1.0, 1.0, 1.0)
        blf.position.assert_called_once_with(0, 10, 20, 0)
        blf.draw.assert_called_once_with(0, "Hello")

    def test_returns_measured_width(self):
        import blf
        from melvil.ui.gpu_ui import draw_text

        blf.dimensions = MagicMock(return_value=(72.5, 14.0))
        result = draw_text("test", 0, 0, 12, (1, 1, 1, 1))
        assert result == 72.5


class TestMeasureText:
    def test_calls_blf_dimensions(self):
        import blf
        from melvil.ui.gpu_ui import measure_text

        blf.dimensions = MagicMock(return_value=(55.0, 12.0))
        blf.size.reset_mock()

        w, h = measure_text("test", 11)

        blf.size.assert_called_once_with(0, 11)
        blf.dimensions.assert_called_once_with(0, "test")
        assert w == 55.0
        assert h == 12.0


# ---------------------------------------------------------------------------
# Shader caching
# ---------------------------------------------------------------------------


class TestShaderCaching:
    def test_uniform_shader_cached(self):
        import melvil.ui.gpu_ui as gpu_ui

        gpu_ui._uniform_shader = None  # reset
        s1 = gpu_ui._get_uniform_shader()
        s2 = gpu_ui._get_uniform_shader()
        assert s1 is s2

    def test_image_shader_cached(self):
        import melvil.ui.gpu_ui as gpu_ui

        gpu_ui._image_shader = None  # reset
        s1 = gpu_ui._get_image_shader()
        s2 = gpu_ui._get_image_shader()
        assert s1 is s2


# ---------------------------------------------------------------------------
# color_with_alpha helper
# ---------------------------------------------------------------------------


class TestColorWithAlpha:
    def test_replaces_alpha(self):
        from melvil.ui.gpu_ui import _color_with_alpha

        result = _color_with_alpha((0.5, 0.6, 0.7, 1.0), 0.3)
        assert result == (0.5, 0.6, 0.7, 0.3)


# ---------------------------------------------------------------------------
# Shared theme instance helpers
# ---------------------------------------------------------------------------


class TestGetTheme:
    def setup_method(self):
        import melvil.ui.gpu_ui as gpu_ui

        gpu_ui._theme = None  # ensure clean state

    def teardown_method(self):
        import melvil.ui.gpu_ui as gpu_ui

        gpu_ui._theme = None

    def test_returns_theme_colors(self):
        from melvil.ui.gpu_ui import ThemeColors, get_theme

        result = get_theme()
        assert isinstance(result, ThemeColors)

    def test_caches_result(self):
        from melvil.ui.gpu_ui import get_theme

        first = get_theme()
        second = get_theme()
        assert first is second

    def test_uses_from_blender_when_available(self):
        import melvil.ui.gpu_ui as gpu_ui
        from melvil.ui.gpu_ui import ThemeColors

        sentinel = ThemeColors.fallback()
        with patch.object(ThemeColors, "from_blender", return_value=sentinel) as mock_fb:
            result = gpu_ui.get_theme()
            mock_fb.assert_called_once()
            assert result is sentinel

    def test_falls_back_on_exception(self):
        import melvil.ui.gpu_ui as gpu_ui
        from melvil.ui.gpu_ui import ThemeColors

        with patch.object(ThemeColors, "from_blender", side_effect=RuntimeError):
            result = gpu_ui.get_theme()
            assert isinstance(result, ThemeColors)


class TestResetTheme:
    def test_clears_cached_theme(self):
        import melvil.ui.gpu_ui as gpu_ui
        from melvil.ui.gpu_ui import ThemeColors

        gpu_ui._theme = ThemeColors.fallback()
        gpu_ui.reset_theme()
        assert gpu_ui._theme is None

    def test_next_get_theme_reloads(self):
        import melvil.ui.gpu_ui as gpu_ui
        from melvil.ui.gpu_ui import ThemeColors

        first = gpu_ui.get_theme()
        gpu_ui.reset_theme()

        new_theme = ThemeColors.fallback()
        with patch.object(ThemeColors, "from_blender", return_value=new_theme):
            second = gpu_ui.get_theme()
            assert second is new_theme
            assert second is not first
