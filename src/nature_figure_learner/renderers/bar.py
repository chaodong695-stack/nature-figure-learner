from __future__ import annotations

from pathlib import Path

from ..models import BarMockData, ChartType, FigurePattern, MockDataResult, RenderResult
from .base import FigureRenderer, render_common


class BarRenderer(FigureRenderer):
    renderer_id = "bar"
    supported_types = frozenset({ChartType.GROUPED_BAR, ChartType.STACKED_BAR, ChartType.HORIZONTAL_BAR})

    def render(self, pattern: FigurePattern, mock_data: MockDataResult, output_dir: Path) -> RenderResult:
        def draw(axes, payload: BarMockData, palette):
            import numpy as np
            values = np.asarray(payload.values, dtype=float)
            for ax in axes:
                positions = np.arange(len(payload.categories))
                if pattern.chart_type is ChartType.HORIZONTAL_BAR:
                    left = np.zeros(len(positions))
                    for group, vals in zip(payload.groups, values.T):
                        ax.barh(positions, vals, left=left, color=palette[len(ax.containers) % len(palette)], label=group)
                        left += vals
                    ax.set_yticks(positions, payload.categories)
                elif pattern.chart_type is ChartType.STACKED_BAR:
                    bottom = np.zeros(len(positions))
                    for index, (group, vals) in enumerate(zip(payload.groups, values.T)):
                        ax.bar(positions, vals, bottom=bottom, color=palette[index % len(palette)], label=group)
                        bottom += vals
                    ax.set_xticks(positions, payload.categories, rotation=30, ha="right")
                else:
                    width = 0.8 / max(1, values.shape[1])
                    for index, (group, vals) in enumerate(zip(payload.groups, values.T)):
                        ax.bar(positions + (index - (values.shape[1] - 1) / 2) * width, vals, width=width, color=palette[index % len(palette)], label=group)
                    ax.set_xticks(positions, payload.categories, rotation=30, ha="right")
                ax.legend(fontsize=7)
                ax.set_title(pattern.chart_type.value)
        return render_common(self.renderer_id, pattern, mock_data, output_dir, "bar", draw)


__all__ = ["BarRenderer"]
