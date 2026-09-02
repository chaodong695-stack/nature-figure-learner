from __future__ import annotations

from pathlib import Path

from ..models import ChartType, FigurePattern, MockDataResult, RenderResult, RenderStatus
from .base import FigureRenderer
from .bar import BarRenderer
from .distribution import DistributionRenderer
from .heatmap import HeatmapRenderer
from .line import LineRenderer
from .scatter import ScatterRenderer


class DuplicateRendererError(ValueError):
    """Raised when a chart type already has a renderer mapping."""


class RendererRegistry:
    def __init__(self) -> None:
        self._renderers: dict[ChartType, FigureRenderer] = {}

    def register(self, renderer: FigureRenderer) -> None:
        collisions = [chart_type for chart_type in renderer.supported_types if chart_type in self._renderers]
        if collisions:
            names = ", ".join(chart_type.value for chart_type in sorted(collisions, key=lambda item: item.value))
            raise DuplicateRendererError(f"renderer collision for chart types: {names}")
        for chart_type in renderer.supported_types:
            self._renderers[chart_type] = renderer

    def get(self, chart_type: ChartType | str) -> FigureRenderer | None:
        try:
            chart_type = ChartType(chart_type)
        except (TypeError, ValueError):
            return None
        return self._renderers.get(chart_type)


def build_default_registry() -> RendererRegistry:
    registry = RendererRegistry()
    for renderer in (BarRenderer(), LineRenderer(), ScatterRenderer(), HeatmapRenderer(), DistributionRenderer()):
        registry.register(renderer)
    return registry


def render_pattern(
    pattern: FigurePattern,
    mock_data: MockDataResult | None,
    output_dir: Path,
    registry: RendererRegistry | None = None,
) -> RenderResult:
    registry = build_default_registry() if registry is None else registry
    renderer = registry.get(pattern.chart_type)
    if renderer is None:
        return RenderResult(
            pattern_id=pattern.id,
            renderer_id="none",
            status=RenderStatus.UNSUPPORTED,
            metadata={"chart_type": pattern.chart_type.value},
        )
    return renderer.render(pattern, mock_data, output_dir)


__all__ = ["DuplicateRendererError", "RendererRegistry", "build_default_registry", "render_pattern"]
