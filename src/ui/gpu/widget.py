"""Base widget class for the GPU UI toolkit."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class GpuWidget:
    """Base class for leaf widgets stored as children of :class:`GpuLayout`.

    Subclasses implement :meth:`measure_height` and :meth:`draw` to define
    their own measurement and rendering behaviour.
    """

    text: str = ""
    icon: str = "NONE"
    enabled: bool = True
    alert: bool = False

    # Assigned during the position pass.
    rect: tuple[float, float, float, float] | None = None

    def measure_height(self, s: float) -> float:
        """Return the height of this widget at UI scale *s*."""
        raise NotImplementedError

    def draw(self, s: float, parent_enabled: bool) -> None:
        """Draw this widget.  Called during the draw pass."""
        raise NotImplementedError

    @property
    def is_separator(self) -> bool:
        """Return ``True`` if this widget acts as a separator for gap logic."""
        return False
