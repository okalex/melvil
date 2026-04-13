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


# ---------------------------------------------------------------------------
# HitResult
# ---------------------------------------------------------------------------


class TestHitResult:
    def test_fields(self):
        from melvil.ui.gpu_ui import HitResult

        hr = HitResult(
            widget_type="operator",
            id="melvil.test",
            kwargs={"name": "a"},
            rect=(10.0, 20.0, 100.0, 50.0),
        )
        assert hr.widget_type == "operator"
        assert hr.id == "melvil.test"
        assert hr.kwargs == {"name": "a"}
        assert hr.rect == (10.0, 20.0, 100.0, 50.0)


# ---------------------------------------------------------------------------
# GpuPanel
# ---------------------------------------------------------------------------


def _make_panel(**kwargs):
    """Create a GpuPanel with sensible defaults and no draw handler."""
    from melvil.ui.gpu_ui import GpuPanel

    defaults = {"width": 300, "anchor": (0, 200)}
    defaults.update(kwargs)
    return GpuPanel(**defaults)


class TestGpuPanelAttachDetach:
    def setup_method(self):
        import bpy

        bpy.types.SpaceView3D.draw_handler_add.reset_mock()
        bpy.types.SpaceView3D.draw_handler_remove.reset_mock()

    def test_attach_registers_draw_handler(self):
        import bpy

        panel = _make_panel()
        area = MagicMock()
        panel.attach(area)

        bpy.types.SpaceView3D.draw_handler_add.assert_called_once()
        assert panel._handle is not None

    def test_detach_removes_draw_handler(self):
        import bpy

        panel = _make_panel()
        area = MagicMock()
        panel.attach(area)
        panel.detach()

        bpy.types.SpaceView3D.draw_handler_remove.assert_called_once()
        assert panel._handle is None

    def test_detach_clears_state(self):
        panel = _make_panel()
        root = panel.begin_frame()
        root.separator()
        panel.end_frame()

        panel.detach()

        assert panel._root is None
        assert panel._panel_rect is None
        assert len(panel._hit_rects) == 0

    def test_detach_without_attach_is_safe(self):
        panel = _make_panel()
        panel.detach()  # should not raise


class TestGpuPanelFrameCycle:
    def test_begin_frame_returns_gpu_layout(self):
        from melvil.ui.gpu_ui import GpuLayout

        panel = _make_panel()
        root = panel.begin_frame()
        assert isinstance(root, GpuLayout)

    def test_end_frame_does_not_raise_on_empty_tree(self):
        panel = _make_panel()
        panel.begin_frame()
        panel.end_frame()  # should not raise

    def test_end_frame_sets_panel_rect(self):
        panel = _make_panel()
        panel.begin_frame()
        panel.end_frame()
        assert panel._panel_rect is not None

    def test_panel_rect_dimensions(self):
        """Panel rect width = scaled width, height = tree height."""
        panel = _make_panel(width=200, anchor=(10, 100))
        root = panel.begin_frame()
        root.separator()  # adds SEPARATOR_HEIGHT
        panel.end_frame()

        from melvil.ui.gpu_ui import SEPARATOR_HEIGHT

        x, y, w, h = panel._panel_rect
        assert w == pytest.approx(200.0)
        assert h == pytest.approx(SEPARATOR_HEIGHT)
        assert x == pytest.approx(10.0)
        assert y == pytest.approx(100.0 - SEPARATOR_HEIGHT)


class TestGpuPanelHitTest:
    def test_returns_none_on_empty_panel(self):
        panel = _make_panel()
        panel.begin_frame()
        panel.end_frame()
        assert panel.hit_test(50, 50) is None

    def test_returns_matching_hit_result(self):
        from melvil.ui.gpu_ui import HitResult

        panel = _make_panel()
        panel.begin_frame()
        panel._hit_rects.append(
            HitResult("button", "test", {}, (10.0, 10.0, 80.0, 20.0)),
        )
        panel.end_frame()

        result = panel.hit_test(50, 20)
        assert result is not None
        assert result.id == "test"

    def test_returns_none_outside_rect(self):
        from melvil.ui.gpu_ui import HitResult

        panel = _make_panel()
        panel.begin_frame()
        panel._hit_rects.append(
            HitResult("button", "test", {}, (10.0, 10.0, 80.0, 20.0)),
        )
        panel.end_frame()

        assert panel.hit_test(200, 200) is None

    def test_topmost_wins(self):
        from melvil.ui.gpu_ui import HitResult

        panel = _make_panel()
        panel.begin_frame()
        panel._hit_rects.append(
            HitResult("button", "bottom", {}, (0.0, 0.0, 100.0, 100.0)),
        )
        panel._hit_rects.append(
            HitResult("button", "top", {}, (0.0, 0.0, 100.0, 100.0)),
        )
        panel.end_frame()

        result = panel.hit_test(50, 50)
        assert result.id == "top"


class TestGpuPanelIsInside:
    def test_inside(self):
        panel = _make_panel(width=100, anchor=(10, 50))
        root = panel.begin_frame()
        root.separator()
        panel.end_frame()

        from melvil.ui.gpu_ui import SEPARATOR_HEIGHT

        # Panel rect: x=10, y=50-8, w=100, h=8
        assert panel.is_inside(50, 50 - SEPARATOR_HEIGHT + 1) is True

    def test_outside(self):
        panel = _make_panel(width=100, anchor=(10, 50))
        root = panel.begin_frame()
        root.separator()
        panel.end_frame()

        assert panel.is_inside(500, 500) is False

    def test_false_before_end_frame(self):
        panel = _make_panel()
        assert panel.is_inside(0, 0) is False


class TestGpuPanelTexture:
    def test_get_texture_caches(self):
        import bpy

        panel = _make_panel()
        tex_mock = MagicMock()
        import gpu as _gpu

        _gpu.texture.from_image.return_value = tex_mock

        result = panel.get_texture("/fake/path.png")
        assert result is tex_mock

        # Second call returns cached value.
        result2 = panel.get_texture("/fake/path.png")
        assert result2 is tex_mock

    def test_get_texture_returns_none_on_error(self):
        import bpy

        bpy.data.images.load.side_effect = RuntimeError("no file")
        panel = _make_panel()
        assert panel.get_texture("/missing.png") is None
        bpy.data.images.load.side_effect = None  # restore


# ---------------------------------------------------------------------------
# GpuLayout — container methods
# ---------------------------------------------------------------------------


class TestGpuLayoutContainers:
    def test_row_direction(self):
        panel = _make_panel()
        root = panel.begin_frame()
        r = root.row()
        assert r._direction == "ROW"

    def test_column_direction(self):
        panel = _make_panel()
        root = panel.begin_frame()
        c = root.column()
        assert c._direction == "COLUMN"

    def test_split_stores_factor(self):
        panel = _make_panel()
        root = panel.begin_frame()
        sp = root.split(factor=0.3)
        assert sp._direction == "SPLIT"
        assert sp._split_factor == pytest.approx(0.3)

    def test_box_flag(self):
        panel = _make_panel()
        root = panel.begin_frame()
        b = root.box()
        assert b._is_box is True

    def test_separator_appended(self):
        from melvil.ui.gpu_ui import _Separator

        panel = _make_panel()
        root = panel.begin_frame()
        root.separator()
        assert len(root._children) == 1
        assert isinstance(root._children[0], _Separator)

    def test_separator_factor(self):
        from melvil.ui.gpu_ui import _Separator

        panel = _make_panel()
        root = panel.begin_frame()
        root.separator(factor=2.5)
        assert root._children[0].factor == pytest.approx(2.5)

    def test_nested_tree(self):
        panel = _make_panel()
        root = panel.begin_frame()
        row = root.row()
        row.column()
        row.column()
        root.separator()
        root.box()

        assert len(root._children) == 3  # row, sep, box
        assert len(row._children) == 2   # two columns

    def test_grid_flow_direction(self):
        panel = _make_panel()
        root = panel.begin_frame()
        gf = root.grid_flow(columns=3)
        assert gf._direction == "GRID_FLOW"
        assert gf._grid_columns == 3

    def test_row_align(self):
        panel = _make_panel()
        root = panel.begin_frame()
        r = root.row(align=True)
        assert r._align is True

    def test_column_align(self):
        panel = _make_panel()
        root = panel.begin_frame()
        c = root.column(align=True)
        assert c._align is True


# ---------------------------------------------------------------------------
# Layout pass
# ---------------------------------------------------------------------------


class TestLayoutPass:
    def test_column_with_3_separators(self):
        """Total height = 3 × SEPARATOR_HEIGHT × ui_scale."""
        from melvil.ui.gpu_ui import SEPARATOR_HEIGHT

        panel = _make_panel()
        root = panel.begin_frame()
        root.separator()
        root.separator()
        root.separator()

        h = root._measure_height(1.0)
        assert h == pytest.approx(3 * SEPARATOR_HEIGHT)

    def test_column_with_3_separators_scaled(self):
        from melvil.ui.gpu_ui import SEPARATOR_HEIGHT

        panel = _make_panel()
        root = panel.begin_frame()
        root.separator()
        root.separator()
        root.separator()

        h = root._measure_height(2.0)
        assert h == pytest.approx(3 * SEPARATOR_HEIGHT * 2.0)

    def test_row_with_2_children_each_gets_half_width(self):
        panel = _make_panel(width=200, anchor=(0, 100))
        root = panel.begin_frame()
        row = root.row()
        c1 = row.column()
        c1.separator()
        c2 = row.column()
        c2.separator()
        panel.end_frame()

        assert c1._rect is not None
        assert c2._rect is not None

        from melvil.ui.gpu_ui import WIDGET_GAP

        expected_each = (200 - WIDGET_GAP) / 2
        assert c1._rect[2] == pytest.approx(expected_each)
        assert c2._rect[2] == pytest.approx(expected_each)

    def test_split_factor_03(self):
        panel = _make_panel(width=200, anchor=(0, 100))
        root = panel.begin_frame()
        sp = root.split(factor=0.3)
        left = sp.column()
        left.separator()
        right = sp.column()
        right.separator()
        panel.end_frame()

        assert left._rect is not None
        assert right._rect is not None
        assert left._rect[2] == pytest.approx(200.0 * 0.3)
        assert right._rect[2] == pytest.approx(200.0 * 0.7)

    def test_box_adds_padding(self):
        from melvil.ui.gpu_ui import BOX_PAD, SEPARATOR_HEIGHT

        panel = _make_panel(width=200, anchor=(0, 200))
        root = panel.begin_frame()
        bx = root.box()
        bx.separator()
        panel.end_frame()

        # Box rect includes padding on all sides.
        assert bx._rect is not None
        bx_x, bx_y, bx_w, bx_h = bx._rect
        assert bx_w == pytest.approx(200.0)
        assert bx_h == pytest.approx(SEPARATOR_HEIGHT + 2 * BOX_PAD)

    def test_nested_row_in_column_in_split(self):
        """Nested containers produce correct coordinates."""
        from melvil.ui.gpu_ui import SEPARATOR_HEIGHT

        panel = _make_panel(width=400, anchor=(0, 300))
        root = panel.begin_frame()
        sp = root.split(factor=0.5)
        left_col = sp.column()
        r = left_col.row()
        a = r.column()
        a.separator()
        b = r.column()
        b.separator()
        right_col = sp.column()
        right_col.separator()
        panel.end_frame()

        # Left half = 200px wide, row inside splits it.
        assert a._rect is not None
        assert b._rect is not None
        assert right_col._rect is not None
        assert a._rect[2] + b._rect[2] == pytest.approx(
            left_col._rect[2], abs=5,
        )
        assert right_col._rect[2] == pytest.approx(200.0)

    def test_scale_y_doubles_height(self):
        from melvil.ui.gpu_ui import SEPARATOR_HEIGHT

        panel = _make_panel()
        root = panel.begin_frame()
        inner = root.column()
        inner.scale_y = 2.0
        inner.separator()

        h = root._measure_height(1.0)
        assert h == pytest.approx(SEPARATOR_HEIGHT * 2.0)

    def test_empty_layout_height_is_zero(self):
        panel = _make_panel()
        root = panel.begin_frame()
        assert root._measure_height(1.0) == 0.0

    def test_column_widgets_gap(self):
        """Two non-separator children get WIDGET_GAP between them."""
        from melvil.ui.gpu_ui import SEPARATOR_HEIGHT, WIDGET_GAP

        panel = _make_panel()
        root = panel.begin_frame()
        root.column().separator()
        root.column().separator()

        h = root._measure_height(1.0)
        expected = 2 * SEPARATOR_HEIGHT + WIDGET_GAP
        assert h == pytest.approx(expected)

    def test_aligned_column_uses_small_gap(self):
        from melvil.ui.gpu_ui import SEPARATOR_HEIGHT, WIDGET_GAP_ALIGNED

        panel = _make_panel()
        root = panel.begin_frame()
        col = root.column(align=True)
        col.column().separator()
        col.column().separator()

        h = col._measure_height(1.0)
        expected = 2 * SEPARATOR_HEIGHT + WIDGET_GAP_ALIGNED
        assert h == pytest.approx(expected)

    def test_auto_anchor_centers(self):
        """When anchor is None, panel auto-centers in the region."""
        import bpy

        bpy.context.region = MagicMock()
        bpy.context.region.width = 800
        bpy.context.region.height = 600

        from melvil.ui.gpu_ui import GpuPanel, SEPARATOR_HEIGHT

        panel = GpuPanel(width=200, anchor=None)
        root = panel.begin_frame()
        root.separator()
        panel.end_frame()

        px, py, pw, ph = panel._panel_rect
        assert pw == pytest.approx(200.0)
        assert px == pytest.approx((800 - 200) / 2)


# ---------------------------------------------------------------------------
# Draw pass
# ---------------------------------------------------------------------------


class TestDrawPass:
    def test_box_issues_draw_calls(self):
        """Box layout draws rounded rect background + outline."""
        panel = _make_panel(width=200, anchor=(0, 200))
        root = panel.begin_frame()
        bx = root.box()
        bx.separator()
        panel.end_frame()

        # Verify draw_rect_rounded and draw_rect_outline were called by
        # checking the shader mock.
        import gpu as _gpu

        shader = _gpu.shader.from_builtin.return_value
        # The shader was bound and draw was called (box bg + outline).
        assert shader.bind.called

    def test_non_box_container_no_draw(self):
        """Plain column/row containers don't issue draw calls themselves."""
        import gpu as _gpu
        from gpu_extras.batch import batch_for_shader as bf

        shader = _gpu.shader.from_builtin.return_value
        bf.reset_mock()
        shader.reset_mock()

        panel = _make_panel(width=200, anchor=(0, 200))
        root = panel.begin_frame()
        col = root.column()
        col.separator()
        panel.end_frame()

        # Separator and plain column produce no draw calls.
        assert not bf.called

    def test_enabled_false_does_not_prevent_drawing(self):
        """enabled=False doesn't suppress draw for now (dimming deferred)."""
        panel = _make_panel(width=200, anchor=(0, 200))
        root = panel.begin_frame()
        bx = root.box()
        bx.enabled = False
        bx.separator()
        panel.end_frame()

        import gpu as _gpu

        shader = _gpu.shader.from_builtin.return_value
        assert shader.bind.called
