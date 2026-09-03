"""Small typed-fixture helpers shared by package tests."""

from pathlib import Path

from nature_figure_learner.models import FigurePattern


def valid_pattern_data(**updates):
    """Return a valid FigurePattern payload, with caller-provided overrides."""
    data = {
        "id": "pattern-001",
        "source_type": "image",
        "source_doi": " https://doi.org/10.1038/ABC.123 ",
        "source_figure": " Figure 3 ",
        "chart_type": "grouped-bar",
        "layout_archetype": "quantitative-grid",
        "panel_count": 3,
        "color_scheme": "nature-nmi-pastel",
        "extracted_colors": ["#aabbcc"],
        "analysis_date": "2026-08-31",
    }
    data.update(updates)
    return data


def make_pattern(**updates) -> FigurePattern:
    """Return a validated pattern suitable for repository fixtures."""
    return FigurePattern.model_validate(valid_pattern_data(**updates))


def write_pattern_fixture(
    kb_path: Path, pattern: FigurePattern, narrative: str = "# Analysis\n"
) -> Path:
    """Write a validated temporary-KB fixture through the public serializer."""
    from nature_figure_learner.repository import (
        pattern_path,
        serialize_pattern_document,
    )

    destination = pattern_path(kb_path, pattern)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        serialize_pattern_document(pattern, narrative), encoding="utf-8"
    )
    return destination
