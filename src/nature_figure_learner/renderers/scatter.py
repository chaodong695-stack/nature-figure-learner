from __future__ import annotations

from pathlib import Path

from ..models import ChartType, FigurePattern, MockDataResult, RenderResult, ScatterMockData
from .base import FigureRenderer, render_common


class ScatterRenderer(FigureRenderer):
    renderer_id = "scatter"
    supported_types = frozenset({ChartType.SCATTER, ChartType.BUBBLE})

    def render(self, pattern: FigurePattern, mock_data: MockDataResult, output_dir: Path) -> RenderResult:
        def draw(axes, payload: ScatterMockData, palette):
            for ax in axes:
                sizes = payload.size if pattern.chart_type is ChartType.BUBBLE and payload.size else 35
                ax.scatter(payload.x, payload.y, s=sizes, color=palette[0], alpha=0.8, edgecolors="white", linewidths=0.4)
                ax.set_title(pattern.chart_type.value)
        return render_common(self.renderer_id, pattern, mock_data, output_dir, "scatter", draw)


__all__ = ["ScatterRenderer"]
