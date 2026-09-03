from __future__ import annotations

from pathlib import Path

from ..models import ChartType, DistributionMockData, FigurePattern, MockDataResult, RenderResult
from .base import FigureRenderer, render_common


class DistributionRenderer(FigureRenderer):
    renderer_id = "distribution"
    supported_types = frozenset({ChartType.VIOLIN, ChartType.BOX})

    def render(self, pattern: FigurePattern, mock_data: MockDataResult, output_dir: Path) -> RenderResult:
        def draw(axes, payload: DistributionMockData, palette):
            for ax in axes:
                if pattern.chart_type is ChartType.VIOLIN:
                    parts = ax.violinplot(payload.distributions, showmeans=True)
                    for index, body in enumerate(parts["bodies"]):
                        body.set_facecolor(palette[index % len(palette)])
                        body.set_alpha(0.75)
                else:
                    box = ax.boxplot(payload.distributions, patch_artist=True)
                    for index, patch in enumerate(box["boxes"]):
                        patch.set_facecolor(palette[index % len(palette)])
                ax.set_xticks(range(1, len(payload.categories) + 1), payload.categories, rotation=30, ha="right")
                ax.set_title(pattern.chart_type.value)
        return render_common(self.renderer_id, pattern, mock_data, output_dir, "distribution", draw)


__all__ = ["DistributionRenderer"]
