"""Deterministic Matplotlib adapters for the supported figure families."""

from .bar import BarRenderer
from .base import FigureRenderer
from .distribution import DistributionRenderer
from .heatmap import HeatmapRenderer
from .line import LineRenderer
from .registry import DuplicateRendererError, RendererRegistry, build_default_registry, render_pattern
from .scatter import ScatterRenderer

__all__ = [
    "BarRenderer",
    "DistributionRenderer",
    "FigureRenderer",
    "HeatmapRenderer",
    "LineRenderer",
    "ScatterRenderer",
    "DuplicateRendererError",
    "RendererRegistry",
    "build_default_registry",
    "render_pattern",
]
