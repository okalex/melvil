"""
Custom GPU-drawn scrollable grid/list component.

Replaces ``template_list`` for card-style UIs where custom selection
highlights, hover states, and scroll capture are needed.  Renders via
``gpu`` and ``blf`` inside a popup operator's ``draw()`` method.

See projects/005-grid-list.md for the full design spec.
"""

from __future__ import annotations

# TODO Phase 1: GPU draw primitives (draw_rect, draw_rect_outline)
# TODO Phase 1: Layout constants (CARD_W, CARD_H, colors, fonts)
# TODO Phase 1: draw_grid() function
# TODO Phase 2: MelvilGridScrollProps PropertyGroup
# TODO Phase 2: MELVIL_OT_grid_scroll_nav operator
# TODO Phase 2: hit_test / is_over_grid helpers
# TODO Phase 3: Selection & hover highlight
# TODO Phase 4: Preview image rendering
# TODO Phase 5: Grid/list layout toggle
