import copy
import json
import tempfile
import unittest
from pathlib import Path

from nature_figure_learner.models import (
    ChartType,
    ColorScheme,
    FigurePattern,
    IndexEntry,
    LayoutArchetype,
    QuerySpec,
    SourceType,
)
from nature_figure_learner.query import query_entries, query_kb
from nature_figure_learner.repository import serialize_pattern_document


def make_pattern(pattern_id="pattern-001", **updates):
    data = {
        "id": pattern_id,
        "source_type": "image",
        "source_journal": "Nature Methods",
        "source_year": 2024,
        "chart_type": "grouped-bar",
        "layout_archetype": "quantitative-grid",
        "panel_count": 1,
        "color_scheme": "nature-nmi-pastel",
        "tags": ["Cell Biology", "benchmark"],
        "quality_rating": 4.0,
        "validation_score": 4,
        "application_count": 2,
        "analysis_date": "2026-08-31",
    }
    data.update(updates)
    return FigurePattern.model_validate(data)


def make_entry(pattern_id="pattern-001", **updates):
    return IndexEntry.from_pattern(make_pattern(pattern_id, **updates), "patterns/x.md")


class QueryEntriesTests(unittest.TestCase):
    def test_default_order_is_stable_evidence_order(self):
        entries = [
            make_entry("z-last", quality_rating=5, validation_score=5, application_count=1),
            make_entry("a-first", quality_rating=5, validation_score=5, application_count=1),
            make_entry("low", quality_rating=3, validation_score=5, application_count=10),
        ]
        result = query_entries(entries, QuerySpec(limit=5))
        self.assertEqual([m.entry.id for m in result.matches], ["a-first", "z-last", "low"])

    def test_filters_casefolded_journal_and_tags(self):
        result = query_entries(
            [make_entry()],
            QuerySpec(journals=["nature methods"], tags_all=["CELL BIOLOGY"]),
        )
        self.assertEqual(result.total_matches, 1)

    def test_missing_score_fails_minimum_filter(self):
        entries = [make_entry("missing-validation", validation_score=None), make_entry()]
        result = query_entries(entries, QuerySpec(min_validation=4))
        self.assertEqual([m.entry.id for m in result.matches], ["pattern-001"])

    def test_similarity_uses_fixed_weights_without_mutating_entries(self):
        entries = [
            make_entry("pattern-001", tags=["a", "b"]),
            make_entry("pattern-002", tags=["a", "c"]),
        ]
        before = copy.deepcopy(entries)
        result = query_entries(entries, QuerySpec(reference_id="pattern-001"))
        self.assertAlmostEqual(result.matches[0].similarity_score, 1.0)
        self.assertAlmostEqual(result.matches[1].similarity_score, 0.35 + 0.25 + 0.20 + 0.20 * (1 / 3))
        self.assertEqual(entries, before)

    def test_no_matches_is_successful_empty_result(self):
        result = query_entries([make_entry()], QuerySpec(chart_types=["sankey"]))
        self.assertEqual(result.total_matches, 0)
        self.assertEqual(result.matches, [])

    def test_limit_marks_truncated(self):
        result = query_entries([make_entry("aa"), make_entry("bb")], QuerySpec(limit=1))
        self.assertEqual(result.returned_count, 1)
        self.assertTrue(result.truncated)

    def test_reference_id_missing_is_structured_error(self):
        result = query_entries([make_entry()], QuerySpec(reference_id="missing"))
        self.assertIsNotNone(result.error)
        self.assertEqual(result.error.code, "QUERY_REFERENCE_NOT_FOUND")


class QueryKBTests(unittest.TestCase):
    def test_corrupt_index_falls_back_to_markdown_without_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pattern = make_pattern()
            source = root / "patterns" / "chart-type" / "grouped-bar" / "pattern-001.md"
            source.parent.mkdir(parents=True)
            source.write_text(serialize_pattern_document(pattern, "narrative\n"), encoding="utf-8")
            index = root / "index.json"
            index.write_text("not json", encoding="utf-8")
            result = query_kb(root, QuerySpec())
            self.assertEqual(result.total_matches, 1)
            self.assertTrue(result.warnings)
            self.assertEqual(index.read_text(encoding="utf-8"), "not json")

    def test_invalid_markdown_is_warning(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "patterns" / "chart-type" / "grouped-bar" / "bad.md"
            source.parent.mkdir(parents=True)
            source.write_text("---\ninvalid: true\n---\n", encoding="utf-8")
            result = query_kb(root, QuerySpec())
            self.assertEqual(result.total_matches, 0)
            self.assertTrue(result.warnings)


if __name__ == "__main__":
    unittest.main()
