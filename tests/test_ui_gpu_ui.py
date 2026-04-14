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
        """Panel rect width = scaled width, height = tree height + padding."""
        panel = _make_panel(width=200, anchor=(10, 100))
        root = panel.begin_frame()
        root.separator()  # adds SEPARATOR_HEIGHT
        panel.end_frame()

        from melvil.ui.gpu import PANEL_PAD, SEPARATOR_HEIGHT

        expected_h = SEPARATOR_HEIGHT + 2 * PANEL_PAD
        x, y, w, h = panel._panel_rect
        assert w == pytest.approx(200.0)
        assert h == pytest.approx(expected_h)
        assert x == pytest.approx(10.0)
        assert y == pytest.approx(100.0 - expected_h)


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

        from melvil.ui.gpu import PANEL_PAD, WIDGET_GAP

        content_w = 200 - 2 * PANEL_PAD
        expected_each = (content_w - WIDGET_GAP) / 2
        assert c1._rect[2] == pytest.approx(expected_each)
        assert c2._rect[2] == pytest.approx(expected_each)

    def test_split_factor_03(self):
        from melvil.ui.gpu import PANEL_PAD, WIDGET_GAP

        panel = _make_panel(width=200, anchor=(0, 100))
        root = panel.begin_frame()
        sp = root.split(factor=0.3)
        left = sp.column()
        left.separator()
        right = sp.column()
        right.separator()
        panel.end_frame()

        content_w = 200 - 2 * PANEL_PAD
        usable = content_w - WIDGET_GAP * 2
        assert left._rect is not None
        assert right._rect is not None
        assert left._rect[2] == pytest.approx(usable * 0.3)
        assert right._rect[2] == pytest.approx(usable * 0.7)

    def test_box_adds_padding(self):
        from melvil.ui.gpu import BOX_PAD, PANEL_PAD, SEPARATOR_HEIGHT

        panel = _make_panel(width=200, anchor=(0, 200))
        root = panel.begin_frame()
        bx = root.box()
        bx.separator()
        panel.end_frame()

        # Box rect includes padding on all sides.
        content_w = 200 - 2 * PANEL_PAD
        assert bx._rect is not None
        bx_x, bx_y, bx_w, bx_h = bx._rect
        assert bx_w == pytest.approx(content_w)
        assert bx_h == pytest.approx(SEPARATOR_HEIGHT + 2 * BOX_PAD)

    def test_nested_row_in_column_in_split(self):
        """Nested containers produce correct coordinates."""
        from melvil.ui.gpu import PANEL_PAD, SEPARATOR_HEIGHT, WIDGET_GAP

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

        content_w = 400 - 2 * PANEL_PAD
        usable = content_w - WIDGET_GAP * 2
        # Left half = usable * 0.5, row inside splits it.
        assert a._rect is not None
        assert b._rect is not None
        assert right_col._rect is not None
        assert a._rect[2] + b._rect[2] == pytest.approx(
            left_col._rect[2], abs=5,
        )
        assert right_col._rect[2] == pytest.approx(usable * 0.5)

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
        from melvil.ui.gpu import PANEL_PAD

        panel = _make_panel(width=200, anchor=(0, 200))
        root = panel.begin_frame()
        root.label(text="Hello")
        panel.end_frame()

        child = root._children[0]
        assert child.rect is not None
        x, y, w, h = child.rect
        assert w == pytest.approx(200 - 2 * PANEL_PAD)

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
        from melvil.ui.gpu import WIDGET_HEIGHT, WIDGET_GAP, PANEL_PAD

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

        content_w = 200 - 2 * PANEL_PAD
        expected_each = (content_w - WIDGET_GAP) / 2
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
        from melvil.ui.gpu import PANEL_PAD

        panel = _make_panel(width=200, anchor=(0, 200))
        root = panel.begin_frame()
        root.operator("melvil.test_op", text="Click")
        panel.end_frame()

        child = root._children[0]
        assert child.rect is not None
        x, y, w, h = child.rect
        assert w == pytest.approx(200 - 2 * PANEL_PAD)

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


def _mock_string_rna(*, textedit_update=False, current_value=""):
    """Create a mock data object with a STRING property for testing prop()."""
    prop_rna = MagicMock()
    prop_rna.type = "STRING"
    prop_rna.name = "Asset name"

    props_coll = MagicMock()
    props_coll.__contains__ = MagicMock(return_value=True)
    props_coll.__getitem__ = MagicMock(return_value=prop_rna)
    props_coll.keys = MagicMock(return_value=["search_query"])

    bl_rna = MagicMock()
    bl_rna.properties = props_coll

    class MockStringData:
        pass

    MockStringData.bl_rna = bl_rna

    if textedit_update:
        _kw = {"options": {"HIDDEN", "TEXTEDIT_UPDATE"}}
    else:
        _kw = {"options": {"HIDDEN"}}

    class _Deferred:
        def __init__(self, keywords):
            self.keywords = keywords

    MockStringData.__annotations__ = {
        "search_query": _Deferred(_kw),
    }

    mock = MockStringData()
    mock.search_query = current_value
    return mock


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

    def test_enum_no_expand_creates_dropdown(self):
        """Enum without expand=True creates a dropdown trigger."""
        from melvil.ui.gpu import GpuDropdown

        mock_data = _mock_enum_rna(_MOCK_ENUM_ITEMS)

        panel = _make_panel()
        root = panel.begin_frame()
        root.prop(mock_data, "type_filter", expand=False)

        assert len(root._children) == 1
        child = root._children[0]
        assert isinstance(child, GpuDropdown)
        assert child.mode == "prop"
        assert child.property_name == "type_filter"

    def test_non_enum_falls_back_to_label(self):
        """Non-enum property type falls back to label stub."""
        from melvil.ui.gpu import GpuLabel

        # Use an INT property (not STRING — STRING is now a text field).
        prop_rna = MagicMock()
        prop_rna.type = "INT"
        props_coll = MagicMock()
        props_coll.__contains__ = MagicMock(return_value=True)
        props_coll.__getitem__ = MagicMock(return_value=prop_rna)

        bl_rna = MagicMock()
        bl_rna.properties = props_coll

        class MockIntData:
            pass

        MockIntData.bl_rna = bl_rna
        mock_data = MockIntData()

        panel = _make_panel()
        root = panel.begin_frame()
        root.prop(mock_data, "some_int")

        assert len(root._children) == 1
        child = root._children[0]
        assert isinstance(child, GpuLabel)

    def test_string_creates_text_field(self):
        """STRING property creates a GpuTextField."""
        from melvil.ui.gpu import GpuTextField

        mock_data = _mock_string_rna()

        panel = _make_panel()
        root = panel.begin_frame()
        root.prop(mock_data, "search_query")

        assert len(root._children) == 1
        child = root._children[0]
        assert isinstance(child, GpuTextField)
        assert child.property_name == "search_query"
        assert child.data is mock_data

    def test_string_text_field_uses_text_param(self):
        """Text field uses the text parameter as prefix."""
        from melvil.ui.gpu import GpuTextField

        mock_data = _mock_string_rna()

        panel = _make_panel()
        root = panel.begin_frame()
        root.prop(mock_data, "search_query", text="Search")

        child = root._children[0]
        assert isinstance(child, GpuTextField)
        assert child.prefix_text == "Search"

    def test_string_text_field_uses_rna_name_when_no_text(self):
        """Text field defaults to the RNA property name as prefix."""
        from melvil.ui.gpu import GpuTextField

        mock_data = _mock_string_rna()

        panel = _make_panel()
        root = panel.begin_frame()
        root.prop(mock_data, "search_query")

        child = root._children[0]
        assert child.prefix_text == "Asset name"

    def test_string_text_field_empty_text_no_prefix(self):
        """text='' means no prefix label on the text field."""
        from melvil.ui.gpu import GpuTextField

        mock_data = _mock_string_rna()

        panel = _make_panel()
        root = panel.begin_frame()
        root.prop(mock_data, "search_query", text="")

        child = root._children[0]
        assert isinstance(child, GpuTextField)
        assert child.prefix_text == ""

    def test_string_text_field_inherits_textedit_update(self):
        """TEXTEDIT_UPDATE option is propagated to the widget."""
        from melvil.ui.gpu import GpuTextField

        mock_data = _mock_string_rna(textedit_update=True)

        panel = _make_panel()
        root = panel.begin_frame()
        root.prop(mock_data, "search_query", text="")

        child = root._children[0]
        assert isinstance(child, GpuTextField)
        assert child.textedit_update is True

    def test_explicit_textedit_update_kwarg(self):
        """Explicit textedit_update=True overrides auto-detection."""
        from melvil.ui.gpu import GpuTextField

        # Without TEXTEDIT_UPDATE in annotations → auto-detect returns False.
        mock_data = _mock_string_rna(textedit_update=False)

        panel = _make_panel()
        root = panel.begin_frame()
        root.prop(mock_data, "search_query", text="", textedit_update=True)

        child = root._children[0]
        assert isinstance(child, GpuTextField)
        assert child.textedit_update is True

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


# ---------------------------------------------------------------------------
# Helper for building GpuTextField used by multiple test classes
# ---------------------------------------------------------------------------


def _make_text_field(**overrides):
    """Return a GpuTextField with sensible defaults."""
    from melvil.ui.gpu import GpuTextField

    mock = _mock_string_rna(current_value="hello")
    defaults = {
        "data": mock,
        "property_name": "search_query",
        "prefix_text": "",
        "textedit_update": False,
    }
    defaults.update(overrides)
    return GpuTextField(**defaults)


class _MockEvent:
    """Minimal mock for ``bpy.types.Event`` used in text field tests."""

    def __init__(
        self,
        type: str = "A",
        value: str = "PRESS",
        unicode: str = "",
        ctrl: bool = False,
        mouse_region_x: int = 0,
        mouse_region_y: int = 0,
    ):
        self.type = type
        self.value = value
        self.unicode = unicode
        self.ctrl = ctrl
        self.mouse_region_x = mouse_region_x
        self.mouse_region_y = mouse_region_y


# ===========================================================================
# Text field widget — measure / draw / hit rect
# ===========================================================================


class TestGpuTextField:
    """Tests for the GpuTextField widget."""

    def test_measure_height(self):
        """measure_height returns scaled WIDGET_HEIGHT."""
        from melvil.ui.gpu.constants import WIDGET_HEIGHT, scaled

        w = _make_text_field()
        assert w.measure_height(1.0) == scaled(WIDGET_HEIGHT, 1.0)
        assert w.measure_height(2.0) == scaled(WIDGET_HEIGHT, 2.0)

    def test_hit_rect_registered(self):
        """Drawing a text field registers a hit rect."""
        w = _make_text_field()
        panel = _make_panel()
        panel.begin_frame()
        w.rect = (10, 20, 200, 26)
        w.draw(1.0, True, panel)
        hits = [h for h in panel._hit_rects if h.widget_type == "text_field"]
        assert len(hits) == 1
        assert hits[0].id == "search_query"
        assert hits[0].kwargs["data"] is w.data

    def test_hit_rect_not_registered_when_disabled(self):
        """Disabled text field does not register a hit rect."""
        w = _make_text_field(enabled=False)
        panel = _make_panel()
        panel.begin_frame()
        w.rect = (10, 20, 200, 26)
        w.draw(1.0, True, panel)
        hits = [h for h in panel._hit_rects if h.widget_type == "text_field"]
        assert len(hits) == 0

    def test_tab_order_registration(self):
        """Drawing registers the field in the panel tab order."""
        w = _make_text_field()
        panel = _make_panel()
        panel.begin_frame()
        w.rect = (10, 20, 200, 26)
        w.draw(1.0, True, panel)
        assert "search_query" in panel._text_field_order
        assert panel._text_field_data["search_query"] is w.data

    def test_textedit_update_registration(self):
        """Field with textedit_update=True is registered in the set."""
        w = _make_text_field(textedit_update=True)
        panel = _make_panel()
        panel.begin_frame()
        w.rect = (10, 20, 200, 26)
        w.draw(1.0, True, panel)
        assert "search_query" in panel._textedit_update_fields

    def test_textedit_update_not_registered_when_false(self):
        """Field with textedit_update=False is not registered."""
        w = _make_text_field(textedit_update=False)
        panel = _make_panel()
        panel.begin_frame()
        w.rect = (10, 20, 200, 26)
        w.draw(1.0, True, panel)
        assert "search_query" not in panel._textedit_update_fields

    def test_prefix_label_shrinks_field(self):
        """Prefix text reduces the field width."""
        w = _make_text_field(prefix_text="Search")
        panel = _make_panel()
        panel.begin_frame()
        w.rect = (10, 20, 200, 26)
        w.draw(1.0, True, panel)
        # Hit rect should be narrower than the full widget width.
        hits = [h for h in panel._hit_rects if h.widget_type == "text_field"]
        assert len(hits) == 1
        hit_x, _, hit_w, _ = hits[0].rect
        assert hit_x > 10  # Field pushed to the right
        assert hit_w < 200  # Field narrower

    def test_no_prefix_field_uses_full_width(self):
        """Without prefix the field uses the full widget width."""
        w = _make_text_field(prefix_text="")
        panel = _make_panel()
        panel.begin_frame()
        w.rect = (10, 20, 200, 26)
        w.draw(1.0, True, panel)
        hits = [h for h in panel._hit_rects if h.widget_type == "text_field"]
        assert len(hits) == 1
        hit_x, _, hit_w, _ = hits[0].rect
        assert hit_x == 10
        assert hit_w == 200


# ===========================================================================
# Text field activation / deactivation
# ===========================================================================


class TestTextFieldActivation:
    """Tests for activating and deactivating text fields."""

    def test_activate_sets_state(self):
        """activate_text_field sets all relevant state."""
        mock = _mock_string_rna(current_value="hello")
        panel = _make_panel()
        panel.begin_frame()
        panel.activate_text_field("search_query", mock)
        assert panel.active_text_field == "search_query"
        assert panel._text_buffer == "hello"
        assert panel.text_cursor_pos == 5  # at end
        assert panel._text_selection_start == 0  # select all
        assert panel._text_original_value == "hello"

    def test_confirm_deactivates(self):
        """confirm_text_field deactivates the field."""
        mock = _mock_string_rna(current_value="hello")
        panel = _make_panel()
        panel.begin_frame()
        panel.activate_text_field("search_query", mock)
        panel.confirm_text_field()
        assert panel.active_text_field is None
        assert panel._text_buffer is None

    def test_confirm_writes_value_for_non_textedit(self):
        """Non-TEXTEDIT_UPDATE fields write on confirm."""
        mock = _mock_string_rna(current_value="hello")
        panel = _make_panel()
        panel.begin_frame()
        panel.activate_text_field("search_query", mock)
        panel._text_buffer = "world"
        panel.confirm_text_field()
        assert mock.search_query == "world"

    def test_confirm_skips_write_for_textedit(self):
        """TEXTEDIT_UPDATE fields were already written; confirm is a no-op."""
        mock = _mock_string_rna(
            current_value="hello", textedit_update=True,
        )
        panel = _make_panel()
        panel.begin_frame()
        # Simulate draw to register TEXTEDIT_UPDATE.
        panel._textedit_update_fields.add("search_query")
        panel.activate_text_field("search_query", mock)
        panel._text_buffer = "world"
        panel.confirm_text_field()
        # The value was NOT written by confirm (it would have been
        # written incrementally by _apply_text).
        assert mock.search_query == "hello"

    def test_cancel_restores_original(self):
        """cancel_text_field restores the original value."""
        mock = _mock_string_rna(current_value="hello")
        panel = _make_panel()
        panel.begin_frame()
        panel.activate_text_field("search_query", mock)
        mock.search_query = "changed"
        panel.cancel_text_field()
        assert mock.search_query == "hello"
        assert panel.active_text_field is None

    def test_activate_confirms_previous_field(self):
        """Activating a new field confirms the currently active one."""
        mock1 = _mock_string_rna(current_value="one")
        mock2 = _mock_string_rna(current_value="two")
        panel = _make_panel()
        panel.begin_frame()
        panel.activate_text_field("search_query", mock1)
        panel._text_buffer = "modified"
        panel.activate_text_field("search_query", mock2)
        # First field was confirmed (non-textedit) so value is written.
        assert mock1.search_query == "modified"


# ===========================================================================
# Text field keyboard handling
# ===========================================================================


class TestTextFieldKeyboard:
    """Tests for _handle_text_keystroke."""

    def _activate(self, panel, mock, prop="search_query"):
        panel.activate_text_field(prop, mock)
        # Clear selection to start typing at end without select-all.
        panel._text_selection_start = None

    def test_printable_inserts_at_cursor(self):
        """Printable character inserts at cursor position."""
        mock = _mock_string_rna(current_value="ab")
        panel = _make_panel()
        panel.begin_frame()
        self._activate(panel, mock)
        panel.text_cursor_pos = 1  # between 'a' and 'b'
        panel._handle_text_keystroke(_MockEvent(type="X", unicode="x"))
        assert panel._text_buffer == "axb"
        assert panel.text_cursor_pos == 2

    def test_backspace_deletes_before_cursor(self):
        """BACK_SPACE deletes the character before the cursor."""
        mock = _mock_string_rna(current_value="abc")
        panel = _make_panel()
        panel.begin_frame()
        self._activate(panel, mock)
        panel.text_cursor_pos = 2
        panel._handle_text_keystroke(_MockEvent(type="BACK_SPACE"))
        assert panel._text_buffer == "ac"
        assert panel.text_cursor_pos == 1

    def test_backspace_at_start_does_nothing(self):
        """BACK_SPACE at position 0 leaves text unchanged."""
        mock = _mock_string_rna(current_value="abc")
        panel = _make_panel()
        panel.begin_frame()
        self._activate(panel, mock)
        panel.text_cursor_pos = 0
        panel._handle_text_keystroke(_MockEvent(type="BACK_SPACE"))
        assert panel._text_buffer == "abc"
        assert panel.text_cursor_pos == 0

    def test_delete_removes_after_cursor(self):
        """DEL deletes the character after the cursor."""
        mock = _mock_string_rna(current_value="abc")
        panel = _make_panel()
        panel.begin_frame()
        self._activate(panel, mock)
        panel.text_cursor_pos = 1
        panel._handle_text_keystroke(_MockEvent(type="DEL"))
        assert panel._text_buffer == "ac"
        assert panel.text_cursor_pos == 1

    def test_delete_at_end_does_nothing(self):
        """DEL at end of text leaves text unchanged."""
        mock = _mock_string_rna(current_value="abc")
        panel = _make_panel()
        panel.begin_frame()
        self._activate(panel, mock)
        panel.text_cursor_pos = 3
        panel._handle_text_keystroke(_MockEvent(type="DEL"))
        assert panel._text_buffer == "abc"

    def test_left_arrow_moves_cursor(self):
        """LEFT_ARROW decrements cursor position."""
        mock = _mock_string_rna(current_value="abc")
        panel = _make_panel()
        panel.begin_frame()
        self._activate(panel, mock)
        panel.text_cursor_pos = 2
        panel._handle_text_keystroke(_MockEvent(type="LEFT_ARROW"))
        assert panel.text_cursor_pos == 1

    def test_right_arrow_moves_cursor(self):
        """RIGHT_ARROW increments cursor position."""
        mock = _mock_string_rna(current_value="abc")
        panel = _make_panel()
        panel.begin_frame()
        self._activate(panel, mock)
        panel.text_cursor_pos = 1
        panel._handle_text_keystroke(_MockEvent(type="RIGHT_ARROW"))
        assert panel.text_cursor_pos == 2

    def test_home_moves_to_start(self):
        """HOME moves cursor to position 0."""
        mock = _mock_string_rna(current_value="abc")
        panel = _make_panel()
        panel.begin_frame()
        self._activate(panel, mock)
        panel.text_cursor_pos = 2
        panel._handle_text_keystroke(_MockEvent(type="HOME"))
        assert panel.text_cursor_pos == 0

    def test_end_moves_to_end(self):
        """END moves cursor to end of text."""
        mock = _mock_string_rna(current_value="abc")
        panel = _make_panel()
        panel.begin_frame()
        self._activate(panel, mock)
        panel.text_cursor_pos = 1
        panel._handle_text_keystroke(_MockEvent(type="END"))
        assert panel.text_cursor_pos == 3

    def test_enter_confirms(self):
        """RET confirms the field."""
        mock = _mock_string_rna(current_value="hello")
        panel = _make_panel()
        panel.begin_frame()
        self._activate(panel, mock)
        consumed = panel._handle_text_keystroke(_MockEvent(type="RET"))
        assert consumed is True
        assert panel.active_text_field is None

    def test_escape_cancels(self):
        """ESC cancels and restores original value."""
        mock = _mock_string_rna(current_value="hello")
        panel = _make_panel()
        panel.begin_frame()
        self._activate(panel, mock)
        panel._text_buffer = "changed"
        consumed = panel._handle_text_keystroke(_MockEvent(type="ESC"))
        assert consumed is True
        assert panel.active_text_field is None
        assert mock.search_query == "hello"

    def test_non_press_ignored(self):
        """Non-PRESS events are not consumed."""
        mock = _mock_string_rna(current_value="abc")
        panel = _make_panel()
        panel.begin_frame()
        self._activate(panel, mock)
        consumed = panel._handle_text_keystroke(
            _MockEvent(type="A", value="RELEASE", unicode="a"),
        )
        assert consumed is False

    def test_unrecognized_key_not_consumed(self):
        """Unrecognized keys return False."""
        mock = _mock_string_rna(current_value="abc")
        panel = _make_panel()
        panel.begin_frame()
        self._activate(panel, mock)
        consumed = panel._handle_text_keystroke(
            _MockEvent(type="F1", unicode=""),
        )
        assert consumed is False

    def test_ctrl_shortcuts_consumed(self):
        """Unknown Ctrl+key combos are consumed to prevent shortcuts."""
        mock = _mock_string_rna(current_value="abc")
        panel = _make_panel()
        panel.begin_frame()
        self._activate(panel, mock)
        consumed = panel._handle_text_keystroke(
            _MockEvent(type="Z", ctrl=True),
        )
        assert consumed is True

    def test_textedit_update_applies_immediately(self):
        """TEXTEDIT_UPDATE field applies text via setattr on each key."""
        mock = _mock_string_rna(
            current_value="abc", textedit_update=True,
        )
        panel = _make_panel()
        panel.begin_frame()
        panel._textedit_update_fields.add("search_query")
        self._activate(panel, mock)
        panel._handle_text_keystroke(
            _MockEvent(type="X", unicode="x"),
        )
        assert mock.search_query == "abcx"

    def test_non_textedit_does_not_apply_immediately(self):
        """Non-TEXTEDIT_UPDATE field only writes to the buffer."""
        mock = _mock_string_rna(current_value="abc")
        panel = _make_panel()
        panel.begin_frame()
        self._activate(panel, mock)
        panel._handle_text_keystroke(
            _MockEvent(type="X", unicode="x"),
        )
        # Buffer updated, but property NOT yet written.
        assert panel._text_buffer == "abcx"
        assert mock.search_query == "abc"


# ===========================================================================
# Text field clipboard
# ===========================================================================


class TestTextFieldClipboard:
    """Tests for Ctrl+V paste."""

    def test_paste_inserts_clipboard(self):
        """Ctrl+V inserts clipboard text at cursor."""
        mock = _mock_string_rna(current_value="ab")
        panel = _make_panel()
        panel.begin_frame()
        panel.activate_text_field("search_query", mock)
        panel._text_selection_start = None
        panel.text_cursor_pos = 1
        with patch(
            "melvil.ui.gpu.panel.bpy.context.window_manager"
        ) as mock_wm:
            mock_wm.clipboard = "XY"
            panel._handle_text_keystroke(
                _MockEvent(type="V", ctrl=True),
            )
        assert panel._text_buffer == "aXYb"
        assert panel.text_cursor_pos == 3

    def test_paste_strips_newlines(self):
        """Pasted newlines are stripped for single-line field."""
        mock = _mock_string_rna(current_value="")
        panel = _make_panel()
        panel.begin_frame()
        panel.activate_text_field("search_query", mock)
        panel._text_selection_start = None
        with patch(
            "melvil.ui.gpu.panel.bpy.context.window_manager"
        ) as mock_wm:
            mock_wm.clipboard = "a\nb\r\nc"
            panel._handle_text_keystroke(
                _MockEvent(type="V", ctrl=True),
            )
        assert panel._text_buffer == "abc"


# ===========================================================================
# Text field selection
# ===========================================================================


class TestTextFieldSelection:
    """Tests for select-all and selection replacement behaviour."""

    def test_activate_selects_all(self):
        """Activating a field selects all text."""
        mock = _mock_string_rna(current_value="hello")
        panel = _make_panel()
        panel.begin_frame()
        panel.activate_text_field("search_query", mock)
        assert panel._text_selection_start == 0
        assert panel.text_cursor_pos == 5

    def test_typing_replaces_selection(self):
        """Typing with select-all replaces all text."""
        mock = _mock_string_rna(current_value="hello")
        panel = _make_panel()
        panel.begin_frame()
        panel.activate_text_field("search_query", mock)
        # select-all is active (selection_start=0, cursor=5)
        panel._handle_text_keystroke(_MockEvent(type="X", unicode="x"))
        assert panel._text_buffer == "x"
        assert panel.text_cursor_pos == 1
        assert panel._text_selection_start is None

    def test_backspace_deletes_selection(self):
        """Backspace with selection deletes the selected text."""
        mock = _mock_string_rna(current_value="hello")
        panel = _make_panel()
        panel.begin_frame()
        panel.activate_text_field("search_query", mock)
        # select-all
        panel._handle_text_keystroke(_MockEvent(type="BACK_SPACE"))
        assert panel._text_buffer == ""
        assert panel.text_cursor_pos == 0

    def test_ctrl_a_selects_all(self):
        """Ctrl+A selects all text."""
        mock = _mock_string_rna(current_value="hello")
        panel = _make_panel()
        panel.begin_frame()
        panel.activate_text_field("search_query", mock)
        panel._text_selection_start = None
        panel.text_cursor_pos = 2
        panel._handle_text_keystroke(_MockEvent(type="A", ctrl=True))
        assert panel._text_selection_start == 0
        assert panel.text_cursor_pos == 5

    def test_arrow_clears_selection(self):
        """Arrow keys clear the selection."""
        mock = _mock_string_rna(current_value="hello")
        panel = _make_panel()
        panel.begin_frame()
        panel.activate_text_field("search_query", mock)
        # select-all is active
        panel._handle_text_keystroke(_MockEvent(type="LEFT_ARROW"))
        assert panel._text_selection_start is None


# ===========================================================================
# Text field tab cycling
# ===========================================================================


class TestTextFieldTabCycle:
    """Tests for Tab key cycling through text fields."""

    def test_tab_cycles_to_next_field(self):
        """Tab confirms current field and activates the next."""
        mock1 = _mock_string_rna(current_value="one")
        mock2 = _mock_string_rna(current_value="two")
        panel = _make_panel()
        panel.begin_frame()
        # Simulate tab order populated during draw.
        panel._text_field_order = ["field_a", "field_b"]
        panel._text_field_data = {"field_a": mock1, "field_b": mock2}
        panel.activate_text_field("field_a", mock1)
        panel._handle_text_keystroke(_MockEvent(type="TAB"))
        assert panel.active_text_field == "field_b"

    def test_tab_wraps_around(self):
        """Tab from the last field wraps to the first."""
        mock1 = _mock_string_rna(current_value="one")
        mock2 = _mock_string_rna(current_value="two")
        panel = _make_panel()
        panel.begin_frame()
        panel._text_field_order = ["field_a", "field_b"]
        panel._text_field_data = {"field_a": mock1, "field_b": mock2}
        panel.activate_text_field("field_b", mock2)
        panel._handle_text_keystroke(_MockEvent(type="TAB"))
        assert panel.active_text_field == "field_a"

    def test_tab_with_single_field_confirms(self):
        """Tab with only one field confirms and re-activates it."""
        mock = _mock_string_rna(current_value="solo")
        panel = _make_panel()
        panel.begin_frame()
        panel._text_field_order = ["search_query"]
        panel._text_field_data = {"search_query": mock}
        panel.activate_text_field("search_query", mock)
        panel._handle_text_keystroke(_MockEvent(type="TAB"))
        # Re-activates the same (only) field.
        assert panel.active_text_field == "search_query"

    def test_tab_with_no_fields_confirms(self):
        """Tab with empty field order just confirms."""
        mock = _mock_string_rna(current_value="solo")
        panel = _make_panel()
        panel.begin_frame()
        panel.activate_text_field("search_query", mock)
        panel._handle_text_keystroke(_MockEvent(type="TAB"))
        assert panel.active_text_field is None


# ===========================================================================
# Phase 6 — Icons
# ===========================================================================


# ---------------------------------------------------------------------------
# draw_texture uv_rect support
# ---------------------------------------------------------------------------


class TestDrawTextureUvRect:
    """Tests for the uv_rect parameter on draw_texture."""

    def test_default_uv_full_texture(self):
        """Without uv_rect, UVs span (0,0)→(1,1)."""
        from gpu_extras.batch import batch_for_shader
        from melvil.ui.gpu import draw_texture

        batch_for_shader.reset_mock()
        draw_texture(MagicMock(), 0, 0, 64, 64)

        # batch_for_shader(shader, 'TRIS', {"pos": ..., "texCoord": ...}, indices=...)
        attrs = batch_for_shader.call_args[0][2]
        assert attrs["texCoord"] == [(0, 0), (1, 0), (1, 1), (0, 1)]

    def test_custom_uv_rect(self):
        """uv_rect provides sub-region UV coordinates."""
        from gpu_extras.batch import batch_for_shader
        from melvil.ui.gpu import draw_texture

        batch_for_shader.reset_mock()
        draw_texture(MagicMock(), 0, 0, 32, 32, uv_rect=(0.25, 0.5, 0.75, 1.0))

        attrs = batch_for_shader.call_args[0][2]
        assert attrs["texCoord"] == [(0.25, 0.5), (0.75, 0.5), (0.75, 1.0), (0.25, 1.0)]


# ---------------------------------------------------------------------------
# IconProvider
# ---------------------------------------------------------------------------


class TestIconProvider:
    """Tests for the IconProvider class."""

    def test_atlas_none_in_test_env(self):
        """Atlas returns None when Blender isn't running."""
        from melvil.ui.gpu.icons import IconProvider

        provider = IconProvider()
        assert provider.atlas is None

    def test_get_icon_uv_none_when_no_atlas(self):
        """get_icon_uv returns None when atlas is not loaded."""
        from melvil.ui.gpu.icons import IconProvider

        provider = IconProvider()
        assert provider.get_icon_uv("MESH_DATA") is None

    def test_get_icon_uv_none_for_unknown_icon(self):
        """get_icon_uv returns None for an unknown icon name."""
        from melvil.ui.gpu.icons import IconProvider

        provider = IconProvider()
        provider._loaded = True
        provider._icon_map = {"MESH_DATA": 5}
        provider._columns = 26
        provider._rows = 30
        provider._atlas_size = (832, 960)
        provider._atlas = MagicMock()  # Pretend atlas loaded.
        assert provider.get_icon_uv("NO_SUCH_ICON") is None

    def test_get_icon_uv_correct_coords(self):
        """get_icon_uv returns correct UV coordinates for a known icon."""
        from melvil.ui.gpu.icons import IconProvider, ICON_PX

        provider = IconProvider()
        provider._loaded = True
        provider._columns = 26
        provider._rows = 30
        provider._atlas_size = (832, 960)
        provider._atlas = MagicMock()
        # Place an icon at grid index 27 → col=1, row=1
        provider._icon_map = {"TEST_ICON": 27}

        uv = provider.get_icon_uv("TEST_ICON")
        assert uv is not None
        u0, v0, u1, v1 = uv

        w, h = 832, 960
        expected_u0 = (1 * ICON_PX) / w
        expected_u1 = (2 * ICON_PX) / w
        expected_v1 = 1.0 - (1 * ICON_PX) / h
        expected_v0 = 1.0 - (2 * ICON_PX) / h

        assert abs(u0 - expected_u0) < 1e-6
        assert abs(u1 - expected_u1) < 1e-6
        assert abs(v0 - expected_v0) < 1e-6
        assert abs(v1 - expected_v1) < 1e-6

    def test_get_icon_uv_none_if_row_out_of_bounds(self):
        """get_icon_uv returns None if the icon index exceeds atlas rows."""
        from melvil.ui.gpu.icons import IconProvider

        provider = IconProvider()
        provider._loaded = True
        provider._columns = 26
        provider._rows = 2  # Only 2 rows.
        provider._atlas_size = (832, 64)
        provider._atlas = MagicMock()
        # Index 100 → row 3 which is beyond rows=2
        provider._icon_map = {"BIG": 100}
        assert provider.get_icon_uv("BIG") is None

    def test_lazy_load_called_once(self):
        """Accessing .atlas triggers _load() exactly once."""
        from melvil.ui.gpu.icons import IconProvider

        provider = IconProvider()

        def _fake_load():
            provider._loaded = True

        with patch.object(provider, "_load", side_effect=_fake_load) as mock_load:
            _ = provider.atlas
            _ = provider.atlas  # Second access should NOT call _load.
            assert mock_load.call_count == 1

    def test_get_icon_uv_triggers_load(self):
        """get_icon_uv triggers _load if not yet loaded."""
        from melvil.ui.gpu.icons import IconProvider

        provider = IconProvider()
        with patch.object(provider, "_load") as mock_load:
            provider.get_icon_uv("MESH_DATA")
            assert mock_load.call_count == 1


# ---------------------------------------------------------------------------
# draw_icon helper
# ---------------------------------------------------------------------------


def _make_panel_with_icons(**overrides):
    """Create a panel with a mocked icon provider."""
    from melvil.ui.gpu.icons import IconProvider

    panel = _make_panel(**overrides)
    provider = IconProvider()
    provider._loaded = True
    provider._columns = 26
    provider._rows = 30
    provider._atlas_size = (832, 960)
    provider._atlas = MagicMock()
    provider._icon_map = {
        "ASSET_MANAGER": 1,
        "VIEWZOOM": 2,
        "ADD": 3,
        "TAG": 4,
        "MESH_DATA": 5,
    }
    panel._icon_provider = provider
    return panel


class TestDrawIcon:
    """Tests for the draw_icon helper function."""

    def test_returns_zero_for_none_icon(self):
        """draw_icon('NONE', ...) returns 0."""
        from melvil.ui.gpu import draw_icon

        panel = _make_panel_with_icons()
        panel.begin_frame()
        offset = draw_icon("NONE", (0, 0, 200, 20), 1.0, panel)
        assert offset == 0.0

    def test_returns_zero_when_no_atlas(self):
        """draw_icon returns 0 when the provider has no atlas."""
        from melvil.ui.gpu import draw_icon

        panel = _make_panel()
        panel.begin_frame()
        offset = draw_icon("MESH_DATA", (0, 0, 200, 20), 1.0, panel)
        assert offset == 0.0

    def test_returns_offset_when_icon_available(self):
        """draw_icon returns nonzero offset when icon atlas is loaded."""
        from melvil.ui.gpu import draw_icon
        from melvil.ui.gpu.constants import ICON_SIZE, WIDGET_PAD_X, scaled

        panel = _make_panel_with_icons()
        panel.begin_frame()
        offset = draw_icon("MESH_DATA", (0, 0, 200, 20), 1.0, panel)
        expected = scaled(WIDGET_PAD_X, 1.0) + scaled(ICON_SIZE, 1.0)
        assert offset == expected

    def test_returns_zero_for_unknown_icon(self):
        """draw_icon returns 0 for an icon not in the map."""
        from melvil.ui.gpu import draw_icon

        panel = _make_panel_with_icons()
        panel.begin_frame()
        offset = draw_icon("NO_SUCH_ICON", (0, 0, 200, 20), 1.0, panel)
        assert offset == 0.0

    def test_calls_draw_texture(self):
        """draw_icon calls draw_texture with atlas and UV coords."""
        from melvil.ui.gpu import draw_icon

        panel = _make_panel_with_icons()
        panel.begin_frame()
        with patch("melvil.ui.gpu.widget.draw_texture") as mock_draw:
            draw_icon("MESH_DATA", (10, 20, 200, 26), 1.0, panel)
            assert mock_draw.call_count == 1
            call_kw = mock_draw.call_args
            assert call_kw.kwargs.get("uv_rect") is not None


# ---------------------------------------------------------------------------
# Icon rendering on existing widgets
# ---------------------------------------------------------------------------


class TestLabelIcon:
    """Tests for icon rendering on GpuLabel."""

    def test_label_renders_icon(self):
        """Label with icon calls draw_texture when atlas is available."""
        from melvil.ui.gpu import GpuLabel

        panel = _make_panel_with_icons()
        panel.begin_frame()
        label = GpuLabel(text="Hello", icon="MESH_DATA")
        label.rect = (10, 20, 200, 20)
        with patch("melvil.ui.gpu.widget.draw_texture") as mock_draw:
            label.draw(1.0, True, panel)
            assert mock_draw.call_count == 1

    def test_label_no_icon_no_texture_call(self):
        """Label without icon does not call draw_texture."""
        from melvil.ui.gpu import GpuLabel

        panel = _make_panel_with_icons()
        panel.begin_frame()
        label = GpuLabel(text="Hello", icon="NONE")
        label.rect = (10, 20, 200, 20)
        with patch("melvil.ui.gpu.widget.draw_texture") as mock_draw:
            label.draw(1.0, True, panel)
            assert mock_draw.call_count == 0

    def test_label_without_atlas_no_crash(self):
        """Label with icon gracefully handles missing atlas."""
        from melvil.ui.gpu import GpuLabel

        panel = _make_panel()  # No icon provider atlas.
        panel.begin_frame()
        label = GpuLabel(text="Hello", icon="MESH_DATA")
        label.rect = (10, 20, 200, 20)
        label.draw(1.0, True, panel)  # Should not raise.


class TestButtonIcon:
    """Tests for icon rendering on GpuButton."""

    def test_button_renders_icon(self):
        """Button with icon calls draw_texture when atlas is available."""
        from melvil.ui.gpu import GpuButton

        panel = _make_panel_with_icons()
        panel.begin_frame()
        btn = GpuButton(text="Add", icon="ADD", operator_id="melvil.test")
        btn.rect = (10, 20, 200, 20)
        with patch("melvil.ui.gpu.widget.draw_texture") as mock_draw:
            btn.draw(1.0, True, panel)
            assert mock_draw.call_count == 1

    def test_button_no_icon_no_texture_call(self):
        """Button without icon does not call draw_texture."""
        from melvil.ui.gpu import GpuButton

        panel = _make_panel_with_icons()
        panel.begin_frame()
        btn = GpuButton(text="Click", icon="NONE", operator_id="melvil.test")
        btn.rect = (10, 20, 200, 20)
        with patch("melvil.ui.gpu.widget.draw_texture") as mock_draw:
            btn.draw(1.0, True, panel)
            assert mock_draw.call_count == 0


class TestIconOnlyButton:
    """Tests for icon-only button centering via draw_icon_centered."""

    def test_icon_only_button_calls_draw_icon_centered(self):
        """Button with icon and no text uses draw_icon_centered."""
        from melvil.ui.gpu import GpuButton

        panel = _make_panel_with_icons()
        panel.begin_frame()
        btn = GpuButton(text="", icon="ADD", operator_id="melvil.test")
        btn.rect = (0, 0, 40, 20)
        with patch("melvil.ui.gpu.button.draw_icon_centered") as mock_center:
            btn.draw(1.0, True, panel)
            assert mock_center.call_count == 1
            # Verify the rect passed matches the button rect.
            call_args = mock_center.call_args
            assert call_args.args[0] == "ADD"
            assert call_args.args[1] == (0, 0, 40, 20)

    def test_button_with_text_uses_left_aligned_icon(self):
        """Button with text + icon uses _draw_text_content (left-aligned)."""
        from melvil.ui.gpu import GpuButton

        panel = _make_panel_with_icons()
        panel.begin_frame()
        btn = GpuButton(text="Add", icon="ADD", operator_id="melvil.test")
        btn.rect = (0, 0, 200, 20)
        with patch("melvil.ui.gpu.button.draw_icon_centered") as mock_center:
            btn.draw(1.0, True, panel)
            mock_center.assert_not_called()

    def test_draw_icon_centered_centres_horizontally(self):
        """draw_icon_centered places icon at horizontal centre of rect."""
        from melvil.ui.gpu import draw_icon_centered
        from melvil.ui.gpu.constants import ICON_SIZE, scaled

        panel = _make_panel_with_icons()
        panel.begin_frame()
        with patch("melvil.ui.gpu.widget.draw_texture") as mock_draw:
            draw_icon_centered("ADD", (0, 0, 40, 20), 1.0, panel)
            assert mock_draw.call_count == 1
            icon_size = scaled(ICON_SIZE, 1.0)
            expected_x = (40 - icon_size) / 2
            expected_y = (20 - icon_size) / 2
            call_args = mock_draw.call_args
            assert call_args.args[1] == expected_x
            assert call_args.args[2] == expected_y

    def test_disabled_icon_only_button_draws_overlay(self):
        """Disabled icon-only button draws a disabled overlay."""
        from melvil.ui.gpu import GpuButton

        panel = _make_panel_with_icons()
        panel.begin_frame()
        btn = GpuButton(
            text="", icon="ADD", operator_id="melvil.test", enabled=False,
        )
        btn.rect = (0, 0, 40, 20)
        with patch("melvil.ui.gpu.button.draw_disabled_overlay") as mock_ov:
            btn.draw(1.0, True, panel)
            mock_ov.assert_called_once_with((0, 0, 40, 20))

    def test_enabled_icon_only_button_no_overlay(self):
        """Enabled icon-only button does not draw a disabled overlay."""
        from melvil.ui.gpu import GpuButton

        panel = _make_panel_with_icons()
        panel.begin_frame()
        btn = GpuButton(
            text="", icon="ADD", operator_id="melvil.test", enabled=True,
        )
        btn.rect = (0, 0, 40, 20)
        with patch("melvil.ui.gpu.button.draw_disabled_overlay") as mock_ov:
            btn.draw(1.0, True, panel)
            mock_ov.assert_not_called()


class TestEnumButtonsIcon:
    """Tests for icon rendering on GpuEnumButtons items."""

    def test_enum_item_renders_icon(self):
        """Enum button with item icon calls draw_icon per item."""
        from melvil.ui.gpu import GpuEnumButtons

        panel = _make_panel_with_icons()
        panel.begin_frame()
        items = [
            ("A", "First", "", "MESH_DATA"),
            ("B", "Second", "", "ADD"),
        ]
        widget = GpuEnumButtons(
            items=items,
            active_value="A",
            property_name="test",
        )
        widget.rect = (10, 20, 200, 50)
        with patch("melvil.ui.gpu.enum_buttons.draw_icon", return_value=0.0) as mock_draw:
            widget.draw(1.0, True, panel)
            assert mock_draw.call_count == 2

    def test_enum_item_none_icon_no_draw(self):
        """Enum button items with NONE icon skip draw_texture."""
        from melvil.ui.gpu import GpuEnumButtons

        panel = _make_panel_with_icons()
        panel.begin_frame()
        items = [
            ("A", "First", "", "NONE"),
            ("B", "Second", "", "NONE"),
        ]
        widget = GpuEnumButtons(
            items=items,
            active_value="A",
            property_name="test",
        )
        widget.rect = (10, 20, 200, 50)
        with patch("melvil.ui.gpu.enum_buttons.draw_icon", return_value=0.0) as mock_draw:
            widget.draw(1.0, True, panel)
            # draw_icon is still called but returns 0 for "NONE".
            for c in mock_draw.call_args_list:
                assert c[0][0] == "NONE"


# ---------------------------------------------------------------------------
# GpuTemplateIcon widget
# ---------------------------------------------------------------------------


class TestGpuTemplateIcon:
    """Tests for the GpuTemplateIcon widget."""

    def test_measure_height(self):
        """Height is ICON_SIZE * scale * s."""
        from melvil.ui.gpu import GpuTemplateIcon
        from melvil.ui.gpu.constants import ICON_SIZE, scaled

        w = GpuTemplateIcon(icon_value=42, scale=5.0)
        assert w.measure_height(1.0) == scaled(ICON_SIZE, 1.0) * 5.0
        assert w.measure_height(2.0) == scaled(ICON_SIZE, 2.0) * 5.0

    def test_no_draw_when_icon_value_zero(self):
        """icon_value=0 produces no draw calls."""
        from melvil.ui.gpu import GpuTemplateIcon

        panel = _make_panel()
        panel.begin_frame()
        w = GpuTemplateIcon(icon_value=0, scale=5.0)
        w.rect = (10, 20, 200, 80)
        with patch("melvil.ui.gpu.template_icon.draw_texture") as mock_draw:
            w.draw(1.0, True, panel)
            assert mock_draw.call_count == 0

    def test_draws_preview_texture(self):
        """Draws the preview texture when registered on the panel."""
        from melvil.ui.gpu import GpuTemplateIcon

        panel = _make_panel()
        panel.begin_frame()
        mock_tex = MagicMock()
        panel._texture_cache["/some/preview.png"] = mock_tex
        panel.register_preview(42, "/some/preview.png")

        w = GpuTemplateIcon(icon_value=42, scale=5.0)
        w.rect = (10, 20, 200, 80)
        with patch("melvil.ui.gpu.template_icon.draw_texture") as mock_draw:
            w.draw(1.0, True, panel)
            assert mock_draw.call_count == 1
            call_args = mock_draw.call_args[0]
            assert call_args[0] is mock_tex  # texture

    def test_no_draw_when_preview_not_registered(self):
        """No draw when icon_value is not in the preview registry."""
        from melvil.ui.gpu import GpuTemplateIcon

        panel = _make_panel()
        panel.begin_frame()
        w = GpuTemplateIcon(icon_value=99, scale=5.0)
        w.rect = (10, 20, 200, 80)
        with patch("melvil.ui.gpu.template_icon.draw_texture") as mock_draw:
            w.draw(1.0, True, panel)
            assert mock_draw.call_count == 0

    def test_layout_template_icon(self):
        """layout.template_icon() appends a GpuTemplateIcon widget."""
        from melvil.ui.gpu import GpuTemplateIcon

        panel = _make_panel()
        root = panel.begin_frame()
        root.template_icon(icon_value=42, scale=8.0)

        assert len(root._children) == 1
        child = root._children[0]
        assert isinstance(child, GpuTemplateIcon)
        assert child.icon_value == 42
        assert child.scale == 8.0


# ---------------------------------------------------------------------------
# Panel preview registry
# ---------------------------------------------------------------------------


class TestPanelPreviewRegistry:
    """Tests for register_preview / get_preview_texture."""

    def test_register_and_get(self):
        """Registered preview resolves to a texture via get_texture."""
        panel = _make_panel()
        mock_tex = MagicMock()
        panel._texture_cache["/img/preview.png"] = mock_tex
        panel.register_preview(42, "/img/preview.png")
        assert panel.get_preview_texture(42) is mock_tex

    def test_unregistered_returns_none(self):
        """Unregistered icon_value returns None."""
        panel = _make_panel()
        assert panel.get_preview_texture(999) is None

    def test_multiple_registrations(self):
        """Multiple previews can be registered independently."""
        panel = _make_panel()
        tex_a = MagicMock()
        tex_b = MagicMock()
        panel._texture_cache["/a.png"] = tex_a
        panel._texture_cache["/b.png"] = tex_b
        panel.register_preview(1, "/a.png")
        panel.register_preview(2, "/b.png")
        assert panel.get_preview_texture(1) is tex_a
        assert panel.get_preview_texture(2) is tex_b


# ---------------------------------------------------------------------------
# ScrollState
# ---------------------------------------------------------------------------


class TestScrollState:
    def test_default_values(self):
        from melvil.ui.gpu import ScrollState

        ss = ScrollState()
        assert ss.offset == 0
        assert ss.max_visible == 5
        assert ss.total_items == 0

    def test_mutable(self):
        from melvil.ui.gpu import ScrollState

        ss = ScrollState()
        ss.offset = 3
        ss.max_visible = 10
        ss.total_items = 50
        assert ss.offset == 3
        assert ss.max_visible == 10
        assert ss.total_items == 50


# ---------------------------------------------------------------------------
# GpuGridList
# ---------------------------------------------------------------------------


def _make_collection(n: int):
    """Create a mock PropertyGroup collection with *n* items."""
    items = []
    for i in range(n):
        item = MagicMock()
        item.name = f"item_{i}"
        item.is_active = i % 2 == 0
        items.append(item)
    coll = MagicMock()
    coll.__len__ = lambda self: len(items)
    coll.__getitem__ = lambda self, idx: items[idx]
    coll.__iter__ = lambda self: iter(items)
    return coll, items


def _make_dataptr(collection, active_index=-1):
    """Create a mock dataptr + active_dataptr pair."""
    dataptr = MagicMock()
    dataptr.my_collection = collection
    active_dataptr = MagicMock()
    active_dataptr.my_collection_index = active_index
    return dataptr, active_dataptr


class TestGpuGridListMeasureHeight:
    def test_basic_measurement(self):
        from melvil.ui.gpu import GpuGridList, WIDGET_HEIGHT, WIDGET_GAP, LIST_BORDER_PAD

        gl = GpuGridList(rows_visible=5, cell_height=WIDGET_HEIGHT)
        h = gl.measure_height(1.0)
        expected = 5 * WIDGET_HEIGHT + 4 * WIDGET_GAP + 2 * LIST_BORDER_PAD
        assert h == pytest.approx(expected)

    def test_scaled_measurement(self):
        from melvil.ui.gpu import GpuGridList, WIDGET_HEIGHT, WIDGET_GAP, LIST_BORDER_PAD

        gl = GpuGridList(rows_visible=3, cell_height=WIDGET_HEIGHT)
        h = gl.measure_height(2.0)
        expected = 3 * (WIDGET_HEIGHT * 2) + 2 * (WIDGET_GAP * 2) + 2 * (LIST_BORDER_PAD * 2)
        assert h == pytest.approx(expected)

    def test_single_row(self):
        from melvil.ui.gpu import GpuGridList, WIDGET_HEIGHT, LIST_BORDER_PAD

        gl = GpuGridList(rows_visible=1, cell_height=WIDGET_HEIGHT)
        h = gl.measure_height(1.0)
        assert h == pytest.approx(WIDGET_HEIGHT + 2 * LIST_BORDER_PAD)


class TestGpuGridListDraw:
    def _make_grid_list(self, n_items, rows=5, cols=1, active=-1):
        from melvil.ui.gpu import GpuGridList, WIDGET_HEIGHT

        coll, items = _make_collection(n_items)
        dataptr, active_dp = _make_dataptr(coll, active)

        def draw_fn(layout, item, index, is_active):
            layout.label(text=item.name)

        gl = GpuGridList(
            list_id="test_list",
            cols=cols,
            rows_visible=rows,
            cell_height=WIDGET_HEIGHT,
            dataptr=dataptr,
            propname="my_collection",
            active_dataptr=active_dp,
            active_propname="my_collection_index",
            draw_fn=draw_fn,
        )
        return gl, items, dataptr, active_dp

    def test_draw_registers_hit_rects(self):
        gl, items, _, _ = self._make_grid_list(10, rows=5)
        panel = _make_panel()
        panel.begin_frame()
        h = gl.measure_height(1.0)
        gl.rect = (0, 0, 300, h)

        with patch("melvil.ui.gpu.grid_list.gpu"):
            gl.draw(1.0, True, panel)

        # Should register 5 hit rects (rows_visible = 5).
        list_rows = [hr for hr in panel._hit_rects if hr.widget_type == "list_row"]
        assert len(list_rows) == 5

    def test_draw_hit_rects_have_correct_indices(self):
        gl, items, _, _ = self._make_grid_list(10, rows=5)
        panel = _make_panel()
        panel.begin_frame()
        h = gl.measure_height(1.0)
        gl.rect = (0, 0, 300, h)

        with patch("melvil.ui.gpu.grid_list.gpu"):
            gl.draw(1.0, True, panel)

        list_rows = [hr for hr in panel._hit_rects if hr.widget_type == "list_row"]
        indices = [hr.kwargs["index"] for hr in list_rows]
        assert indices == [0, 1, 2, 3, 4]

    def test_draw_with_scroll_offset(self):
        gl, items, _, _ = self._make_grid_list(10, rows=5)
        panel = _make_panel()
        scroll = panel._get_scroll_state("test_list")
        scroll.offset = 3
        panel.begin_frame()
        h = gl.measure_height(1.0)
        gl.rect = (0, 0, 300, h)

        with patch("melvil.ui.gpu.grid_list.gpu"):
            gl.draw(1.0, True, panel)

        list_rows = [hr for hr in panel._hit_rects if hr.widget_type == "list_row"]
        indices = [hr.kwargs["index"] for hr in list_rows]
        assert indices == [3, 4, 5, 6, 7]

    def test_draw_fewer_items_than_rows(self):
        gl, items, _, _ = self._make_grid_list(3, rows=5)
        panel = _make_panel()
        panel.begin_frame()
        h = gl.measure_height(1.0)
        gl.rect = (0, 0, 300, h)

        with patch("melvil.ui.gpu.grid_list.gpu"):
            gl.draw(1.0, True, panel)

        list_rows = [hr for hr in panel._hit_rects if hr.widget_type == "list_row"]
        assert len(list_rows) == 3

    def test_draw_calls_draw_fn_per_visible_item(self):
        from melvil.ui.gpu import GpuGridList, WIDGET_HEIGHT

        coll, items = _make_collection(10)
        dataptr, active_dp = _make_dataptr(coll, 2)
        draw_calls = []

        def draw_fn(layout, item, index, is_active):
            draw_calls.append((item.name, index, is_active))

        gl = GpuGridList(
            list_id="cb_test",
            rows_visible=3,
            cell_height=WIDGET_HEIGHT,
            dataptr=dataptr,
            propname="my_collection",
            active_dataptr=active_dp,
            active_propname="my_collection_index",
            draw_fn=draw_fn,
        )
        panel = _make_panel()
        panel.begin_frame()
        panel._list_selections["cb_test"] = 2
        gl.rect = (0, 0, 300, gl.measure_height(1.0))

        with patch("melvil.ui.gpu.grid_list.gpu"):
            gl.draw(1.0, True, panel)

        assert len(draw_calls) == 3
        assert draw_calls[0] == ("item_0", 0, False)
        assert draw_calls[1] == ("item_1", 1, False)
        assert draw_calls[2] == ("item_2", 2, True)

    def test_draw_no_draw_fn_does_nothing(self):
        from melvil.ui.gpu import GpuGridList, WIDGET_HEIGHT

        coll, _ = _make_collection(5)
        dataptr, active_dp = _make_dataptr(coll)
        gl = GpuGridList(
            list_id="no_fn",
            rows_visible=3,
            cell_height=WIDGET_HEIGHT,
            dataptr=dataptr,
            propname="my_collection",
            active_dataptr=active_dp,
            active_propname="my_collection_index",
            draw_fn=None,
        )
        panel = _make_panel()
        panel.begin_frame()
        gl.rect = (0, 0, 300, 100)

        # Should not raise.
        gl.draw(1.0, True, panel)
        assert len(panel._hit_rects) == 0

    def test_draw_active_row_uses_selection_bg(self):
        from melvil.ui.gpu import GpuGridList, WIDGET_HEIGHT
        from melvil.ui.gpu.theme import get_theme

        coll, items = _make_collection(5)
        dataptr, active_dp = _make_dataptr(coll, active_index=1)

        def draw_fn(layout, item, index, is_active):
            layout.label(text=item.name)

        gl = GpuGridList(
            list_id="sel_test",
            rows_visible=3,
            cell_height=WIDGET_HEIGHT,
            dataptr=dataptr,
            propname="my_collection",
            active_dataptr=active_dp,
            active_propname="my_collection_index",
            draw_fn=draw_fn,
        )
        panel = _make_panel()
        panel.begin_frame()
        panel._list_selections["sel_test"] = 1
        gl.rect = (0, 0, 300, gl.measure_height(1.0))

        sel_bg = get_theme().selection_bg
        with patch("melvil.ui.gpu.grid_list.draw_rect_rounded") as mock_rr:
            gl.draw(1.0, True, panel)
            found = any(
                len(c.args) >= 6 and c.args[5] == sel_bg
                for c in mock_rr.call_args_list
            )
            assert found, "selection_bg not used for active row"

    def test_draw_grid_mode_multi_column(self):
        """Grid mode with cols=2 registers correct hit rect indices."""
        from melvil.ui.gpu import GpuGridList

        coll, items = _make_collection(6)
        dataptr, active_dp = _make_dataptr(coll)

        def draw_fn(layout, item, index, is_active):
            layout.label(text=item.name)

        gl = GpuGridList(
            list_id="grid_test",
            cols=2,
            rows_visible=2,
            cell_height=40,
            dataptr=dataptr,
            propname="my_collection",
            active_dataptr=active_dp,
            active_propname="my_collection_index",
            draw_fn=draw_fn,
        )
        panel = _make_panel()
        panel.begin_frame()
        gl.rect = (0, 0, 300, gl.measure_height(1.0))

        with patch("melvil.ui.gpu.grid_list.gpu"):
            gl.draw(1.0, True, panel)

        list_rows = [hr for hr in panel._hit_rects if hr.widget_type == "list_row"]
        # 2 rows × 2 cols = 4 cells visible.
        assert len(list_rows) == 4
        indices = [hr.kwargs["index"] for hr in list_rows]
        assert indices == [0, 1, 2, 3]

    def test_hit_rects_carry_allow_deselect_false_by_default(self):
        gl, items, _, _ = self._make_grid_list(3, rows=3)
        panel = _make_panel()
        panel.begin_frame()
        gl.rect = (0, 0, 300, gl.measure_height(1.0))

        with patch("melvil.ui.gpu.grid_list.gpu"):
            gl.draw(1.0, True, panel)

        list_rows = [hr for hr in panel._hit_rects if hr.widget_type == "list_row"]
        assert all(hr.kwargs["allow_deselect"] is False for hr in list_rows)

    def test_hit_rects_carry_allow_deselect_true_when_set(self):
        from melvil.ui.gpu import GpuGridList, WIDGET_HEIGHT

        coll, items = _make_collection(3)
        dataptr, active_dp = _make_dataptr(coll)

        def draw_fn(layout, item, index, is_active):
            layout.label(text=item.name)

        gl = GpuGridList(
            list_id="desel_test",
            rows_visible=3,
            cell_height=WIDGET_HEIGHT,
            dataptr=dataptr,
            propname="my_collection",
            active_dataptr=active_dp,
            active_propname="my_collection_index",
            draw_fn=draw_fn,
            allow_deselect=True,
        )
        panel = _make_panel()
        panel.begin_frame()
        gl.rect = (0, 0, 300, gl.measure_height(1.0))

        with patch("melvil.ui.gpu.grid_list.gpu"):
            gl.draw(1.0, True, panel)

        list_rows = [hr for hr in panel._hit_rects if hr.widget_type == "list_row"]
        assert all(hr.kwargs["allow_deselect"] is True for hr in list_rows)


class TestGpuGridListHover:
    def test_hovered_row_uses_hover_bg(self):
        from melvil.ui.gpu import GpuGridList, WIDGET_HEIGHT, LIST_BORDER_PAD
        from melvil.ui.gpu.theme import get_theme

        coll, items = _make_collection(5)
        dataptr, active_dp = _make_dataptr(coll, active_index=-1)

        def draw_fn(layout, item, index, is_active):
            layout.label(text=item.name)

        gl = GpuGridList(
            list_id="hover_test",
            rows_visible=5,
            cell_height=WIDGET_HEIGHT,
            dataptr=dataptr,
            propname="my_collection",
            active_dataptr=active_dp,
            active_propname="my_collection_index",
            draw_fn=draw_fn,
        )
        panel = _make_panel()
        panel.begin_frame()
        h = gl.measure_height(1.0)
        gl.rect = (0, 0, 300, h)

        # Place mouse inside the first row (top of the list, inside padding).
        panel._mouse_pos = (5.0, h - LIST_BORDER_PAD - 2.0)

        hover_bg = get_theme().list_item_bg
        with patch("melvil.ui.gpu.grid_list.draw_rect_rounded") as mock_rr:
            gl.draw(1.0, True, panel)
            found = any(
                len(c.args) >= 6 and c.args[5] == hover_bg
                for c in mock_rr.call_args_list
            )
            assert found, "list_item_bg not used for hovered row"

    def test_active_row_draws_only_one_background(self):
        """Active row draws exactly one background rect — no double highlight."""
        from melvil.ui.gpu import GpuGridList, WIDGET_HEIGHT, LIST_BORDER_PAD

        coll, items = _make_collection(5)
        dataptr, active_dp = _make_dataptr(coll, active_index=0)

        def draw_fn(layout, item, index, is_active):
            layout.label(text=item.name)

        gl = GpuGridList(
            list_id="active_hover_test",
            rows_visible=5,
            cell_height=WIDGET_HEIGHT,
            dataptr=dataptr,
            propname="my_collection",
            active_dataptr=active_dp,
            active_propname="my_collection_index",
            draw_fn=draw_fn,
        )
        panel = _make_panel()
        panel.begin_frame()
        panel._list_selections["active_hover_test"] = 0
        h = gl.measure_height(1.0)
        gl.rect = (0, 0, 300, h)

        # Hover over the active row.
        panel._mouse_pos = (5.0, h - LIST_BORDER_PAD - 2.0)

        with patch("melvil.ui.gpu.grid_list.draw_rect_rounded") as mock_rr:
            gl.draw(1.0, True, panel)
            # Only one background rect should be drawn for the first row
            # (selection bg), not two (selection + hover).
            first_row_y = h - LIST_BORDER_PAD - WIDGET_HEIGHT
            bg_calls_for_row = [
                c for c in mock_rr.call_args_list
                if len(c.args) >= 2 and abs(c.args[1] - first_row_y) < 1.0
            ]
            assert len(bg_calls_for_row) == 1

    def test_no_hover_when_mouse_outside(self):
        from melvil.ui.gpu import GpuGridList, WIDGET_HEIGHT
        from melvil.ui.gpu.theme import get_theme

        coll, items = _make_collection(3)
        dataptr, active_dp = _make_dataptr(coll, active_index=-1)

        def draw_fn(layout, item, index, is_active):
            layout.label(text=item.name)

        gl = GpuGridList(
            list_id="no_hover",
            rows_visible=5,
            cell_height=WIDGET_HEIGHT,
            dataptr=dataptr,
            propname="my_collection",
            active_dataptr=active_dp,
            active_propname="my_collection_index",
            draw_fn=draw_fn,
        )
        panel = _make_panel()
        panel.begin_frame()
        h = gl.measure_height(1.0)
        gl.rect = (0, 0, 300, h)

        # Mouse far outside.
        panel._mouse_pos = (-999.0, -999.0)

        hover_bg = get_theme().list_item_bg
        with patch("melvil.ui.gpu.grid_list.draw_rect_rounded") as mock_rr:
            gl.draw(1.0, True, panel)
            hover_calls = [
                c for c in mock_rr.call_args_list
                if len(c.args) >= 6 and c.args[5] == hover_bg
            ]
            assert len(hover_calls) == 0


class TestGpuGridListScrollbar:
    def test_scrollbar_drawn_when_items_exceed_rows(self):
        from melvil.ui.gpu import GpuGridList, WIDGET_HEIGHT
        from melvil.ui.gpu.theme import get_theme

        coll, _ = _make_collection(10)
        dataptr, active_dp = _make_dataptr(coll)

        def draw_fn(layout, item, index, is_active):
            layout.label(text=item.name)

        gl = GpuGridList(
            list_id="sb_test",
            rows_visible=5,
            cell_height=WIDGET_HEIGHT,
            dataptr=dataptr,
            propname="my_collection",
            active_dataptr=active_dp,
            active_propname="my_collection_index",
            draw_fn=draw_fn,
        )
        panel = _make_panel()
        panel.begin_frame()
        gl.rect = (0, 0, 300, gl.measure_height(1.0))

        theme = get_theme()
        with patch("melvil.ui.gpu.grid_list.draw_rect_rounded") as mock_rr:
            gl.draw(1.0, True, panel)
            sb_calls = [
                c for c in mock_rr.call_args_list
                if len(c.args) >= 6
                and c.args[5] in (theme.scrollbar_bg, theme.scrollbar_handle)
            ]
            assert len(sb_calls) >= 2

    def test_no_scrollbar_when_items_fit(self):
        from melvil.ui.gpu import GpuGridList, WIDGET_HEIGHT

        coll, _ = _make_collection(3)
        dataptr, active_dp = _make_dataptr(coll)

        def draw_fn(layout, item, index, is_active):
            layout.label(text=item.name)

        gl = GpuGridList(
            list_id="no_sb",
            rows_visible=5,
            cell_height=WIDGET_HEIGHT,
            dataptr=dataptr,
            propname="my_collection",
            active_dataptr=active_dp,
            active_propname="my_collection_index",
            draw_fn=draw_fn,
        )
        panel = _make_panel()
        panel.begin_frame()
        gl.rect = (0, 0, 300, gl.measure_height(1.0))

        from melvil.ui.gpu.theme import get_theme

        theme = get_theme()
        with patch("melvil.ui.gpu.grid_list.draw_rect_rounded") as mock_rr:
            gl.draw(1.0, True, panel)
            sb_calls = [
                c for c in mock_rr.call_args_list
                if len(c.args) >= 6
                and c.args[5] in (theme.scrollbar_bg, theme.scrollbar_handle)
            ]
            assert len(sb_calls) == 0

    def test_scrollbar_handle_proportional_height(self):
        """Handle height is proportional to visible/total ratio."""
        from melvil.ui.gpu import GpuGridList, ScrollState, WIDGET_HEIGHT

        gl = GpuGridList(list_id="prop_test", rows_visible=5, cols=1)
        scroll = ScrollState(offset=0, max_visible=5, total_items=10)
        # 5/10 = 0.5 → handle should be ~50% of track height
        track_h = 200.0
        # Call _draw_scrollbar directly to check.
        from melvil.ui.gpu.theme import get_theme

        theme = get_theme()
        with patch("melvil.ui.gpu.grid_list.draw_rect_rounded") as mock_rr:
            gl._draw_scrollbar(0, 0, 8, track_h, scroll, 1.0, theme)
            # Second call is the handle.
            assert mock_rr.call_count == 2
            handle_call = mock_rr.call_args_list[1]
            handle_h = handle_call.args[3]  # height arg (x, y, w, h, r, color)
            assert handle_h == pytest.approx(track_h * 0.5)


# ---------------------------------------------------------------------------
# GpuGridList event handling
# ---------------------------------------------------------------------------


class TestGpuGridListHandleEvent:
    def _make_list_with_scroll(self, n_items=10, rows=5, offset=0):
        from melvil.ui.gpu import GpuGridList, WIDGET_HEIGHT

        coll, items = _make_collection(n_items)
        dataptr, active_dp = _make_dataptr(coll)
        gl = GpuGridList(
            list_id="ev_test",
            rows_visible=rows,
            cell_height=WIDGET_HEIGHT,
            dataptr=dataptr,
            propname="my_collection",
            active_dataptr=active_dp,
            active_propname="my_collection_index",
        )
        panel = _make_panel()
        scroll = panel._get_scroll_state("ev_test")
        scroll.offset = offset
        return gl, panel, scroll

    def test_scroll_down_increments_offset(self):
        gl, panel, scroll = self._make_list_with_scroll(10, 5, offset=0)
        consumed = gl.handle_event("SCROLL_DOWN", panel=panel)
        assert consumed is True
        assert scroll.offset == 1

    def test_scroll_up_decrements_offset(self):
        gl, panel, scroll = self._make_list_with_scroll(10, 5, offset=3)
        consumed = gl.handle_event("SCROLL_UP", panel=panel)
        assert consumed is True
        assert scroll.offset == 2

    def test_scroll_up_at_zero_not_consumed(self):
        gl, panel, scroll = self._make_list_with_scroll(10, 5, offset=0)
        consumed = gl.handle_event("SCROLL_UP", panel=panel)
        assert consumed is False
        assert scroll.offset == 0

    def test_scroll_down_at_max_not_consumed(self):
        gl, panel, scroll = self._make_list_with_scroll(10, 5, offset=5)
        consumed = gl.handle_event("SCROLL_DOWN", panel=panel)
        assert consumed is False
        assert scroll.offset == 5

    def test_scroll_offset_clamped(self):
        gl, panel, scroll = self._make_list_with_scroll(10, 5, offset=0)
        for _ in range(20):
            gl.handle_event("SCROLL_DOWN", panel=panel)
        assert scroll.offset == 5  # max(0, 10-5)

    def test_unknown_event_not_consumed(self):
        gl, panel, scroll = self._make_list_with_scroll(10, 5, offset=0)
        consumed = gl.handle_event("CLICK", panel=panel)
        assert consumed is False


# ---------------------------------------------------------------------------
# List drawer registry
# ---------------------------------------------------------------------------


class TestListDrawerRegistry:
    def test_register_stores_callback(self):
        panel = _make_panel()
        fn = lambda layout, item, index, is_active: None
        panel.register_list_drawer("MY_UL_list", fn)
        assert panel._list_drawers["MY_UL_list"] is fn

    def test_template_list_calls_registered_callback(self):
        from melvil.ui.gpu import GpuGridList

        panel = _make_panel()
        calls = []

        def draw_fn(layout, item, index, is_active):
            calls.append((item.name, index, is_active))

        panel.register_list_drawer("MY_UL_list", draw_fn)

        coll, items = _make_collection(5)
        dataptr, active_dp = _make_dataptr(coll, active_index=2)

        root = panel.begin_frame()
        panel._list_selections["test"] = 2
        root.template_list(
            "MY_UL_list", "test",
            dataptr, "my_collection",
            active_dp, "my_collection_index",
            rows=3,
        )
        # The child should be a GpuGridList.
        assert len(root._children) == 1
        assert isinstance(root._children[0], GpuGridList)

        # Run a frame to trigger draw.
        with patch("melvil.ui.gpu.grid_list.gpu"):
            panel.end_frame()

        assert len(calls) == 3
        assert calls[0] == ("item_0", 0, False)
        assert calls[1] == ("item_1", 1, False)
        assert calls[2] == ("item_2", 2, True)

    def test_unregistered_listtype_appends_grid_list_with_none_fn(self):
        """Unregistered listtype creates a GpuGridList with draw_fn=None."""
        from melvil.ui.gpu import GpuGridList

        panel = _make_panel()
        coll, _ = _make_collection(5)
        dataptr, active_dp = _make_dataptr(coll)

        root = panel.begin_frame()
        root.template_list(
            "UNKNOWN_UL_list", "test",
            dataptr, "my_collection",
            active_dp, "my_collection_index",
        )
        assert len(root._children) == 1
        child = root._children[0]
        assert isinstance(child, GpuGridList)
        assert child.draw_fn is None

    def test_template_list_passes_allow_deselect(self):
        from melvil.ui.gpu import GpuGridList

        panel = _make_panel()
        panel.register_list_drawer("MY_UL_list", lambda *a: None)

        coll, _ = _make_collection(3)
        dataptr, active_dp = _make_dataptr(coll)

        root = panel.begin_frame()
        root.template_list(
            "MY_UL_list", "desel",
            dataptr, "my_collection",
            active_dp, "my_collection_index",
            allow_deselect=True,
        )
        child = root._children[0]
        assert isinstance(child, GpuGridList)
        assert child.allow_deselect is True


# ---------------------------------------------------------------------------
# Scissor clipping
# ---------------------------------------------------------------------------


class TestScissorClipping:
    def test_scissor_enabled_during_draw(self):
        from melvil.ui.gpu import GpuGridList, WIDGET_HEIGHT

        coll, _ = _make_collection(10)
        dataptr, active_dp = _make_dataptr(coll)

        def draw_fn(layout, item, index, is_active):
            layout.label(text=item.name)

        gl = GpuGridList(
            list_id="scissor_test",
            rows_visible=5,
            cell_height=WIDGET_HEIGHT,
            dataptr=dataptr,
            propname="my_collection",
            active_dataptr=active_dp,
            active_propname="my_collection_index",
            draw_fn=draw_fn,
        )
        panel = _make_panel()
        panel.begin_frame()
        gl.rect = (10, 20, 300, gl.measure_height(1.0))

        mock_gpu = MagicMock()
        with patch("melvil.ui.gpu.grid_list.gpu", mock_gpu):
            gl.draw(1.0, True, panel)

        # Scissor test should have been enabled then disabled.
        calls = mock_gpu.state.scissor_test_set.call_args_list
        assert len(calls) >= 2
        assert calls[0] == call(True)
        assert calls[-1] == call(False)

    def test_scissor_rect_matches_content_area(self):
        from melvil.ui.gpu import GpuGridList, WIDGET_HEIGHT, SCROLLBAR_WIDTH, LIST_BORDER_PAD

        coll, _ = _make_collection(10)
        dataptr, active_dp = _make_dataptr(coll)

        def draw_fn(layout, item, index, is_active):
            layout.label(text=item.name)

        gl = GpuGridList(
            list_id="scissor_rect_test",
            rows_visible=5,
            cell_height=WIDGET_HEIGHT,
            dataptr=dataptr,
            propname="my_collection",
            active_dataptr=active_dp,
            active_propname="my_collection_index",
            draw_fn=draw_fn,
        )
        panel = _make_panel()
        panel.begin_frame()
        h = gl.measure_height(1.0)
        gl.rect = (10, 20, 300, h)

        mock_gpu = MagicMock()
        with patch("melvil.ui.gpu.grid_list.gpu", mock_gpu):
            gl.draw(1.0, True, panel)

        # Scissor rect should be the inner content area (inside border padding,
        # excluding scrollbar).
        scissor_call = mock_gpu.state.scissor_set.call_args
        pad = LIST_BORDER_PAD
        # 10 items > 5 rows → scrollbar present.
        sb_margin = pad
        content_w = 300 - SCROLLBAR_WIDTH - sb_margin
        expected_x = 10 + pad
        expected_y = 20 + pad
        expected_w = content_w - 2 * pad
        expected_h = h - 2 * pad
        assert scissor_call == call(int(expected_x), int(expected_y), int(expected_w), int(expected_h))


# ---------------------------------------------------------------------------
# Event bubbling (dispatch_event)
# ---------------------------------------------------------------------------


class TestEventBubbling:
    def test_dispatch_to_grid_list(self):
        """Scroll event dispatched to GpuGridList under cursor is consumed."""
        from melvil.ui.gpu import GpuGridList, WIDGET_HEIGHT

        coll, _ = _make_collection(10)
        dataptr, active_dp = _make_dataptr(coll)

        def draw_fn(layout, item, index, is_active):
            layout.label(text=item.name)

        panel = _make_panel()
        panel.register_list_drawer("MY_UL", draw_fn)

        root = panel.begin_frame()
        root.template_list(
            "MY_UL", "bubble_test",
            dataptr, "my_collection",
            active_dp, "my_collection_index",
            rows=5,
        )

        with patch("melvil.ui.gpu.grid_list.gpu"):
            panel.end_frame()

        # Grid list should have a rect after layout.
        grid_list = root._children[0]
        assert grid_list.rect is not None

        # Dispatch scroll event inside the grid list rect.
        gx, gy, gw, gh = grid_list.rect
        consumed = panel.dispatch_event(
            "SCROLL_DOWN", gx + 5, gy + 5,
        )
        assert consumed is True
        scroll = panel._get_scroll_state("bubble_test")
        assert scroll.offset == 1

    def test_dispatch_outside_panel_not_consumed(self):
        """Event outside any widget rect is not consumed."""
        panel = _make_panel()
        root = panel.begin_frame()
        root.label(text="hello")
        panel.end_frame()

        consumed = panel.dispatch_event("SCROLL_DOWN", -999, -999)
        assert consumed is False

    def test_dispatch_to_non_handling_widget(self):
        """Event dispatched to a label (non-handler) is not consumed."""
        panel = _make_panel()
        root = panel.begin_frame()
        root.label(text="hello")
        panel.end_frame()

        # Label's rect should be inside the panel.
        label = root._children[0]
        assert label.rect is not None
        lx, ly, lw, lh = label.rect
        consumed = panel.dispatch_event("SCROLL_DOWN", lx + 1, ly + 1)
        assert consumed is False

    def test_bubbling_reaches_parent(self):
        """Event on a child widget bubbles to parent layout if unhandled.

        Here we verify the path includes parent layouts.
        """
        panel = _make_panel()
        root = panel.begin_frame()
        col = root.column()
        col.label(text="nested")
        panel.end_frame()

        label = col._children[0]
        assert label.rect is not None
        lx, ly, lw, lh = label.rect

        # Build the hit path manually.
        path: list = []
        panel._build_hit_path(panel._root, lx + 1, ly + 1, path)
        # Path should contain: root → col → label.
        assert len(path) >= 3
        assert path[0] is root
        assert path[1] is col
        assert path[-1] is label

    def test_dispatch_no_root_returns_false(self):
        panel = _make_panel()
        consumed = panel.dispatch_event("SCROLL_DOWN", 0, 0)
        assert consumed is False


# ---------------------------------------------------------------------------
# GpuWidget.handle_event default
# ---------------------------------------------------------------------------


class TestWidgetHandleEvent:
    def test_default_returns_false(self):
        from melvil.ui.gpu.widget import GpuWidget

        class ConcreteWidget(GpuWidget):
            def measure_height(self, s):
                return 20

            def draw(self, s, parent_enabled, panel):
                pass

        w = ConcreteWidget()
        panel = _make_panel()
        assert w.handle_event("SCROLL_DOWN", panel=panel) is False


# ---------------------------------------------------------------------------
# GpuLayout.handle_event default
# ---------------------------------------------------------------------------


class TestLayoutHandleEvent:
    def test_default_returns_false(self):
        from melvil.ui.gpu import GpuLayout

        panel = _make_panel()
        layout = GpuLayout(panel)
        assert layout.handle_event("SCROLL_DOWN", panel=panel) is False


# ---------------------------------------------------------------------------
# Panel scroll state management
# ---------------------------------------------------------------------------


class TestPanelScrollState:
    def test_get_creates_new_state(self):
        from melvil.ui.gpu import ScrollState

        panel = _make_panel()
        ss = panel._get_scroll_state("my_list")
        assert isinstance(ss, ScrollState)
        assert ss.offset == 0

    def test_get_returns_same_instance(self):
        panel = _make_panel()
        ss1 = panel._get_scroll_state("my_list")
        ss1.offset = 7
        ss2 = panel._get_scroll_state("my_list")
        assert ss1 is ss2
        assert ss2.offset == 7

    def test_different_ids_different_states(self):
        panel = _make_panel()
        a = panel._get_scroll_state("list_a")
        b = panel._get_scroll_state("list_b")
        a.offset = 5
        assert b.offset == 0

    def test_detach_clears_scroll_states(self):
        import bpy

        panel = _make_panel()
        panel.attach(MagicMock())
        panel._get_scroll_state("test").offset = 5
        panel.detach()
        assert len(panel._scroll_states) == 0


# ---------------------------------------------------------------------------
# Icon Button
# ---------------------------------------------------------------------------


class TestGpuIconButton:
    def test_icon_button_registers_hit_rect(self):
        """icon_button inside a list row registers an icon_button HitResult."""
        from melvil.ui.gpu import GpuGridList, WIDGET_HEIGHT

        coll, items = _make_collection(3)
        dataptr, active_dp = _make_dataptr(coll)

        def draw_fn(layout, item, index, is_active):
            row = layout.row(align=True)
            row.label(text=item.name)
            row.icon_button(icon="GREASEPENCIL", button_id="rename")

        gl = GpuGridList(
            list_id="ib_test",
            rows_visible=3,
            cell_height=WIDGET_HEIGHT,
            dataptr=dataptr,
            propname="my_collection",
            active_dataptr=active_dp,
            active_propname="my_collection_index",
            draw_fn=draw_fn,
        )
        panel = _make_panel()
        panel.begin_frame()
        # Select row 0 so the icon is visible.
        panel._list_selections["ib_test"] = 0
        h = gl.measure_height(1.0)
        gl.rect = (0, 0, 300, h)

        with patch("melvil.ui.gpu.grid_list.gpu"):
            gl.draw(1.0, True, panel)

        icon_hits = [
            hr for hr in panel._hit_rects if hr.widget_type == "icon_button"
        ]
        assert len(icon_hits) == 1
        assert icon_hits[0].id == "rename"
        assert icon_hits[0].kwargs["index"] == 0
        assert icon_hits[0].kwargs["list_id"] == "ib_test"

    def test_icon_button_hidden_when_row_not_hovered_or_selected(self):
        """icon_button with show_only_on_hover does not register when row
        is neither hovered nor selected."""
        from melvil.ui.gpu import GpuGridList, WIDGET_HEIGHT

        coll, items = _make_collection(3)
        dataptr, active_dp = _make_dataptr(coll)

        def draw_fn(layout, item, index, is_active):
            row = layout.row(align=True)
            row.label(text=item.name)
            row.icon_button(icon="GREASEPENCIL", button_id="rename")

        gl = GpuGridList(
            list_id="ib_hidden",
            rows_visible=3,
            cell_height=WIDGET_HEIGHT,
            dataptr=dataptr,
            propname="my_collection",
            active_dataptr=active_dp,
            active_propname="my_collection_index",
            draw_fn=draw_fn,
        )
        panel = _make_panel()
        panel.begin_frame()
        # No selection, mouse far away.
        panel._mouse_pos = (-999, -999)
        h = gl.measure_height(1.0)
        gl.rect = (0, 0, 300, h)

        with patch("melvil.ui.gpu.grid_list.gpu"):
            gl.draw(1.0, True, panel)

        icon_hits = [
            hr for hr in panel._hit_rects if hr.widget_type == "icon_button"
        ]
        assert len(icon_hits) == 0

    def test_icon_button_shown_on_hover(self):
        """icon_button visible when row is hovered."""
        from melvil.ui.gpu import GpuGridList, WIDGET_HEIGHT, LIST_BORDER_PAD

        coll, items = _make_collection(3)
        dataptr, active_dp = _make_dataptr(coll)

        def draw_fn(layout, item, index, is_active):
            row = layout.row(align=True)
            row.label(text=item.name)
            row.icon_button(icon="GREASEPENCIL", button_id="rename")

        gl = GpuGridList(
            list_id="ib_hover",
            rows_visible=3,
            cell_height=WIDGET_HEIGHT,
            dataptr=dataptr,
            propname="my_collection",
            active_dataptr=active_dp,
            active_propname="my_collection_index",
            draw_fn=draw_fn,
        )
        panel = _make_panel()
        panel.begin_frame()
        h = gl.measure_height(1.0)
        gl.rect = (0, 0, 300, h)
        # Hover over the first row (inside padding).
        panel._mouse_pos = (5.0, h - LIST_BORDER_PAD - 2.0)

        with patch("melvil.ui.gpu.grid_list.gpu"):
            gl.draw(1.0, True, panel)

        icon_hits = [
            hr for hr in panel._hit_rects if hr.widget_type == "icon_button"
        ]
        assert len(icon_hits) == 1
        assert icon_hits[0].kwargs["index"] == 0

    def test_icon_button_hit_wins_over_list_row(self):
        """hit_test returns icon_button when mouse is over both icon and row."""
        from melvil.ui.gpu import GpuGridList, WIDGET_HEIGHT

        coll, items = _make_collection(3)
        dataptr, active_dp = _make_dataptr(coll)

        def draw_fn(layout, item, index, is_active):
            row = layout.row(align=True)
            row.label(text=item.name)
            row.icon_button(icon="GREASEPENCIL", button_id="rename")

        gl = GpuGridList(
            list_id="ib_hit",
            rows_visible=3,
            cell_height=WIDGET_HEIGHT,
            dataptr=dataptr,
            propname="my_collection",
            active_dataptr=active_dp,
            active_propname="my_collection_index",
            draw_fn=draw_fn,
        )
        panel = _make_panel()
        panel.begin_frame()
        panel._list_selections["ib_hit"] = 0
        h = gl.measure_height(1.0)
        gl.rect = (0, 0, 300, h)

        with patch("melvil.ui.gpu.grid_list.gpu"):
            gl.draw(1.0, True, panel)

        # Find the icon_button hit rect and test at its centre.
        icon_hits = [
            hr for hr in panel._hit_rects if hr.widget_type == "icon_button"
        ]
        assert len(icon_hits) == 1
        ix, iy, iw, ih = icon_hits[0].rect
        result = panel.hit_test(int(ix + iw / 2), int(iy + ih / 2))
        assert result is not None
        assert result.widget_type == "icon_button"

    def test_list_context_propagates_to_nested_layouts(self):
        """_list_context propagates through row/column/split/box."""
        panel = _make_panel()
        root = panel.begin_frame()
        root._list_context = {"list_id": "test", "index": 3}

        row = root.row()
        assert row._list_context == {"list_id": "test", "index": 3}

        col = row.column()
        assert col._list_context == {"list_id": "test", "index": 3}

        sp = col.split(factor=0.5)
        assert sp._list_context == {"list_id": "test", "index": 3}

        bx = sp.box()
        assert bx._list_context == {"list_id": "test", "index": 3}

    def test_icon_button_always_visible_when_show_only_on_hover_false(self):
        """icon_button with show_only_on_hover=False registers even when
        row is not hovered or selected."""
        from melvil.ui.gpu import GpuGridList, WIDGET_HEIGHT

        coll, items = _make_collection(3)
        dataptr, active_dp = _make_dataptr(coll)

        def draw_fn(layout, item, index, is_active):
            row = layout.row(align=True)
            row.label(text=item.name)
            row.icon_button(
                icon="GREASEPENCIL", button_id="always",
                show_only_on_hover=False,
            )

        gl = GpuGridList(
            list_id="ib_always",
            rows_visible=3,
            cell_height=WIDGET_HEIGHT,
            dataptr=dataptr,
            propname="my_collection",
            active_dataptr=active_dp,
            active_propname="my_collection_index",
            draw_fn=draw_fn,
        )
        panel = _make_panel()
        panel.begin_frame()
        panel._mouse_pos = (-999, -999)
        h = gl.measure_height(1.0)
        gl.rect = (0, 0, 300, h)

        with patch("melvil.ui.gpu.grid_list.gpu"):
            gl.draw(1.0, True, panel)

        icon_hits = [
            hr for hr in panel._hit_rects if hr.widget_type == "icon_button"
        ]
        # All 3 rows should have the icon.
        assert len(icon_hits) == 3

    def test_ghost_style_skips_hover_background(self):
        """icon_button with style='GHOST' does not draw hover background."""
        from melvil.ui.gpu import GpuGridList, WIDGET_HEIGHT

        coll, items = _make_collection(3)
        dataptr, active_dp = _make_dataptr(coll)

        def draw_fn(layout, item, index, is_active):
            row = layout.row(align=True)
            row.label(text=item.name)
            row.icon_button(
                icon="GREASEPENCIL", button_id="ghost",
                style="GHOST",
            )

        gl = GpuGridList(
            list_id="ib_ghost",
            rows_visible=3,
            cell_height=WIDGET_HEIGHT,
            dataptr=dataptr,
            propname="my_collection",
            active_dataptr=active_dp,
            active_propname="my_collection_index",
            draw_fn=draw_fn,
        )
        panel = _make_panel()
        panel.begin_frame()
        panel._list_selections["ib_ghost"] = 0
        h = gl.measure_height(1.0)
        gl.rect = (0, 0, 300, h)

        with patch("melvil.ui.gpu.grid_list.gpu"):
            gl.draw(1.0, True, panel)

        # Place mouse over the icon_button hit rect.
        icon_hits = [
            hr for hr in panel._hit_rects if hr.widget_type == "icon_button"
        ]
        assert len(icon_hits) == 1
        ix, iy, iw, ih = icon_hits[0].rect
        panel._mouse_pos = (ix + iw / 2, iy + ih / 2)

        # Re-draw and check that draw_rect_rounded is NOT called
        # from icon_button (the grid_list will still call it for row bg).
        panel.begin_frame()
        panel._list_selections["ib_ghost"] = 0
        panel._mouse_pos = (ix + iw / 2, iy + ih / 2)
        with patch("melvil.ui.gpu.grid_list.gpu"), \
             patch("melvil.ui.gpu.icon_button.draw_rect_rounded") as mock_rr:
            gl.draw(1.0, True, panel)
        mock_rr.assert_not_called()


# ---------------------------------------------------------------------------
# GpuDropdown — construction & measure
# ---------------------------------------------------------------------------


_MOCK_DROPDOWN_ITEMS = [
    ("RED", "Red", "", "NONE"),
    ("GREEN", "Green", "", "NONE"),
    ("BLUE", "Blue", "", "NONE"),
]


class TestGpuDropdown:
    def test_construction(self):
        from melvil.ui.gpu import GpuDropdown

        d = GpuDropdown(
            text="Color",
            dropdown_id="test.color",
            items=_MOCK_DROPDOWN_ITEMS,
            mode="prop",
        )
        assert d.dropdown_id == "test.color"
        assert len(d.items) == 3
        assert d.mode == "prop"

    def test_inherits_gpu_widget(self):
        from melvil.ui.gpu import GpuDropdown, GpuWidget

        assert issubclass(GpuDropdown, GpuWidget)

    def test_height_matches_widget_height(self):
        from melvil.ui.gpu import GpuDropdown, WIDGET_HEIGHT

        d = GpuDropdown(items=_MOCK_DROPDOWN_ITEMS)
        assert d.measure_height(1.0) == pytest.approx(WIDGET_HEIGHT)

    def test_display_text_from_text_field(self):
        from melvil.ui.gpu import GpuDropdown

        d = GpuDropdown(text="Choose Color", items=_MOCK_DROPDOWN_ITEMS)
        assert d._display_text() == "Choose Color"

    def test_display_text_from_prop_value(self):
        from melvil.ui.gpu import GpuDropdown

        data = MagicMock()
        data.color = "GREEN"
        d = GpuDropdown(
            items=_MOCK_DROPDOWN_ITEMS,
            mode="prop",
            data=data,
            property_name="color",
        )
        assert d._display_text() == "Green"

    def test_display_text_unknown_value(self):
        from melvil.ui.gpu import GpuDropdown

        data = MagicMock()
        data.color = "YELLOW"
        d = GpuDropdown(
            items=_MOCK_DROPDOWN_ITEMS,
            mode="prop",
            data=data,
            property_name="color",
        )
        # Falls back to empty string when no item matches.
        assert d._display_text() == ""


# ---------------------------------------------------------------------------
# GpuDropdown — drawing & hit rects
# ---------------------------------------------------------------------------


class TestGpuDropdownDraw:
    def test_draw_registers_hit_rect(self):
        from melvil.ui.gpu import GpuDropdown

        panel = _make_panel(width=200, anchor=(0, 200))
        root = panel.begin_frame()
        d = GpuDropdown(
            text="Pick",
            dropdown_id="test.dd",
            items=_MOCK_DROPDOWN_ITEMS,
        )
        root._children.append(d)
        panel.end_frame()

        hits = [hr for hr in panel._hit_rects if hr.widget_type == "dropdown"]
        assert len(hits) == 1
        assert hits[0].id == "test.dd"

    def test_draw_hit_rect_carries_items(self):
        from melvil.ui.gpu import GpuDropdown

        panel = _make_panel(width=200, anchor=(0, 200))
        root = panel.begin_frame()
        d = GpuDropdown(
            dropdown_id="test.dd",
            items=_MOCK_DROPDOWN_ITEMS,
            mode="operator",
            operator_id="melvil.set_color",
        )
        root._children.append(d)
        panel.end_frame()

        hit = [hr for hr in panel._hit_rects if hr.widget_type == "dropdown"][0]
        assert hit.kwargs["items"] == _MOCK_DROPDOWN_ITEMS
        assert hit.kwargs["mode"] == "operator"
        assert hit.kwargs["operator_id"] == "melvil.set_color"

    def test_disabled_no_hit_rect(self):
        from melvil.ui.gpu import GpuDropdown

        panel = _make_panel(width=200, anchor=(0, 200))
        root = panel.begin_frame()
        d = GpuDropdown(
            dropdown_id="test.dd",
            items=_MOCK_DROPDOWN_ITEMS,
            enabled=False,
        )
        root._children.append(d)
        panel.end_frame()

        hits = [hr for hr in panel._hit_rects if hr.widget_type == "dropdown"]
        assert len(hits) == 0

    def test_button_text_drawn(self):
        """Trigger button text is drawn via blf."""
        import blf
        from melvil.ui.gpu import GpuDropdown

        blf.draw.reset_mock()
        blf.dimensions = MagicMock(return_value=(40.0, 12.0))

        panel = _make_panel(width=200, anchor=(0, 200))
        root = panel.begin_frame()
        d = GpuDropdown(
            text="My Dropdown",
            dropdown_id="test.dd",
            items=_MOCK_DROPDOWN_ITEMS,
        )
        root._children.append(d)
        panel.end_frame()

        drawn_texts = [c.args[1] for c in blf.draw.call_args_list]
        assert "My Dropdown" in drawn_texts


# ---------------------------------------------------------------------------
# DropdownState — geometry & hit testing
# ---------------------------------------------------------------------------


class TestDropdownState:
    def test_compute_rect_below_anchor(self):
        from melvil.ui.gpu import DropdownState

        state = DropdownState(
            items=_MOCK_DROPDOWN_ITEMS,
            anchor_rect=(100.0, 200.0, 150.0, 30.0),
        )
        rect = state.compute_rect(1.0)
        # Dropdown opens below the anchor.
        assert rect[0] == 100.0  # x matches anchor
        assert rect[2] == 150.0  # w matches anchor
        assert rect[1] + rect[3] == pytest.approx(200.0)  # top edge == anchor bottom

    def test_item_rects_populated_after_draw(self):
        from melvil.ui.gpu import DropdownState

        state = DropdownState(
            items=_MOCK_DROPDOWN_ITEMS,
            anchor_rect=(50.0, 300.0, 200.0, 30.0),
        )
        state.compute_rect(1.0)

        panel = _make_panel(width=200, anchor=(0, 400))
        panel.begin_frame()
        state.draw(1.0, panel)

        assert len(state.item_rects) == 3

    def test_hit_test_returns_correct_index(self):
        from melvil.ui.gpu import DropdownState

        state = DropdownState(
            items=_MOCK_DROPDOWN_ITEMS,
            anchor_rect=(0.0, 200.0, 200.0, 30.0),
        )
        state.compute_rect(1.0)

        panel = _make_panel(width=200, anchor=(0, 300))
        panel.begin_frame()
        state.draw(1.0, panel)

        # Click in the middle of the first item rect.
        ix, iy, iw, ih = state.item_rects[0]
        assert state.hit_test(ix + iw / 2, iy + ih / 2) == 0

        # Click in the middle of the last item rect.
        lx, ly, lw, lh = state.item_rects[2]
        assert state.hit_test(lx + lw / 2, ly + lh / 2) == 2

    def test_hit_test_outside_returns_negative(self):
        from melvil.ui.gpu import DropdownState

        state = DropdownState(
            items=_MOCK_DROPDOWN_ITEMS,
            anchor_rect=(0.0, 200.0, 200.0, 30.0),
        )
        state.compute_rect(1.0)

        panel = _make_panel(width=200, anchor=(0, 300))
        panel.begin_frame()
        state.draw(1.0, panel)

        assert state.hit_test(-100, -100) == -1

    def test_is_inside(self):
        from melvil.ui.gpu import DropdownState

        state = DropdownState(
            items=_MOCK_DROPDOWN_ITEMS,
            anchor_rect=(0.0, 200.0, 200.0, 30.0),
        )
        rect = state.compute_rect(1.0)

        # Centre of the dropdown.
        cx = rect[0] + rect[2] / 2
        cy = rect[1] + rect[3] / 2
        assert state.is_inside(cx, cy) is True
        assert state.is_inside(-100, -100) is False

    def test_is_inside_none_rect(self):
        from melvil.ui.gpu import DropdownState

        state = DropdownState(
            items=_MOCK_DROPDOWN_ITEMS,
            anchor_rect=(0.0, 200.0, 200.0, 30.0),
        )
        # rect not yet computed
        assert state.is_inside(0, 0) is False

    def test_apply_selection_prop_mode(self):
        """apply_selection sets the property on data in prop mode."""
        from melvil.ui.gpu import DropdownState

        data = MagicMock()
        state = DropdownState(
            items=_MOCK_DROPDOWN_ITEMS,
            anchor_rect=(0.0, 200.0, 200.0, 30.0),
            mode="prop",
            data=data,
            property_name="color",
        )
        state.apply_selection(1)
        assert data.color == "GREEN"

    def test_apply_selection_out_of_range_ignored(self):
        """apply_selection silently ignores out-of-range indices."""
        from melvil.ui.gpu import DropdownState

        data = MagicMock(spec=[])
        state = DropdownState(
            items=_MOCK_DROPDOWN_ITEMS,
            anchor_rect=(0.0, 200.0, 200.0, 30.0),
            mode="prop",
            data=data,
            property_name="color",
        )
        state.apply_selection(-1)
        state.apply_selection(99)
        assert not hasattr(data, "color")

    def test_apply_selection_operator_mode(self):
        """apply_selection invokes the operator in operator mode."""
        from melvil.ui.gpu import DropdownState

        state = DropdownState(
            items=_MOCK_DROPDOWN_ITEMS,
            anchor_rect=(0.0, 200.0, 200.0, 30.0),
            mode="operator",
            operator_id="melvil.load_asset",
            operator_props={"extra": "val"},
            property_name="color",
        )
        mock_ns = MagicMock()
        with patch("bpy.ops", create=True) as mock_ops:
            mock_ops.melvil = mock_ns
            state.apply_selection(0)
        mock_ns.load_asset.assert_called_once_with(
            "INVOKE_DEFAULT", extra="val", color="RED",
        )

    def test_from_hit_prop_mode(self):
        """from_hit creates a correctly populated state from a HitResult."""
        from melvil.ui.gpu import DropdownState
        from melvil.ui.gpu.panel import HitResult

        hit = HitResult(
            widget_type="dropdown",
            id="test.color",
            kwargs={
                "items": _MOCK_DROPDOWN_ITEMS,
                "mode": "prop",
                "data": MagicMock(),
                "property_name": "color",
                "operator_id": "",
                "operator_props": {},
            },
            rect=(10.0, 200.0, 150.0, 30.0),
        )
        state = DropdownState.from_hit(hit, ui_scale=1.0)
        assert state.items == _MOCK_DROPDOWN_ITEMS
        assert state.mode == "prop"
        assert state.property_name == "color"
        assert state.anchor_rect == (10.0, 200.0, 150.0, 30.0)
        assert state.rect is not None  # compute_rect was called

    def test_from_hit_defaults(self):
        """from_hit handles minimal kwargs with sensible defaults."""
        from melvil.ui.gpu import DropdownState
        from melvil.ui.gpu.panel import HitResult

        hit = HitResult(
            widget_type="dropdown",
            id="test.empty",
            kwargs={"items": _MOCK_DROPDOWN_ITEMS},
            rect=(0.0, 100.0, 100.0, 20.0),
        )
        state = DropdownState.from_hit(hit, ui_scale=1.0)
        assert state.mode == "prop"
        assert state.operator_id == ""
        assert state.property_name == ""


# ---------------------------------------------------------------------------
# GpuPanel — dropdown lifecycle
# ---------------------------------------------------------------------------


class TestPanelDropdown:
    def test_initial_state_is_none(self):
        panel = _make_panel()
        assert panel.active_dropdown is None

    def test_open_and_close(self):
        from melvil.ui.gpu import DropdownState

        panel = _make_panel()
        state = DropdownState(
            items=_MOCK_DROPDOWN_ITEMS,
            anchor_rect=(0.0, 200.0, 200.0, 30.0),
        )
        panel.open_dropdown(state)
        assert panel.active_dropdown is state

        panel.close_dropdown()
        assert panel.active_dropdown is None

    def test_detach_clears_dropdown(self):
        from melvil.ui.gpu import DropdownState

        panel = _make_panel()
        state = DropdownState(
            items=_MOCK_DROPDOWN_ITEMS,
            anchor_rect=(0.0, 200.0, 200.0, 30.0),
        )
        panel.open_dropdown(state)
        panel.detach()
        assert panel.active_dropdown is None

    def test_overlay_drawn_in_end_frame(self):
        """Dropdown overlay draw is called during end_frame."""
        from melvil.ui.gpu import DropdownState

        panel = _make_panel(width=200, anchor=(0, 200))
        root = panel.begin_frame()
        root.label(text="trigger")

        state = DropdownState(
            items=_MOCK_DROPDOWN_ITEMS,
            anchor_rect=(0.0, 100.0, 200.0, 30.0),
        )
        state.compute_rect(1.0)
        panel.open_dropdown(state)
        panel.end_frame()

        # After end_frame the overlay should have populated item rects.
        assert len(state.item_rects) == 3


# ---------------------------------------------------------------------------
# layout.prop(expand=False) for ENUM → GpuDropdown
# ---------------------------------------------------------------------------


class TestPropExpandFalse:
    def test_enum_expand_false_creates_dropdown(self):
        from melvil.ui.gpu import GpuDropdown

        mock_data = _mock_enum_rna(_MOCK_ENUM_ITEMS, current_value="ALL")

        panel = _make_panel(width=200, anchor=(0, 200))
        root = panel.begin_frame()
        root.prop(mock_data, "type_filter", expand=False)

        children = [c for c in root._children if isinstance(c, GpuDropdown)]
        assert len(children) == 1
        assert children[0].mode == "prop"
        assert children[0].data is mock_data
        assert children[0].property_name == "type_filter"


# ---------------------------------------------------------------------------
# layout.operator_menu_enum
# ---------------------------------------------------------------------------


class TestOperatorMenuEnum:
    def test_appends_dropdown(self):
        from melvil.ui.gpu import GpuDropdown

        panel = _make_panel(width=200, anchor=(0, 200))
        root = panel.begin_frame()
        root.operator_menu_enum(
            "melvil.set_kit", "kit", text="Assign Kit", icon="ADD",
        )

        children = [c for c in root._children if isinstance(c, GpuDropdown)]
        assert len(children) == 1
        assert children[0].mode == "operator"
        assert children[0].operator_id == "melvil.set_kit"
        assert children[0].text == "Assign Kit"
        assert children[0].icon == "ADD"


# ===========================================================================
# EventResult
# ===========================================================================


class TestEventResult:
    def test_defaults(self):
        from melvil.ui.gpu import EventResult

        r = EventResult()
        assert r.consumed is False
        assert r.cancelled is False
        assert r.redraw is False

    def test_consumed(self):
        from melvil.ui.gpu import EventResult

        r = EventResult(consumed=True)
        assert r.consumed is True
        assert r.cancelled is False

    def test_cancelled(self):
        from melvil.ui.gpu import EventResult

        r = EventResult(cancelled=True, redraw=True)
        assert r.cancelled is True
        assert r.redraw is True


# ===========================================================================
# GpuPanel.handle_event — dropdown mode
# ===========================================================================


class TestHandleEventDropdown:
    def _make_panel_with_dropdown(self):
        from melvil.ui.gpu.dropdown import DropdownState

        panel = _make_panel()
        dd = MagicMock(spec=DropdownState)
        dd.hit_test = MagicMock(return_value=-1)
        dd.hovered_index = -1
        panel.active_dropdown = dd
        return panel, dd

    def test_mousemove_updates_hovered_index(self):
        panel, dd = self._make_panel_with_dropdown()
        dd.hit_test.return_value = 2

        result = panel.handle_event(
            _MockEvent(type="MOUSEMOVE", value="NOTHING", mouse_region_x=50, mouse_region_y=50),
        )

        dd.hit_test.assert_called_once_with(50, 50)
        assert dd.hovered_index == 2
        assert result.consumed is True
        assert result.redraw is True

    def test_esc_closes_dropdown(self):
        panel, dd = self._make_panel_with_dropdown()

        result = panel.handle_event(_MockEvent(type="ESC"))

        assert panel.active_dropdown is None
        assert result.consumed is True
        assert result.redraw is True

    def test_rightmouse_closes_dropdown(self):
        panel, dd = self._make_panel_with_dropdown()

        result = panel.handle_event(_MockEvent(type="RIGHTMOUSE"))

        assert panel.active_dropdown is None
        assert result.consumed is True

    def test_lmb_applies_selection_and_closes(self):
        panel, dd = self._make_panel_with_dropdown()
        dd.hit_test.return_value = 1

        result = panel.handle_event(
            _MockEvent(type="LEFTMOUSE", mouse_region_x=50, mouse_region_y=50),
        )

        dd.apply_selection.assert_called_once_with(1)
        assert panel.active_dropdown is None
        assert result.consumed is True
        assert result.redraw is True

    def test_lmb_miss_closes_without_selection(self):
        panel, dd = self._make_panel_with_dropdown()
        dd.hit_test.return_value = -1

        result = panel.handle_event(
            _MockEvent(type="LEFTMOUSE", mouse_region_x=50, mouse_region_y=50),
        )

        dd.apply_selection.assert_not_called()
        assert panel.active_dropdown is None

    def test_other_events_consumed_no_redraw(self):
        panel, dd = self._make_panel_with_dropdown()

        result = panel.handle_event(
            _MockEvent(type="A", value="PRESS"),
        )

        assert result.consumed is True
        # Dropdown mode consumes all events.


# ===========================================================================
# GpuPanel.handle_event — text field mode
# ===========================================================================


class TestHandleEventTextField:
    def _make_panel_with_text(self):
        panel = _make_panel()
        data = MagicMock()
        data.name = "hello"
        panel.activate_text_field("name", data)
        return panel, data

    def test_esc_cancels_text_not_panel(self):
        panel, data = self._make_panel_with_text()

        result = panel.handle_event(_MockEvent(type="ESC"))

        assert panel.active_text_field is None
        assert result.consumed is True
        assert result.cancelled is False
        assert result.redraw is True

    def test_rightmouse_cancels_text(self):
        panel, data = self._make_panel_with_text()

        result = panel.handle_event(_MockEvent(type="RIGHTMOUSE"))

        assert panel.active_text_field is None
        assert result.consumed is True
        assert result.cancelled is False

    def test_keystroke_routed_to_text_handler(self):
        panel, data = self._make_panel_with_text()
        # Clear the select-all so the character is appended.
        panel._text_selection_start = None

        result = panel.handle_event(
            _MockEvent(type="X", unicode="x"),
        )

        assert panel._text_buffer == "hellox"
        assert result.consumed is True
        assert result.redraw is True

    def test_drag_mousemove_updates(self):
        panel, data = self._make_panel_with_text()
        panel._text_dragging = True
        panel._text_drag_field_rect = (0, 0, 200, 20)

        result = panel.handle_event(
            _MockEvent(type="MOUSEMOVE", value="NOTHING", mouse_region_x=50),
        )

        assert result.consumed is True
        assert result.redraw is True

    def test_drag_release_ends(self):
        panel, data = self._make_panel_with_text()
        panel._text_dragging = True
        panel._text_drag_field_rect = (0, 0, 200, 20)

        result = panel.handle_event(
            _MockEvent(type="LEFTMOUSE", value="RELEASE"),
        )

        assert panel._text_dragging is False
        assert result.consumed is True


# ===========================================================================
# GpuPanel.handle_event — normal mode
# ===========================================================================


class TestHandleEventNormal:
    def test_esc_returns_cancelled(self):
        panel = _make_panel()

        result = panel.handle_event(_MockEvent(type="ESC"))

        assert result.cancelled is True
        assert result.redraw is True

    def test_rightmouse_returns_cancelled(self):
        panel = _make_panel()

        result = panel.handle_event(_MockEvent(type="RIGHTMOUSE"))

        assert result.cancelled is True

    def test_scroll_dispatches_event(self):
        panel = _make_panel()
        panel.dispatch_event = MagicMock(return_value=True)

        result = panel.handle_event(
            _MockEvent(type="WHEELUPMOUSE", mouse_region_x=50, mouse_region_y=50),
        )

        panel.dispatch_event.assert_called_once_with("SCROLL_UP", 50, 50)
        assert result.consumed is True
        assert result.redraw is True

    def test_scroll_down(self):
        panel = _make_panel()
        panel.dispatch_event = MagicMock(return_value=True)

        result = panel.handle_event(
            _MockEvent(type="WHEELDOWNMOUSE", mouse_region_x=10, mouse_region_y=20),
        )

        panel.dispatch_event.assert_called_once_with("SCROLL_DOWN", 10, 20)

    def test_lmb_outside_cancels(self):
        panel = _make_panel()
        # Panel has no rect, so is_inside returns False.

        result = panel.handle_event(
            _MockEvent(type="LEFTMOUSE", mouse_region_x=9999, mouse_region_y=9999),
        )

        assert result.cancelled is True

    def test_lmb_text_field_activates(self):
        from melvil.ui.gpu import HitResult

        panel = _make_panel()
        data = MagicMock()
        data.name = "test"
        panel._panel_rect = (0, 0, 300, 200)
        panel._hit_rects.append(HitResult(
            widget_type="text_field",
            id="name",
            kwargs={"data": data},
            rect=(10, 10, 100, 20),
        ))

        result = panel.handle_event(
            _MockEvent(type="LEFTMOUSE", mouse_region_x=50, mouse_region_y=15),
        )

        assert panel.active_text_field == "name"
        assert result.consumed is True
        assert result.redraw is True

    def test_lmb_operator_invokes(self):
        from melvil.ui.gpu import HitResult

        panel = _make_panel()
        panel._panel_rect = (0, 0, 300, 200)
        panel._hit_rects.append(HitResult(
            widget_type="operator",
            id="melvil.save",
            kwargs={},
            rect=(10, 10, 100, 20),
        ))

        result = panel.handle_event(
            _MockEvent(type="LEFTMOUSE", mouse_region_x=50, mouse_region_y=15),
        )

        # Operator is called via bpy.ops (mocked); just check consumed.
        assert result.consumed is True

    def test_lmb_dropdown_opens(self):
        from melvil.ui.gpu import HitResult

        panel = _make_panel()
        panel._panel_rect = (0, 0, 300, 200)
        panel._hit_rects.append(HitResult(
            widget_type="dropdown",
            id="my_enum",
            kwargs={
                "data": MagicMock(),
                "items": [("A", "A", ""), ("B", "B", "")],
                "mode": "prop",
            },
            rect=(10, 10, 100, 20),
        ))

        result = panel.handle_event(
            _MockEvent(type="LEFTMOUSE", mouse_region_x=50, mouse_region_y=15),
        )

        assert panel.active_dropdown is not None
        assert result.consumed is True
        assert result.redraw is True

    def test_lmb_prop_sets_value(self):
        from melvil.ui.gpu import HitResult

        panel = _make_panel()
        data = MagicMock()
        panel._panel_rect = (0, 0, 300, 200)
        panel._hit_rects.append(HitResult(
            widget_type="prop",
            id="my_prop",
            kwargs={"data": data, "value": 42},
            rect=(10, 10, 100, 20),
        ))

        result = panel.handle_event(
            _MockEvent(type="LEFTMOUSE", mouse_region_x=50, mouse_region_y=15),
        )

        assert data.my_prop == 42
        assert result.consumed is True

    def test_lmb_list_row_sets_index(self):
        from melvil.ui.gpu import HitResult

        panel = _make_panel()
        data = MagicMock()
        panel._panel_rect = (0, 0, 300, 200)
        panel._hit_rects.append(HitResult(
            widget_type="list_row",
            id="items",
            kwargs={
                "active_dataptr": data,
                "active_propname": "active_index",
                "index": 2,
                "list_id": "my_list",
            },
            rect=(10, 10, 100, 20),
        ))

        result = panel.handle_event(
            _MockEvent(type="LEFTMOUSE", mouse_region_x=50, mouse_region_y=15),
        )

        assert data.active_index == 2
        assert panel._list_selections["my_list"] == 2
        assert result.consumed is True
        assert result.redraw is True

    def test_lmb_list_row_deselect_toggle(self):
        from melvil.ui.gpu import HitResult

        panel = _make_panel()
        data = MagicMock()
        panel._panel_rect = (0, 0, 300, 200)
        panel._list_selections["my_list"] = 2
        panel._hit_rects.append(HitResult(
            widget_type="list_row",
            id="items",
            kwargs={
                "active_dataptr": data,
                "active_propname": "active_index",
                "index": 2,
                "list_id": "my_list",
                "allow_deselect": True,
            },
            rect=(10, 10, 100, 20),
        ))

        result = panel.handle_event(
            _MockEvent(type="LEFTMOUSE", mouse_region_x=50, mouse_region_y=15),
        )

        assert panel._list_selections["my_list"] == -1
        assert result.consumed is True


# ===========================================================================
# GpuPanel.register_widget_handler
# ===========================================================================


class TestRegisterWidgetHandler:
    def test_custom_handler_called(self):
        from melvil.ui.gpu import HitResult, EventResult

        panel = _make_panel()
        panel._panel_rect = (0, 0, 300, 200)
        handler = MagicMock(return_value=EventResult(consumed=True, redraw=True))
        panel.register_widget_handler("icon_button", handler)
        panel._hit_rects.append(HitResult(
            widget_type="icon_button",
            id="my_button",
            kwargs={"index": 0},
            rect=(10, 10, 100, 20),
        ))

        result = panel.handle_event(
            _MockEvent(type="LEFTMOUSE", mouse_region_x=50, mouse_region_y=15),
        )

        handler.assert_called_once()
        assert handler.call_args[0][0].id == "my_button"
        assert result.consumed is True
        assert result.redraw is True

    def test_unregistered_widget_type_consumed(self):
        from melvil.ui.gpu import HitResult

        panel = _make_panel()
        panel._panel_rect = (0, 0, 300, 200)
        panel._hit_rects.append(HitResult(
            widget_type="custom_unknown",
            id="x",
            kwargs={},
            rect=(10, 10, 100, 20),
        ))

        result = panel.handle_event(
            _MockEvent(type="LEFTMOUSE", mouse_region_x=50, mouse_region_y=15),
        )

        assert result.consumed is True
