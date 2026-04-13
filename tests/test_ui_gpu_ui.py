"""Tests for ui/gpu/ — GPU UI toolkit foundation."""

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
        from melvil.ui.gpu import ThemeColors

        tc = ThemeColors.fallback()
        assert tc is not None

    def test_all_fields_are_4_element_float_tuples(self):
        from melvil.ui.gpu import ThemeColors

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
        from melvil.ui.gpu import ThemeColors

        tc = ThemeColors.fallback()
        for field_name in ThemeColors.__dataclass_fields__:
            value = getattr(tc, field_name)
            for i, v in enumerate(value):
                assert 0.0 <= v <= 1.0, (
                    f"{field_name}[{i}] = {v} out of [0, 1] range"
                )

    def test_text_secondary_is_primary_at_lower_alpha(self):
        from melvil.ui.gpu import ThemeColors

        tc = ThemeColors.fallback()
        assert tc.text_secondary[:3] == tc.text_primary[:3]
        assert tc.text_secondary[3] < tc.text_primary[3]

    def test_text_disabled_is_primary_at_lower_alpha(self):
        from melvil.ui.gpu import ThemeColors

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
        ui.wcol_menu_back = _make_wcol(inner=(0.16, 0.16, 0.16, 1.0))
        ui.wcol_box = _make_wcol(inner=(0.15, 0.15, 0.15, 0.8))
        ui.wcol_tool = _make_wcol()
        ui.wcol_option = _make_wcol(inner_sel=(0.2, 0.5, 0.8, 1.0))
        ui.wcol_text = _make_wcol()
        ui.wcol_list_item = _make_wcol()
        ui.wcol_scroll = _make_wcol()
        return ui

    def test_produces_correct_rgba_tuples(self):
        import bpy
        from melvil.ui.gpu import ThemeColors

        mock_ui = self._make_mock_ui()
        mock_theme = MagicMock()
        mock_theme.user_interface = mock_ui
        bpy.context.preferences.themes.__getitem__ = MagicMock(
            return_value=mock_theme,
        )

        tc = ThemeColors.from_blender()

        # panel_bg should come from wcol_menu_back.inner
        assert tc.panel_bg == (0.16, 0.16, 0.16, 1.0)
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
        from melvil.ui.gpu import ThemeColors

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
        from melvil.ui.gpu import ThemeColors

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
        from melvil.ui.gpu import get_ui_scale

        bpy.context.preferences.system.ui_scale = 1.5
        assert get_ui_scale() == 1.5
        bpy.context.preferences.system.ui_scale = 1.0  # restore

    def test_returns_1_on_exception(self):
        import bpy
        from melvil.ui.gpu import get_ui_scale

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
        from melvil.ui.gpu import scaled

        assert scaled(20, 1.5) == 30.0

    def test_identity_at_scale_1(self):
        from melvil.ui.gpu import scaled

        assert scaled(42, 1.0) == 42.0

    def test_zero_px(self):
        from melvil.ui.gpu import scaled

        assert scaled(0, 2.0) == 0.0


# ---------------------------------------------------------------------------
# Drawing primitives
# ---------------------------------------------------------------------------


class TestDrawRect:
    def test_calls_shader_and_batch(self):
        from melvil.ui.gpu import draw_rect

        draw_rect(10, 20, 100, 50, (1.0, 0.0, 0.0, 1.0))

    def test_draws_with_given_color(self):
        import gpu
        from melvil.ui.gpu import draw_rect, _get_uniform_shader

        shader_mock = _get_uniform_shader()
        shader_mock.uniform_float.reset_mock()

        color = (0.5, 0.5, 0.5, 1.0)
        draw_rect(0, 0, 10, 10, color)

        shader_mock.uniform_float.assert_called_with("color", color)


class TestDrawRectOutline:
    def test_calls_shader_and_batch(self):
        from melvil.ui.gpu import draw_rect_outline

        draw_rect_outline(10, 20, 100, 50, (1.0, 1.0, 1.0, 1.0))

    def test_thickness_parameter_accepted(self):
        from melvil.ui.gpu import draw_rect_outline

        draw_rect_outline(0, 0, 50, 50, (1.0, 1.0, 1.0, 1.0), thickness=2)


class TestDrawRectRounded:
    def test_zero_radius_falls_back_to_plain_rect(self):
        import gpu
        from melvil.ui.gpu import draw_rect_rounded, _get_uniform_shader

        shader_mock = _get_uniform_shader()
        shader_mock.uniform_float.reset_mock()

        color = (1.0, 0.0, 0.0, 1.0)
        draw_rect_rounded(10, 20, 100, 50, 0, color)

        shader_mock.uniform_float.assert_called_with("color", color)

    def test_positive_radius_generates_vertices(self):
        from gpu_extras.batch import batch_for_shader
        from melvil.ui.gpu import draw_rect_rounded

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
        from melvil.ui.gpu import draw_rect_rounded

        batch_for_shader.reset_mock()
        # Radius 100 on a 20×10 rect → clamped to 5.
        draw_rect_rounded(0, 0, 20, 10, 100, (1.0, 1.0, 1.0, 1.0))

        assert batch_for_shader.called

    def test_custom_segments(self):
        from gpu_extras.batch import batch_for_shader
        from melvil.ui.gpu import draw_rect_rounded

        batch_for_shader.reset_mock()
        draw_rect_rounded(0, 0, 100, 50, 5, (1.0, 1.0, 1.0, 1.0), segments=8)

        call_args = batch_for_shader.call_args
        verts = call_args[1]["pos"] if "pos" in (call_args[1] or {}) else call_args[0][2]["pos"]
        # 4 corners × (8+1) perimeter verts + 1 centre = 37
        assert len(verts) == 4 * (8 + 1) + 1


class TestDrawTexture:
    def test_calls_image_shader(self):
        from melvil.ui.gpu import draw_texture, _get_image_shader

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
        from melvil.ui.gpu import draw_text

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
        from melvil.ui.gpu import draw_text

        blf.dimensions = MagicMock(return_value=(72.5, 14.0))
        result = draw_text("test", 0, 0, 12, (1, 1, 1, 1))
        assert result == 72.5


class TestMeasureText:
    def test_calls_blf_dimensions(self):
        import blf
        from melvil.ui.gpu import measure_text

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
        import melvil.ui.gpu.drawing as gpu_drawing

        gpu_drawing._uniform_shader = None  # reset
        s1 = gpu_drawing._get_uniform_shader()
        s2 = gpu_drawing._get_uniform_shader()
        assert s1 is s2

    def test_image_shader_cached(self):
        import melvil.ui.gpu.drawing as gpu_drawing

        gpu_drawing._image_shader = None  # reset
        s1 = gpu_drawing._get_image_shader()
        s2 = gpu_drawing._get_image_shader()
        assert s1 is s2


# ---------------------------------------------------------------------------
# color_with_alpha helper
# ---------------------------------------------------------------------------


class TestColorWithAlpha:
    def test_replaces_alpha(self):
        from melvil.ui.gpu import _color_with_alpha

        result = _color_with_alpha((0.5, 0.6, 0.7, 1.0), 0.3)
        assert result == (0.5, 0.6, 0.7, 0.3)


# ---------------------------------------------------------------------------
# Shared theme instance helpers
# ---------------------------------------------------------------------------


class TestGetTheme:
    def setup_method(self):
        import melvil.ui.gpu.theme as gpu_theme

        gpu_theme._theme = None  # ensure clean state

    def teardown_method(self):
        import melvil.ui.gpu.theme as gpu_theme

        gpu_theme._theme = None

    def test_returns_theme_colors(self):
        from melvil.ui.gpu import ThemeColors, get_theme

        result = get_theme()
        assert isinstance(result, ThemeColors)

    def test_caches_result(self):
        from melvil.ui.gpu import get_theme

        first = get_theme()
        second = get_theme()
        assert first is second

    def test_uses_from_blender_when_available(self):
        import melvil.ui.gpu.theme as gpu_theme
        from melvil.ui.gpu import ThemeColors

        sentinel = ThemeColors.fallback()
        with patch.object(ThemeColors, "from_blender", return_value=sentinel) as mock_fb:
            result = gpu_theme.get_theme()
            mock_fb.assert_called_once()
            assert result is sentinel

    def test_falls_back_on_exception(self):
        import melvil.ui.gpu.theme as gpu_theme
        from melvil.ui.gpu import ThemeColors

        with patch.object(ThemeColors, "from_blender", side_effect=RuntimeError):
            result = gpu_theme.get_theme()
            assert isinstance(result, ThemeColors)


class TestResetTheme:
    def test_clears_cached_theme(self):
        import melvil.ui.gpu.theme as gpu_theme
        from melvil.ui.gpu import ThemeColors

        gpu_theme._theme = ThemeColors.fallback()
        gpu_theme.reset_theme()
        assert gpu_theme._theme is None

    def test_next_get_theme_reloads(self):
        import melvil.ui.gpu.theme as gpu_theme
        from melvil.ui.gpu import ThemeColors

        first = gpu_theme.get_theme()
        gpu_theme.reset_theme()

        new_theme = ThemeColors.fallback()
        with patch.object(ThemeColors, "from_blender", return_value=new_theme):
            second = gpu_theme.get_theme()
            assert second is new_theme
            assert second is not first


# ---------------------------------------------------------------------------
# HitResult
# ---------------------------------------------------------------------------


class TestHitResult:
    def test_fields(self):
        from melvil.ui.gpu import HitResult

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
    from melvil.ui.gpu import GpuPanel

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
        from melvil.ui.gpu import GpuLayout

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

        from melvil.ui.gpu import SEPARATOR_HEIGHT

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
        from melvil.ui.gpu import HitResult

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
        from melvil.ui.gpu import HitResult

        panel = _make_panel()
        panel.begin_frame()
        panel._hit_rects.append(
            HitResult("button", "test", {}, (10.0, 10.0, 80.0, 20.0)),
        )
        panel.end_frame()

        assert panel.hit_test(200, 200) is None

    def test_topmost_wins(self):
        from melvil.ui.gpu import HitResult

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

        from melvil.ui.gpu import SEPARATOR_HEIGHT

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
        from melvil.ui.gpu import GpuSeparator

        panel = _make_panel()
        root = panel.begin_frame()
        root.separator()
        assert len(root._children) == 1
        assert isinstance(root._children[0], GpuSeparator)

    def test_separator_factor(self):
        from melvil.ui.gpu import GpuSeparator

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
        from melvil.ui.gpu import SEPARATOR_HEIGHT

        panel = _make_panel()
        root = panel.begin_frame()
        root.separator()
        root.separator()
        root.separator()

        h = root._measure_height(1.0)
        assert h == pytest.approx(3 * SEPARATOR_HEIGHT)

    def test_column_with_3_separators_scaled(self):
        from melvil.ui.gpu import SEPARATOR_HEIGHT

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

        from melvil.ui.gpu import WIDGET_GAP

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
        from melvil.ui.gpu import BOX_PAD, SEPARATOR_HEIGHT

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
        from melvil.ui.gpu import SEPARATOR_HEIGHT

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
        from melvil.ui.gpu import SEPARATOR_HEIGHT

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
        from melvil.ui.gpu import SEPARATOR_HEIGHT, WIDGET_GAP

        panel = _make_panel()
        root = panel.begin_frame()
        root.column().separator()
        root.column().separator()

        h = root._measure_height(1.0)
        expected = 2 * SEPARATOR_HEIGHT + WIDGET_GAP
        assert h == pytest.approx(expected)

    def test_aligned_column_uses_small_gap(self):
        from melvil.ui.gpu import SEPARATOR_HEIGHT, WIDGET_GAP_ALIGNED

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

        from melvil.ui.gpu import GpuPanel, SEPARATOR_HEIGHT

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

    def test_non_box_container_no_extra_draw(self):
        """Plain column/row containers don't issue draw calls themselves.

        The panel background draws (rounded rect + outline), but the
        inner column and separator produce no additional draw calls.
        """
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

        # Panel background issues draw calls (rounded rect + outline).
        # Record how many calls the panel bg made, then verify no
        # additional calls came from the column or separator.
        bg_calls = bf.call_count
        assert bg_calls > 0  # panel background was drawn

        # A second identical panel should produce the same call count
        # (no extra draws from col/separator).
        bf.reset_mock()
        root2 = panel.begin_frame()
        root2.column()  # empty column, no separator
        panel.end_frame()
        assert bf.call_count == bg_calls

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


# ---------------------------------------------------------------------------
# GpuWidget
# ---------------------------------------------------------------------------


class TestGpuWidget:
    def test_label_fields(self):
        from melvil.ui.gpu import GpuLabel

        w = GpuLabel(text="Hello", icon="MESH_DATA")
        assert w.text == "Hello"
        assert w.icon == "MESH_DATA"
        assert w.enabled is True
        assert w.alert is False
        assert w.rect is None

    def test_separator_fields(self):
        from melvil.ui.gpu import GpuSeparator

        w = GpuSeparator(factor=2.0)
        assert w.factor == 2.0
        assert w.is_separator is True

    def test_defaults(self):
        from melvil.ui.gpu import GpuLabel

        w = GpuLabel()
        assert w.text == ""
        assert w.icon == "NONE"
        assert w.enabled is True
        assert w.alert is False


# ---------------------------------------------------------------------------
# GpuLayout.label()
# ---------------------------------------------------------------------------


class TestGpuLayoutLabel:
    def test_label_appends_widget(self):
        from melvil.ui.gpu import GpuLabel

        panel = _make_panel()
        root = panel.begin_frame()
        root.label(text="Hello")

        assert len(root._children) == 1
        child = root._children[0]
        assert isinstance(child, GpuLabel)
        assert child.text == "Hello"

    def test_label_icon(self):
        from melvil.ui.gpu import GpuLabel

        panel = _make_panel()
        root = panel.begin_frame()
        root.label(text="Test", icon="MESH_DATA")

        child = root._children[0]
        assert child.icon == "MESH_DATA"

    def test_label_inherits_enabled(self):
        panel = _make_panel()
        root = panel.begin_frame()
        root.enabled = False
        root.label(text="Disabled")

        child = root._children[0]
        assert child.enabled is False

    def test_label_inherits_alert(self):
        panel = _make_panel()
        root = panel.begin_frame()
        root.alert = True
        root.label(text="Alert!")

        child = root._children[0]
        assert child.alert is True

    def test_empty_text_label(self):
        panel = _make_panel()
        root = panel.begin_frame()
        root.label()

        child = root._children[0]
        assert child.text == ""

    def test_label_height_matches_widget_height(self):
        from melvil.ui.gpu import WIDGET_HEIGHT

        panel = _make_panel()
        root = panel.begin_frame()
        root.label(text="Hello")

        h = root._measure_height(1.0)
        assert h == pytest.approx(WIDGET_HEIGHT)

    def test_label_height_scaled(self):
        from melvil.ui.gpu import WIDGET_HEIGHT

        panel = _make_panel()
        root = panel.begin_frame()
        root.label(text="Hello")

        h = root._measure_height(2.0)
        assert h == pytest.approx(WIDGET_HEIGHT * 2.0)

    def test_label_gets_rect_after_position(self):
        panel = _make_panel(width=200, anchor=(0, 200))
        root = panel.begin_frame()
        root.label(text="Hello")
        panel.end_frame()

        child = root._children[0]
        assert child.rect is not None
        x, y, w, h = child.rect
        assert w == pytest.approx(200.0)

    def test_multiple_labels_stacked(self):
        from melvil.ui.gpu import WIDGET_HEIGHT, WIDGET_GAP

        panel = _make_panel()
        root = panel.begin_frame()
        root.label(text="A")
        root.label(text="B")

        h = root._measure_height(1.0)
        assert h == pytest.approx(2 * WIDGET_HEIGHT + WIDGET_GAP)

    def test_label_separator_label(self):
        from melvil.ui.gpu import WIDGET_HEIGHT, SEPARATOR_HEIGHT

        panel = _make_panel()
        root = panel.begin_frame()
        root.label(text="A")
        root.separator()
        root.label(text="B")

        # No gap adjacent to separators.
        h = root._measure_height(1.0)
        assert h == pytest.approx(2 * WIDGET_HEIGHT + SEPARATOR_HEIGHT)


# ---------------------------------------------------------------------------
# Label drawing
# ---------------------------------------------------------------------------


class TestLabelDraw:
    def test_label_calls_draw_text(self):
        import blf

        blf.draw.reset_mock()
        blf.dimensions = MagicMock(return_value=(40.0, 12.0))

        panel = _make_panel(width=200, anchor=(0, 200))
        root = panel.begin_frame()
        root.label(text="Hello World")
        panel.end_frame()

        blf.draw.assert_called()
        # The text drawn should be "Hello World".
        drawn_texts = [c.args[1] for c in blf.draw.call_args_list]
        assert "Hello World" in drawn_texts

    def test_empty_label_no_text_draw(self):
        import blf

        blf.draw.reset_mock()

        panel = _make_panel(width=200, anchor=(0, 200))
        root = panel.begin_frame()
        root.label()  # empty text
        panel.end_frame()

        # Empty label should not call blf.draw for empty string.
        drawn_texts = [c.args[1] for c in blf.draw.call_args_list]
        assert "" not in drawn_texts

    def test_disabled_label_uses_disabled_color(self):
        import blf
        from melvil.ui.gpu import get_theme

        blf.color.reset_mock()
        blf.dimensions = MagicMock(return_value=(40.0, 12.0))

        panel = _make_panel(width=200, anchor=(0, 200))
        root = panel.begin_frame()
        root.enabled = False
        root.label(text="Dim")
        panel.end_frame()

        theme = get_theme()
        color_calls = [c.args[1:] for c in blf.color.call_args_list]
        assert theme.text_disabled in color_calls

    def test_alert_label_uses_alert_color(self):
        import blf
        from melvil.ui.gpu import get_theme

        blf.color.reset_mock()
        blf.dimensions = MagicMock(return_value=(40.0, 12.0))

        panel = _make_panel(width=200, anchor=(0, 200))
        root = panel.begin_frame()
        root.alert = True
        root.label(text="Alert!")
        panel.end_frame()

        theme = get_theme()
        color_calls = [c.args[1:] for c in blf.color.call_args_list]
        assert theme.alert in color_calls

    def test_label_in_disabled_parent(self):
        """A label inside a disabled parent layout uses disabled color."""
        import blf
        from melvil.ui.gpu import get_theme

        blf.color.reset_mock()
        blf.dimensions = MagicMock(return_value=(40.0, 12.0))

        panel = _make_panel(width=200, anchor=(0, 200))
        root = panel.begin_frame()
        col = root.column()
        col.enabled = False
        col.label(text="Disabled child")
        panel.end_frame()

        theme = get_theme()
        color_calls = [c.args[1:] for c in blf.color.call_args_list]
        assert theme.text_disabled in color_calls


# ---------------------------------------------------------------------------
# Separator with label interop
# ---------------------------------------------------------------------------


class TestSeparatorGapLogic:
    def test_separator_between_labels_no_extra_gap(self):
        """Separator between two labels should not add WIDGET_GAP."""
        from melvil.ui.gpu import WIDGET_HEIGHT, SEPARATOR_HEIGHT

        panel = _make_panel()
        root = panel.begin_frame()
        root.label(text="A")
        root.separator()
        root.label(text="B")

        h = root._measure_height(1.0)
        assert h == pytest.approx(2 * WIDGET_HEIGHT + SEPARATOR_HEIGHT)

    def test_label_then_container_gets_gap(self):
        """A label followed by a column gets WIDGET_GAP between them."""
        from melvil.ui.gpu import WIDGET_HEIGHT, SEPARATOR_HEIGHT, WIDGET_GAP

        panel = _make_panel()
        root = panel.begin_frame()
        root.label(text="A")
        col = root.column()
        col.separator()

        h = root._measure_height(1.0)
        assert h == pytest.approx(WIDGET_HEIGHT + WIDGET_GAP + SEPARATOR_HEIGHT)

    def test_label_in_row(self):
        """Labels placed in a row share width equally."""
        from melvil.ui.gpu import WIDGET_HEIGHT, WIDGET_GAP

        panel = _make_panel(width=200, anchor=(0, 200))
        root = panel.begin_frame()
        row = root.row()
        row.label(text="Left")
        row.label(text="Right")
        panel.end_frame()

        left = row._children[0]
        right = row._children[1]
        assert left.rect is not None
        assert right.rect is not None

        expected_each = (200 - WIDGET_GAP) / 2
        assert left.rect[2] == pytest.approx(expected_each)
        assert right.rect[2] == pytest.approx(expected_each)


# ---------------------------------------------------------------------------
# GpuOperatorProps
# ---------------------------------------------------------------------------


class TestGpuOperatorProps:
    def test_set_and_get(self):
        from melvil.ui.gpu import GpuOperatorProps

        op = GpuOperatorProps()
        op.asset_id = "abc"
        assert op.asset_id == "abc"

    def test_get_missing_returns_none(self):
        from melvil.ui.gpu import GpuOperatorProps

        op = GpuOperatorProps()
        assert op.nonexistent is None

    def test_internal_attrs_use_normal_setattr(self):
        from melvil.ui.gpu import GpuOperatorProps

        op = GpuOperatorProps()
        assert isinstance(op._props, dict)

    def test_internal_attrs_raise_on_missing(self):
        from melvil.ui.gpu import GpuOperatorProps

        op = GpuOperatorProps()
        with pytest.raises(AttributeError):
            _ = op._nonexistent

    def test_multiple_props(self):
        from melvil.ui.gpu import GpuOperatorProps

        op = GpuOperatorProps()
        op.asset_id = "abc"
        op.kit_id = "xyz"
        op.count = 42
        assert op._props == {"asset_id": "abc", "kit_id": "xyz", "count": 42}


# ---------------------------------------------------------------------------
# GpuButton — construction
# ---------------------------------------------------------------------------


class TestGpuButton:
    def test_operator_appends_button(self):
        from melvil.ui.gpu import GpuButton

        panel = _make_panel()
        root = panel.begin_frame()
        root.operator("melvil.load_asset", text="Load")

        assert len(root._children) == 1
        child = root._children[0]
        assert isinstance(child, GpuButton)
        assert child.text == "Load"
        assert child.operator_id == "melvil.load_asset"

    def test_operator_returns_props(self):
        from melvil.ui.gpu import GpuOperatorProps

        panel = _make_panel()
        root = panel.begin_frame()
        props = root.operator("melvil.test_op", text="Test")

        assert isinstance(props, GpuOperatorProps)

    def test_operator_props_stored_on_button(self):
        from melvil.ui.gpu import GpuButton

        panel = _make_panel()
        root = panel.begin_frame()
        props = root.operator("melvil.test_op", text="")
        props.asset_id = "abc"

        child = root._children[0]
        assert child.operator_props is props
        assert child.operator_props._props == {"asset_id": "abc"}

    def test_button_inherits_enabled(self):
        panel = _make_panel()
        root = panel.begin_frame()
        root.enabled = False
        root.operator("melvil.test_op", text="Disabled")

        child = root._children[0]
        assert child.enabled is False

    def test_button_inherits_alert(self):
        panel = _make_panel()
        root = panel.begin_frame()
        root.alert = True
        root.operator("melvil.test_op", text="Alert!")

        child = root._children[0]
        assert child.alert is True

    def test_button_emboss_default(self):
        from melvil.ui.gpu import GpuButton

        panel = _make_panel()
        root = panel.begin_frame()
        root.operator("melvil.test_op", text="", emboss=True)

        child = root._children[0]
        assert child.emboss is True

    def test_button_no_emboss(self):
        panel = _make_panel()
        root = panel.begin_frame()
        root.operator("melvil.test_op", text="", emboss=False)

        child = root._children[0]
        assert child.emboss is False

    def test_button_depress(self):
        panel = _make_panel()
        root = panel.begin_frame()
        root.operator("melvil.test_op", text="", depress=True)

        child = root._children[0]
        assert child.depress is True

    def test_button_height_matches_widget_height(self):
        from melvil.ui.gpu import WIDGET_HEIGHT

        panel = _make_panel()
        root = panel.begin_frame()
        root.operator("melvil.test_op", text="Click")

        h = root._measure_height(1.0)
        assert h == pytest.approx(WIDGET_HEIGHT)

    def test_button_gets_rect_after_position(self):
        panel = _make_panel(width=200, anchor=(0, 200))
        root = panel.begin_frame()
        root.operator("melvil.test_op", text="Click")
        panel.end_frame()

        child = root._children[0]
        assert child.rect is not None
        x, y, w, h = child.rect
        assert w == pytest.approx(200.0)

    def test_icon_stored(self):
        panel = _make_panel()
        root = panel.begin_frame()
        root.operator("melvil.test_op", text="", icon="ADD")

        child = root._children[0]
        assert child.icon == "ADD"


# ---------------------------------------------------------------------------
# GpuButton — drawing
# ---------------------------------------------------------------------------


class TestGpuButtonDraw:
    def test_embossed_button_draws_background(self):
        """Embossed button issues draw_rect_rounded + draw_rect_outline."""
        from gpu_extras.batch import batch_for_shader as bf

        bf.reset_mock()

        panel = _make_panel(width=200, anchor=(0, 200))
        root = panel.begin_frame()
        root.operator("melvil.test_op", text="Click")
        panel.end_frame()

        # At minimum, the panel background + button background were drawn.
        assert bf.call_count >= 3  # panel bg + button bg + outlines

    def test_unembossed_button_no_idle_background(self):
        """Unembossed button without hover draws no button background.

        Panel background drawing is still expected.
        """
        from gpu_extras.batch import batch_for_shader as bf

        # Baseline: measure panel background draw calls with no children.
        panel = _make_panel(width=200, anchor=(0, 200))
        root = panel.begin_frame()
        root.separator()
        panel.end_frame()
        bf.reset_mock()
        root2 = panel.begin_frame()
        root2.separator()
        panel.end_frame()
        baseline = bf.call_count

        # Now with an unembossed button (not hovered).
        bf.reset_mock()
        root3 = panel.begin_frame()
        root3.operator("melvil.test_op", text="Click", emboss=False)
        panel.end_frame()
        assert bf.call_count == baseline  # no extra draws

    def test_depress_button_uses_active_bg(self):
        """Depressed button draws with widget_bg_active color."""
        import gpu as _gpu
        from melvil.ui.gpu import get_theme

        shader = _gpu.shader.from_builtin.return_value

        panel = _make_panel(width=200, anchor=(0, 200))
        root = panel.begin_frame()
        root.operator("melvil.test_op", text="Click", depress=True)
        panel.end_frame()

        theme = get_theme()
        color_calls = [
            c.args[1] for c in shader.uniform_float.call_args_list
            if c.args[0] == "color"
        ]
        assert theme.widget_bg_active in color_calls

    def test_button_text_drawn(self):
        """Button with text calls blf.draw."""
        import blf

        blf.draw.reset_mock()
        blf.dimensions = MagicMock(return_value=(40.0, 12.0))

        panel = _make_panel(width=200, anchor=(0, 200))
        root = panel.begin_frame()
        root.operator("melvil.test_op", text="Click Me")
        panel.end_frame()

        drawn_texts = [c.args[1] for c in blf.draw.call_args_list]
        assert "Click Me" in drawn_texts

    def test_empty_text_no_text_draw(self):
        """Button with empty text doesn't call blf.draw for empty string."""
        import blf

        blf.draw.reset_mock()

        panel = _make_panel(width=200, anchor=(0, 200))
        root = panel.begin_frame()
        root.operator("melvil.test_op", text="")
        panel.end_frame()

        drawn_texts = [c.args[1] for c in blf.draw.call_args_list]
        assert "" not in drawn_texts

    def test_disabled_button_uses_disabled_color(self):
        """Disabled button uses text_disabled color."""
        import blf
        from melvil.ui.gpu import get_theme

        blf.color.reset_mock()
        blf.dimensions = MagicMock(return_value=(40.0, 12.0))

        panel = _make_panel(width=200, anchor=(0, 200))
        root = panel.begin_frame()
        root.enabled = False
        root.operator("melvil.test_op", text="Disabled")
        panel.end_frame()

        theme = get_theme()
        color_calls = [c.args[1:] for c in blf.color.call_args_list]
        assert theme.text_disabled in color_calls

    def test_alert_button_uses_alert_color(self):
        """Alert button uses alert text color."""
        import blf
        from melvil.ui.gpu import get_theme

        blf.color.reset_mock()
        blf.dimensions = MagicMock(return_value=(40.0, 12.0))

        panel = _make_panel(width=200, anchor=(0, 200))
        root = panel.begin_frame()
        root.alert = True
        root.operator("melvil.test_op", text="Delete")
        panel.end_frame()

        theme = get_theme()
        color_calls = [c.args[1:] for c in blf.color.call_args_list]
        assert theme.alert in color_calls


# ---------------------------------------------------------------------------
# GpuButton — hit-rect registration
# ---------------------------------------------------------------------------


class TestGpuButtonHitRect:
    def test_enabled_button_registers_hit_rect(self):
        panel = _make_panel(width=200, anchor=(0, 200))
        root = panel.begin_frame()
        root.operator("melvil.test_op", text="Click")
        panel.end_frame()

        assert len(panel._hit_rects) == 1
        hr = panel._hit_rects[0]
        assert hr.widget_type == "operator"
        assert hr.id == "melvil.test_op"

    def test_hit_rect_stores_operator_kwargs(self):
        panel = _make_panel(width=200, anchor=(0, 200))
        root = panel.begin_frame()
        op = root.operator("melvil.test_op", text="Click")
        op.asset_id = "abc"
        op.count = 5
        panel.end_frame()

        hr = panel._hit_rects[0]
        assert hr.kwargs == {"asset_id": "abc", "count": 5}

    def test_disabled_button_no_hit_rect(self):
        panel = _make_panel(width=200, anchor=(0, 200))
        root = panel.begin_frame()
        root.enabled = False
        root.operator("melvil.test_op", text="Disabled")
        panel.end_frame()

        assert len(panel._hit_rects) == 0

    def test_disabled_parent_no_hit_rect(self):
        """Button in a disabled parent layout registers no hit rect."""
        panel = _make_panel(width=200, anchor=(0, 200))
        root = panel.begin_frame()
        col = root.column()
        col.enabled = False
        col.operator("melvil.test_op", text="Disabled")
        panel.end_frame()

        assert len(panel._hit_rects) == 0

    def test_multiple_buttons_register_multiple_rects(self):
        panel = _make_panel(width=200, anchor=(0, 200))
        root = panel.begin_frame()
        root.operator("melvil.op_a", text="A")
        root.operator("melvil.op_b", text="B")
        panel.end_frame()

        assert len(panel._hit_rects) == 2
        ids = {hr.id for hr in panel._hit_rects}
        assert ids == {"melvil.op_a", "melvil.op_b"}

    def test_hit_test_finds_button(self):
        panel = _make_panel(width=200, anchor=(0, 200))
        root = panel.begin_frame()
        root.operator("melvil.test_op", text="Click")
        panel.end_frame()

        hr = panel._hit_rects[0]
        cx = hr.rect[0] + hr.rect[2] / 2
        cy = hr.rect[1] + hr.rect[3] / 2
        result = panel.hit_test(int(cx), int(cy))
        assert result is not None
        assert result.id == "melvil.test_op"


# ---------------------------------------------------------------------------
# GpuPanel — hover state
# ---------------------------------------------------------------------------


class TestGpuPanelHover:
    def test_mouse_pos_initially_none(self):
        panel = _make_panel()
        assert panel._mouse_pos is None

    def test_update_mouse_stores_position(self):
        panel = _make_panel()
        panel.update_mouse(50.0, 75.0)
        assert panel._mouse_pos == (50.0, 75.0)

    def test_detach_clears_mouse_pos(self):
        panel = _make_panel()
        panel.update_mouse(50.0, 75.0)
        panel.detach()
        assert panel._mouse_pos is None


# ---------------------------------------------------------------------------
# GpuButton — hover visual
# ---------------------------------------------------------------------------


class TestGpuButtonHover:
    def setup_method(self):
        import melvil.ui.gpu.theme as gpu_theme
        from melvil.ui.gpu import ThemeColors

        gpu_theme._theme = ThemeColors.fallback()

    def teardown_method(self):
        import melvil.ui.gpu.theme as gpu_theme

        gpu_theme._theme = None

    def test_hovered_embossed_uses_hover_bg(self):
        """Button with mouse over it uses button_bg_hover color."""
        import gpu as _gpu
        from melvil.ui.gpu import get_theme

        shader = _gpu.shader.from_builtin.return_value

        panel = _make_panel(width=200, anchor=(0, 200))
        root = panel.begin_frame()
        root.operator("melvil.test_op", text="Click")
        # Simulate frame cycle with mouse positioned over the button.
        panel.end_frame()

        # Get button rect and set mouse inside it.
        btn = root._children[0]
        cx = btn.rect[0] + btn.rect[2] / 2
        cy = btn.rect[1] + btn.rect[3] / 2
        panel.update_mouse(cx, cy)

        # Redraw with hover.
        shader.uniform_float.reset_mock()
        root2 = panel.begin_frame()
        root2.operator("melvil.test_op", text="Click")
        panel.end_frame()

        theme = get_theme()
        colors = [
            c.args[1] for c in shader.uniform_float.call_args_list
            if c.args[0] == "color"
        ]
        assert theme.button_bg_hover in colors

    def test_unhovered_embossed_uses_default_bg(self):
        """Button without hover uses button_bg color (not active/depress)."""
        import gpu as _gpu
        from melvil.ui.gpu import get_theme

        shader = _gpu.shader.from_builtin.return_value

        panel = _make_panel(width=200, anchor=(0, 200))
        # Mouse far away from button.
        panel.update_mouse(999.0, 999.0)

        shader.uniform_float.reset_mock()
        root = panel.begin_frame()
        root.operator("melvil.test_op", text="Click")
        panel.end_frame()

        theme = get_theme()
        colors = [
            c.args[1] for c in shader.uniform_float.call_args_list
            if c.args[0] == "color"
        ]
        assert theme.button_bg in colors
        # widget_bg_active should not appear (that's for depress).
        assert theme.widget_bg_active not in colors

    def test_hovered_unembossed_draws_subtle_bg(self):
        """Unembossed button under hover draws a half-alpha background."""
        from gpu_extras.batch import batch_for_shader as bf

        panel = _make_panel(width=200, anchor=(0, 200))
        # First, find the button rect.
        root = panel.begin_frame()
        root.operator("melvil.test_op", text="Hover", emboss=False)
        panel.end_frame()
        btn = root._children[0]
        cx = btn.rect[0] + btn.rect[2] / 2
        cy = btn.rect[1] + btn.rect[3] / 2
        panel.update_mouse(cx, cy)

        # Redraw. Unembossed + hovered should draw at least one bg rect.
        bf.reset_mock()
        root2 = panel.begin_frame()
        root2.separator()  # baseline
        panel.end_frame()
        baseline = bf.call_count

        bf.reset_mock()
        root3 = panel.begin_frame()
        root3.operator("melvil.test_op", text="Hover", emboss=False)
        panel.end_frame()
        assert bf.call_count > baseline


# ---------------------------------------------------------------------------
# Shared widget helpers (_resolve_text_color, _draw_text_content)
# ---------------------------------------------------------------------------


class TestResolveTextColor:
    def test_alert_takes_priority(self):
        from melvil.ui.gpu import GpuLabel, get_theme

        w = GpuLabel(text="X", alert=True)
        theme = get_theme()
        assert w._resolve_text_color(True, theme.text_primary) == theme.alert

    def test_disabled_returns_text_disabled(self):
        from melvil.ui.gpu import GpuLabel, get_theme

        w = GpuLabel(text="X", enabled=False)
        theme = get_theme()
        assert w._resolve_text_color(True, theme.text_primary) == theme.text_disabled

    def test_parent_disabled_returns_text_disabled(self):
        from melvil.ui.gpu import GpuLabel, get_theme

        w = GpuLabel(text="X", enabled=True)
        theme = get_theme()
        assert w._resolve_text_color(False, theme.text_primary) == theme.text_disabled

    def test_enabled_returns_default(self):
        from melvil.ui.gpu import GpuLabel, get_theme

        w = GpuLabel(text="X")
        theme = get_theme()
        assert w._resolve_text_color(True, theme.button_text) == theme.button_text


class TestDrawTextContent:
    def test_left_aligned(self):
        import blf
        from melvil.ui.gpu import GpuLabel, WIDGET_PAD_X

        blf.draw.reset_mock()
        blf.position.reset_mock()
        blf.dimensions = MagicMock(return_value=(40.0, 12.0))

        w = GpuLabel(text="Hello")
        w.rect = (10.0, 20.0, 200.0, 20.0)
        w._draw_text_content(1.0, (1, 1, 1, 1), align="LEFT")

        blf.position.assert_called_once()
        text_x = blf.position.call_args.args[1]
        assert text_x == pytest.approx(10.0 + WIDGET_PAD_X)

    def test_center_aligned(self):
        import blf
        from melvil.ui.gpu import GpuLabel

        blf.draw.reset_mock()
        blf.position.reset_mock()
        blf.dimensions = MagicMock(return_value=(40.0, 12.0))

        w = GpuLabel(text="Center")
        w.rect = (10.0, 20.0, 200.0, 20.0)
        w._draw_text_content(1.0, (1, 1, 1, 1), align="CENTER")

        text_x = blf.position.call_args.args[1]
        expected_x = 10.0 + (200.0 - 40.0) / 2
        assert text_x == pytest.approx(expected_x)

    def test_no_draw_on_empty_text(self):
        import blf
        from melvil.ui.gpu import GpuLabel

        blf.draw.reset_mock()

        w = GpuLabel(text="")
        w.rect = (0.0, 0.0, 100.0, 20.0)
        w._draw_text_content(1.0, (1, 1, 1, 1))

        blf.draw.assert_not_called()

    def test_no_draw_on_none_rect(self):
        import blf
        from melvil.ui.gpu import GpuLabel

        blf.draw.reset_mock()

        w = GpuLabel(text="Hello")
        w.rect = None
        w._draw_text_content(1.0, (1, 1, 1, 1))

        blf.draw.assert_not_called()


# ---------------------------------------------------------------------------
# point_in_rect (shared helper)
# ---------------------------------------------------------------------------


class TestPointInRect:
    def test_inside(self):
        from melvil.ui.gpu import point_in_rect

        assert point_in_rect((50, 50), (0, 0, 100, 100)) is True

    def test_outside(self):
        from melvil.ui.gpu import point_in_rect

        assert point_in_rect((150, 50), (0, 0, 100, 100)) is False

    def test_none_pos(self):
        from melvil.ui.gpu import point_in_rect

        assert point_in_rect(None, (0, 0, 100, 100)) is False

    def test_on_edge(self):
        from melvil.ui.gpu import point_in_rect

        assert point_in_rect((100, 100), (0, 0, 100, 100)) is True


# ---------------------------------------------------------------------------
# draw_text_in_rect (shared helper)
# ---------------------------------------------------------------------------


class TestDrawTextInRect:
    def test_center_aligned(self):
        import blf
        from melvil.ui.gpu import draw_text_in_rect

        blf.draw.reset_mock()
        blf.position.reset_mock()
        blf.dimensions = MagicMock(return_value=(40.0, 12.0))

        draw_text_in_rect("Hello", (10.0, 20.0, 200.0, 20.0), 1.0, (1, 1, 1, 1))

        blf.position.assert_called_once()
        text_x = blf.position.call_args.args[1]
        expected_x = 10.0 + (200.0 - 40.0) / 2
        assert text_x == pytest.approx(expected_x)

    def test_left_aligned(self):
        import blf
        from melvil.ui.gpu import draw_text_in_rect, WIDGET_PAD_X

        blf.draw.reset_mock()
        blf.position.reset_mock()
        blf.dimensions = MagicMock(return_value=(40.0, 12.0))

        draw_text_in_rect("Hello", (10.0, 20.0, 200.0, 20.0), 1.0, (1, 1, 1, 1), align="LEFT")

        text_x = blf.position.call_args.args[1]
        assert text_x == pytest.approx(10.0 + WIDGET_PAD_X)

    def test_empty_text_no_draw(self):
        import blf
        from melvil.ui.gpu import draw_text_in_rect

        blf.draw.reset_mock()
        draw_text_in_rect("", (10.0, 20.0, 200.0, 20.0), 1.0, (1, 1, 1, 1))
        blf.draw.assert_not_called()


# ---------------------------------------------------------------------------
# GpuEnumButtons — construction
# ---------------------------------------------------------------------------


_MOCK_ENUM_ITEMS = [
    ("ALL", "All", "", "ASSET_MANAGER"),
    ("MATERIAL", "Materials", "", "MATERIAL"),
    ("MESH", "Meshes", "", "MESH_DATA"),
    ("NODE_GROUP", "Node Groups", "", "NODETREE"),
]


class TestGpuEnumButtons:
    def test_construction(self):
        from melvil.ui.gpu import GpuEnumButtons

        w = GpuEnumButtons(
            items=_MOCK_ENUM_ITEMS,
            active_value="ALL",
            property_name="type_filter",
        )
        assert len(w.items) == 4
        assert w.active_value == "ALL"
        assert w.property_name == "type_filter"

    def test_height_matches_item_count(self):
        from melvil.ui.gpu import GpuEnumButtons, WIDGET_HEIGHT, WIDGET_GAP_ALIGNED

        w = GpuEnumButtons(items=_MOCK_ENUM_ITEMS)
        h = w.measure_height(1.0)
        expected = 4 * WIDGET_HEIGHT + 3 * WIDGET_GAP_ALIGNED
        assert h == pytest.approx(expected)

    def test_empty_items_zero_height(self):
        from melvil.ui.gpu import GpuEnumButtons

        w = GpuEnumButtons(items=[])
        assert w.measure_height(1.0) == 0.0

    def test_single_item_no_gap(self):
        from melvil.ui.gpu import GpuEnumButtons, WIDGET_HEIGHT

        w = GpuEnumButtons(items=[("ONLY", "Only", "", "NONE")])
        assert w.measure_height(1.0) == pytest.approx(WIDGET_HEIGHT)

    def test_inherits_from_gpu_widget(self):
        from melvil.ui.gpu import GpuEnumButtons, GpuWidget

        assert issubclass(GpuEnumButtons, GpuWidget)


# ---------------------------------------------------------------------------
# GpuEnumButtons — drawing
# ---------------------------------------------------------------------------


class TestGpuEnumButtonsDraw:
    def test_active_item_uses_active_bg(self):
        """Active item draws with widget_bg_active background color."""
        import gpu as _gpu
        from melvil.ui.gpu import get_theme

        shader = _gpu.shader.from_builtin.return_value

        panel = _make_panel(width=200, anchor=(0, 400))
        root = panel.begin_frame()
        root._children.append(
            _make_enum_widget(active_value="MATERIAL"),
        )
        panel.end_frame()

        theme = get_theme()
        colors = [
            c.args[1] for c in shader.uniform_float.call_args_list
            if c.args[0] == "color"
        ]
        assert theme.widget_bg_active in colors

    def test_inactive_item_uses_button_bg(self):
        """Non-active items draw with button_bg background color."""
        import gpu as _gpu
        from melvil.ui.gpu import get_theme

        shader = _gpu.shader.from_builtin.return_value

        panel = _make_panel(width=200, anchor=(0, 400))
        root = panel.begin_frame()
        root._children.append(
            _make_enum_widget(active_value="ALL"),
        )
        panel.end_frame()

        theme = get_theme()
        colors = [
            c.args[1] for c in shader.uniform_float.call_args_list
            if c.args[0] == "color"
        ]
        # "ALL" is active; MATERIAL, MESH, NODE_GROUP should use button_bg.
        assert theme.button_bg in colors

    def test_item_text_drawn(self):
        """Each enum item name is drawn via blf."""
        import blf

        blf.draw.reset_mock()
        blf.dimensions = MagicMock(return_value=(40.0, 12.0))

        panel = _make_panel(width=200, anchor=(0, 400))
        root = panel.begin_frame()
        root._children.append(_make_enum_widget())
        panel.end_frame()

        drawn_texts = [c.args[1] for c in blf.draw.call_args_list]
        assert "All" in drawn_texts
        assert "Materials" in drawn_texts
        assert "Meshes" in drawn_texts
        assert "Node Groups" in drawn_texts

    def test_active_item_uses_selection_text_color(self):
        """Active item text uses selection_text for contrast."""
        import blf
        from melvil.ui.gpu import get_theme

        blf.color.reset_mock()
        blf.dimensions = MagicMock(return_value=(40.0, 12.0))

        panel = _make_panel(width=200, anchor=(0, 400))
        root = panel.begin_frame()
        root._children.append(_make_enum_widget(active_value="ALL"))
        panel.end_frame()

        theme = get_theme()
        color_calls = [c.args[1:] for c in blf.color.call_args_list]
        assert theme.selection_text in color_calls

    def test_disabled_uses_disabled_color(self):
        """Disabled enum buttons use text_disabled for all items."""
        import blf
        from melvil.ui.gpu import get_theme, GpuEnumButtons

        blf.color.reset_mock()
        blf.dimensions = MagicMock(return_value=(40.0, 12.0))

        w = GpuEnumButtons(
            items=_MOCK_ENUM_ITEMS,
            active_value="ALL",
            enabled=False,
        )

        panel = _make_panel(width=200, anchor=(0, 400))
        root = panel.begin_frame()
        root._children.append(w)
        panel.end_frame()

        theme = get_theme()
        color_calls = [c.args[1:] for c in blf.color.call_args_list]
        # All item text should be disabled color.
        item_colors = color_calls[-4:]  # last 4 items
        assert all(c == theme.text_disabled for c in item_colors)

    def test_empty_items_no_draw(self):
        """Widget with no items draws nothing extra."""
        import blf
        from melvil.ui.gpu import GpuEnumButtons

        panel = _make_panel(width=200, anchor=(0, 200))
        root = panel.begin_frame()
        root._children.append(GpuEnumButtons(items=[]))
        blf.draw.reset_mock()
        panel.end_frame()

        drawn_texts = [c.args[1] for c in blf.draw.call_args_list]
        assert "All" not in drawn_texts
        assert "Materials" not in drawn_texts


# ---------------------------------------------------------------------------
# GpuEnumButtons — hit-rect registration
# ---------------------------------------------------------------------------


class TestGpuEnumButtonsHitRect:
    def test_registers_hit_rects_per_item(self):
        panel = _make_panel(width=200, anchor=(0, 400))
        root = panel.begin_frame()
        root._children.append(
            _make_enum_widget(property_name="type_filter"),
        )
        panel.end_frame()

        prop_hits = [h for h in panel._hit_rects if h.widget_type == "prop"]
        assert len(prop_hits) == 4

    def test_hit_rect_has_correct_property_name(self):
        panel = _make_panel(width=200, anchor=(0, 400))
        root = panel.begin_frame()
        root._children.append(
            _make_enum_widget(property_name="type_filter"),
        )
        panel.end_frame()

        prop_hits = [h for h in panel._hit_rects if h.widget_type == "prop"]
        assert all(h.id == "type_filter" for h in prop_hits)

    def test_hit_rect_has_correct_value(self):
        panel = _make_panel(width=200, anchor=(0, 400))
        root = panel.begin_frame()
        root._children.append(
            _make_enum_widget(property_name="type_filter"),
        )
        panel.end_frame()

        prop_hits = [h for h in panel._hit_rects if h.widget_type == "prop"]
        values = [h.kwargs["value"] for h in prop_hits]
        assert set(values) == {"ALL", "MATERIAL", "MESH", "NODE_GROUP"}

    def test_disabled_registers_no_hit_rects(self):
        from melvil.ui.gpu import GpuEnumButtons

        panel = _make_panel(width=200, anchor=(0, 400))
        root = panel.begin_frame()
        root._children.append(GpuEnumButtons(
            items=_MOCK_ENUM_ITEMS,
            active_value="ALL",
            enabled=False,
            property_name="type_filter",
        ))
        panel.end_frame()

        prop_hits = [h for h in panel._hit_rects if h.widget_type == "prop"]
        assert len(prop_hits) == 0

    def test_hit_test_finds_enum_button(self):
        """hit_test() on an enum button returns the correct HitResult."""
        panel = _make_panel(width=200, anchor=(0, 400))
        root = panel.begin_frame()
        root._children.append(
            _make_enum_widget(property_name="type_filter"),
        )
        panel.end_frame()

        # Find the first prop hit rect and click its center.
        prop_hits = [h for h in panel._hit_rects if h.widget_type == "prop"]
        hit_rect = prop_hits[0].rect
        cx = hit_rect[0] + hit_rect[2] / 2
        cy = hit_rect[1] + hit_rect[3] / 2
        result = panel.hit_test(cx, cy)

        assert result is not None
        assert result.widget_type == "prop"


# ---------------------------------------------------------------------------
# GpuEnumButtons — hover
# ---------------------------------------------------------------------------


class TestGpuEnumButtonsHover:
    def setup_method(self):
        from melvil.ui.gpu import reset_theme, ThemeColors

        reset_theme()
        self._orig = ThemeColors.fallback

    def teardown_method(self):
        from melvil.ui.gpu import reset_theme, ThemeColors

        ThemeColors.fallback = self._orig
        reset_theme()

    def test_hovered_inactive_uses_hover_bg(self):
        """Non-active enum button under hover uses button_bg_hover."""
        import gpu as _gpu
        from melvil.ui.gpu import get_theme

        theme = get_theme()
        shader = _gpu.shader.from_builtin.return_value

        panel = _make_panel(width=200, anchor=(0, 400))
        # First pass: find the last item's rect (it's not active).
        root = panel.begin_frame()
        w = _make_enum_widget(active_value="ALL")
        root._children.append(w)
        panel.end_frame()

        # The widget has been positioned — grab the bottom-most item rect.
        # Items draw top-to-bottom in the widget rect.  The last enum item
        # ("NODE_GROUP") is at the bottom.
        prop_hits = [h for h in panel._hit_rects if h.widget_type == "prop"]
        # Find the NODE_GROUP hit rect.
        ng_hit = next(h for h in prop_hits if h.kwargs["value"] == "NODE_GROUP")
        cx = ng_hit.rect[0] + ng_hit.rect[2] / 2
        cy = ng_hit.rect[1] + ng_hit.rect[3] / 2
        panel.update_mouse(cx, cy)

        # Second pass: redraw with hover.
        shader.uniform_float.reset_mock()
        root2 = panel.begin_frame()
        root2._children.append(_make_enum_widget(active_value="ALL"))
        panel.end_frame()

        colors = [
            c.args[1] for c in shader.uniform_float.call_args_list
            if c.args[0] == "color"
        ]
        assert theme.button_bg_hover in colors


# ---------------------------------------------------------------------------
# GpuLayout.prop() — dispatch
# ---------------------------------------------------------------------------


def _mock_enum_rna(items, current_value="ALL"):
    """Create a mock data object with an ENUM property for testing prop().

    The ``prop()`` method first checks ``type(data).bl_rna.properties``
    using ``in`` then ``[]``, so the mock properties collection must
    support both ``__contains__`` and ``__getitem__``.
    """

    prop_rna = MagicMock()
    prop_rna.type = "ENUM"
    mock_items = []
    for ident, name, desc, icon in items:
        item = MagicMock()
        item.identifier = ident
        item.name = name
        item.description = desc
        item.icon = icon
        mock_items.append(item)
    prop_rna.enum_items = mock_items

    props_coll = MagicMock()
    props_coll.__contains__ = MagicMock(return_value=True)
    props_coll.__getitem__ = MagicMock(return_value=prop_rna)
    props_coll.keys = MagicMock(return_value=["type_filter"])

    bl_rna = MagicMock()
    bl_rna.properties = props_coll

    class MockData:
        pass

    MockData.bl_rna = bl_rna

    mock_data = MockData()
    mock_data.type_filter = current_value

    return mock_data


def _mock_string_rna():
    """Create a mock data object with a STRING property for testing prop()."""
    prop_rna = MagicMock()
    prop_rna.type = "STRING"

    props_coll = MagicMock()
    props_coll.__contains__ = MagicMock(return_value=True)
    props_coll.__getitem__ = MagicMock(return_value=prop_rna)
    props_coll.keys = MagicMock(return_value=["some_string"])

    bl_rna = MagicMock()
    bl_rna.properties = props_coll

    class MockStringData:
        pass

    MockStringData.bl_rna = bl_rna
    return MockStringData()


class TestGpuLayoutProp:
    def test_enum_expand_appends_enum_buttons(self):
        from melvil.ui.gpu import GpuEnumButtons

        mock_data = _mock_enum_rna(_MOCK_ENUM_ITEMS, "ALL")

        panel = _make_panel()
        root = panel.begin_frame()
        root.prop(mock_data, "type_filter", expand=True)

        assert len(root._children) == 1
        child = root._children[0]
        assert isinstance(child, GpuEnumButtons)
        assert len(child.items) == 4
        assert child.active_value == "ALL"
        assert child.property_name == "type_filter"

    def test_enum_expand_reads_current_value(self):
        mock_data = _mock_enum_rna(_MOCK_ENUM_ITEMS, "MESH")

        panel = _make_panel()
        root = panel.begin_frame()
        root.prop(mock_data, "type_filter", expand=True)

        child = root._children[0]
        assert child.active_value == "MESH"

    def test_enum_no_expand_falls_back_to_label(self):
        """Enum without expand=True falls back to label stub."""
        from melvil.ui.gpu import GpuLabel

        mock_data = _mock_enum_rna(_MOCK_ENUM_ITEMS)

        panel = _make_panel()
        root = panel.begin_frame()
        root.prop(mock_data, "type_filter", expand=False)

        assert len(root._children) == 1
        child = root._children[0]
        assert isinstance(child, GpuLabel)

    def test_non_enum_falls_back_to_label(self):
        """Non-enum property type falls back to label stub."""
        from melvil.ui.gpu import GpuLabel

        mock_data = _mock_string_rna()

        panel = _make_panel()
        root = panel.begin_frame()
        root.prop(mock_data, "search_query")

        assert len(root._children) == 1
        child = root._children[0]
        assert isinstance(child, GpuLabel)

    def test_label_stub_uses_text_param(self):
        """Label stub uses the text parameter when provided."""
        from melvil.ui.gpu import GpuLabel

        mock_data = _mock_string_rna()

        panel = _make_panel()
        root = panel.begin_frame()
        root.prop(mock_data, "search_query", text="Search")

        child = root._children[0]
        assert isinstance(child, GpuLabel)
        assert child.text == "Search"

    def test_label_stub_uses_property_name_when_no_text(self):
        """Label stub defaults to the property name when text is None."""
        from melvil.ui.gpu import GpuLabel

        mock_data = _mock_string_rna()

        panel = _make_panel()
        root = panel.begin_frame()
        root.prop(mock_data, "search_query")

        child = root._children[0]
        assert child.text == "search_query"

    def test_bl_rna_missing_falls_back_to_label(self):
        """If bl_rna access fails, falls back to label gracefully."""
        from melvil.ui.gpu import GpuLabel

        bl_rna = MagicMock()
        bl_rna.properties.__getitem__.side_effect = KeyError("no")

        class BrokenData:
            pass

        BrokenData.bl_rna = bl_rna
        mock_data = BrokenData()

        panel = _make_panel()
        root = panel.begin_frame()
        root.prop(mock_data, "missing_prop")

        assert len(root._children) == 1
        assert isinstance(root._children[0], GpuLabel)

    def test_inherits_enabled_false(self):
        """Enum buttons inherit enabled=False from parent layout."""
        from melvil.ui.gpu import GpuEnumButtons

        mock_data = _mock_enum_rna(_MOCK_ENUM_ITEMS)

        panel = _make_panel()
        root = panel.begin_frame()
        root.enabled = False
        root.prop(mock_data, "type_filter", expand=True)

        child = root._children[0]
        assert isinstance(child, GpuEnumButtons)
        assert child.enabled is False

    def test_inherits_alert(self):
        """Enum buttons inherit alert from parent layout."""
        from melvil.ui.gpu import GpuEnumButtons

        mock_data = _mock_enum_rna(_MOCK_ENUM_ITEMS)

        panel = _make_panel()
        root = panel.begin_frame()
        root.alert = True
        root.prop(mock_data, "type_filter", expand=True)

        child = root._children[0]
        assert child.alert is True

    def test_data_stored_on_widget(self):
        """The data object reference is stored on the widget for hit dispatch."""
        mock_data = _mock_enum_rna(_MOCK_ENUM_ITEMS)

        panel = _make_panel()
        root = panel.begin_frame()
        root.prop(mock_data, "type_filter", expand=True)

        child = root._children[0]
        assert child.data is mock_data


# ---------------------------------------------------------------------------
# Helper for building GpuEnumButtons used by multiple test classes
# ---------------------------------------------------------------------------


def _make_enum_widget(**overrides):
    """Return a GpuEnumButtons with sensible defaults."""
    from melvil.ui.gpu import GpuEnumButtons

    defaults = {
        "items": list(_MOCK_ENUM_ITEMS),
        "active_value": "ALL",
        "property_name": "type_filter",
    }
    defaults.update(overrides)
    return GpuEnumButtons(**defaults)
