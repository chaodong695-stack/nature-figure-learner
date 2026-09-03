from __future__ import annotations

from pathlib import Path

from ..models import ChartType, FigurePattern, MatrixMockData, MockDataResult, RenderResult
from .base import FigureRenderer, render_common


class HeatmapRenderer(FigureRenderer):
    renderer_id = "heatmap"
    supported_types = frozenset({ChartType.HEATMAP})

    def render(self, pattern: FigurePattern, mock_data: MockDataResult, output_dir: Path) -> RenderResult:
        def draw(axes, payload: MatrixMockData, palette):
            from matplotlib.colors import LinearSegmentedColormap

            cmap = LinearSegmentedColormap.from_list("figure_kb_palette", palette)
            for ax in axes:
                image = ax.imshow(payload.matrix, cmap=cmap, aspect="auto")
                ax.set_title(pattern.chart_type.value)
                ax.figure.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
        return render_common(self.renderer_id, pattern, mock_data, output_dir, "matrix", draw)


__all__ = ["HeatmapRenderer"]
