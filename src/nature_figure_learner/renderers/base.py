"""Base protocol and shared deterministic Matplotlib helpers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, ClassVar, Callable

import matplotlib

matplotlib.use("Agg")
import matplotlib.font_manager as font_manager
import matplotlib.pyplot as plt

from ..models import (
    CLIError,
    CLIWarning,
    ChartType,
    FigurePattern,
    MockDataResult,
    RenderResult,
    RenderStatus,
)


FALLBACK_PALETTE = ("#4C78A8", "#F58518", "#54A24B", "#E45756", "#72B7B2")


class FigureRenderer(ABC):
    renderer_id: ClassVar[str]
    supported_types: ClassVar[frozenset[ChartType]]

    @abstractmethod
    def render(
        self,
        pattern: FigurePattern,
        mock_data: MockDataResult,
        output_dir: Path,
    ) -> RenderResult:
        raise NotImplementedError


def _settings(pattern: FigurePattern) -> tuple[list[str], str, list[CLIWarning], dict[str, Any]]:
    palette = list(pattern.extracted_colors) or list(FALLBACK_PALETTE)
    warnings: list[CLIWarning] = []
    requested = pattern.font_family.value if hasattr(pattern.font_family, "value") else pattern.font_family
    requested = requested or "DejaVu Sans"
    try:
        font_manager.findfont(requested, fallback_to_default=False)
        effective = requested
    except (ValueError, RuntimeError):
        effective = "DejaVu Sans"
        warnings.append(CLIWarning(code="FONT_FALLBACK", message=f"Font '{requested}' unavailable; using DejaVu Sans", details={"requested": requested, "effective": effective}))
    metadata = {
        "effective_palette": palette,
        "font_family": effective,
        "requested_font_family": requested,
        "layout": {"figsize": [float(x) for x in (pattern.figsize or (4.0, 3.0))], "panel_count": pattern.panel_count},
        "panel_count": pattern.panel_count,
    }
    return palette, effective, warnings, metadata


def _axes(pattern: FigurePattern):
    count = pattern.panel_count
    cols = max(1, int(count**0.5))
    while cols * cols < count:
        cols += 1
    rows = (count + cols - 1) // cols
    base_w, base_h = pattern.figsize or (4.0, 3.0)
    figure, axes = plt.subplots(rows, cols, figsize=(base_w * cols, base_h * rows), squeeze=False)
    flat = list(axes.flat)
    for extra in flat[count:]:
        extra.set_visible(False)
    return figure, flat[:count]


def render_common(
    renderer_id: str,
    pattern: FigurePattern,
    mock_data: MockDataResult | None,
    output_dir: Path,
    expected_kind: str,
    draw: Callable[[list[Any], Any, list[str]], None],
) -> RenderResult:
    """Run adapter boilerplate and return errors as data instead of raising."""
    if mock_data is None or mock_data.status.value != "success" or mock_data.data is None:
        return RenderResult(pattern_id=pattern.id, renderer_id=renderer_id, status=RenderStatus.ERROR,
                            error=CLIError(type="RenderInputError", code="MOCK_DATA_MISSING", message="successful typed mock data is required"))
    payload = mock_data.data
    if getattr(payload, "kind", None) != expected_kind:
        return RenderResult(pattern_id=pattern.id, renderer_id=renderer_id, status=RenderStatus.ERROR,
                            error=CLIError(type="RenderInputError", code="PAYLOAD_KIND_MISMATCH", message=f"expected {expected_kind} payload", details={"actual_kind": getattr(payload, "kind", None)}))
    figure = None
    try:
        palette, font_name, warnings, metadata = _settings(pattern)
        with matplotlib.rc_context({"font.family": [font_name]}):
            figure, axes = _axes(pattern)
            draw(axes, payload, palette)
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file = output_dir / f"{pattern.id}.png"
            figure.savefig(output_file, dpi=pattern.dpi or 150, format="png")
            return RenderResult(pattern_id=pattern.id, renderer_id=renderer_id, status=RenderStatus.SUCCESS,
                                output_file=str(output_file), metadata=metadata, warnings=warnings)
    except Exception as exc:
        return RenderResult(pattern_id=pattern.id, renderer_id=renderer_id, status=RenderStatus.ERROR,
                            error=CLIError(type=type(exc).__name__, code="RENDER_FAILED", message=str(exc)))
    finally:
        if figure is not None:
            plt.close(figure)


__all__ = ["FigureRenderer", "render_common", "FALLBACK_PALETTE"]
