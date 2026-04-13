"""Conditional logger for the GPU UI toolkit."""

from __future__ import annotations

import os


class GpuUiLogger:
    """Conditional logger controlled by the ``GPU_UI_LOG`` env var."""

    def __init__(self) -> None:
        val = os.environ.get("GPU_UI_LOG", "0")
        self._enabled = val not in ("", "0")

    def log(self, msg: str) -> None:
        if self._enabled:
            print(f"[gpu_ui] {msg}")


_logger = GpuUiLogger()
