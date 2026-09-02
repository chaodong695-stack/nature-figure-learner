from __future__ import annotations

from pathlib import Path

from ..models import ChartType, FigurePattern, LineMockData, MockDataResult, RenderResult
from .base import FigureRenderer, render_common


class LineRenderer(FigureRenderer):
    renderer_id = "line"
    supported_types = frozenset({ChartType.LINE_TREND, ChartType.MULTI_LINE})

    def render(self, pattern: FigurePattern, mock_data: MockDataResult, output_dir: Path) -> RenderResult:
        def draw(axes, payload: LineMockData, palette):
            for ax in axes:
                for index, ys in enumerate(payload.y):
                    label = payload.labels[index] if index < len(payload.labels) else f"Series {index + 1}"
                    ax.plot(payload.x, ys, color=palette[index % len(palette)], linewidth=1.8, label=label)
                ax.set_title(pattern.chart_type.value)
                if len(payload.y) > 1:
                    ax.legend(fontsize=7)
        return render_common(self.renderer_id, pattern, mock_data, output_dir, "line", draw)


__all__ = ["LineRenderer"]
