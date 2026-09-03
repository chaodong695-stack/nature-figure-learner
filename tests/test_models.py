import unittest

from pydantic import ValidationError

import nature_figure_learner.models as models
from nature_figure_learner.models import FigurePattern, IndexEntry
from tests.helpers import valid_pattern_data


class FigurePatternTests(unittest.TestCase):
    def test_normalizes_doi_figure_and_colors(self):
        pattern = FigurePattern.model_validate(valid_pattern_data())

        self.assertEqual(pattern.source_doi, "10.1038/abc.123")
        self.assertEqual(pattern.source_figure, "Figure 3")
        self.assertEqual(pattern.extracted_colors, ["#AABBCC"])

    def test_rejects_unknown_fields(self):
        with self.assertRaises(ValidationError):
            FigurePattern.model_validate(valid_pattern_data(unknown_key="value"))

    def test_other_chart_requires_description(self):
        with self.assertRaises(ValidationError):
            FigurePattern.model_validate(valid_pattern_data(chart_type="other"))

    def test_novel_pattern_requires_name(self):
        with self.assertRaises(ValidationError):
            FigurePattern.model_validate(valid_pattern_data(novel_pattern=True))

    def test_legacy_entry_defaults_schema_version(self):
        pattern = FigurePattern.model_validate(valid_pattern_data())

        self.assertEqual(pattern.schema_version, "1.0")

    def test_rejects_path_traversal_in_id(self):
        with self.assertRaises(ValidationError):
            FigurePattern.model_validate(valid_pattern_data(id="../pattern-001"))

    def test_rejects_invalid_numeric_bounds(self):
        invalid_updates = (
            {"panel_count": 0},
            {"source_year": 1599},
            {"source_year": 2201},
            {"quality_rating": 0},
            {"quality_rating": 6},
            {"validation_score": 0},
            {"validation_score": 6},
            {"application_count": -1},
            {"base_font_size_pt": 0},
            {"base_font_size_pt": 73},
            {"matched_nature_figure_pattern": 0},
            {"matched_nature_figure_pattern": 17},
            {"dpi": 71},
            {"dpi": 2401},
        )

        for updates in invalid_updates:
            with self.subTest(updates=updates), self.assertRaises(ValidationError):
                FigurePattern.model_validate(valid_pattern_data(**updates))

    def test_rejects_invalid_enum_values(self):
        invalid_updates = (
            {"chart_type": "not-a-chart"},
            {"layout_archetype": "not-a-layout"},
            {"color_scheme": "not-a-scheme"},
        )

        for updates in invalid_updates:
            with self.subTest(updates=updates), self.assertRaises(ValidationError):
                FigurePattern.model_validate(valid_pattern_data(**updates))

    def test_rejects_invalid_hex_color(self):
        for color in ("aabbcc", "#ABC", "#AABBCCDD", "#GGGGGG"):
            with self.subTest(color=color), self.assertRaises(ValidationError):
                FigurePattern.model_validate(valid_pattern_data(extracted_colors=[color]))

    def test_rejects_invalid_hex_color_in_tuple(self):
        with self.assertRaises(ValidationError):
            FigurePattern.model_validate(
                valid_pattern_data(extracted_colors=("#GGGGGG",))
            )

    def test_normalizes_tags_in_tuple(self):
        pattern = FigurePattern.model_validate(
            valid_pattern_data(tags=(" ML-Benchmark ", " method-comparison "))
        )

        self.assertEqual(pattern.tags, ["ML-Benchmark", "method-comparison"])

    def test_font_family_vocabulary_and_legacy_strings_are_accepted(self):
        self.assertEqual(models.FontFamily.ARIAL.value, "Arial")
        self.assertEqual(models.FontFamily.HELVETICA.value, "Helvetica")
        self.assertEqual(models.FontFamily.TIMES.value, "Times")
        self.assertEqual(models.FontFamily.SERIF.value, "serif")
        self.assertEqual(models.FontFamily.SANS_SERIF.value, "sans-serif")
        self.assertEqual(models.FontFamily.OTHER.value, "other")

        controlled = FigurePattern.model_validate(
            valid_pattern_data(font_family=models.FontFamily.HELVETICA)
        )
        legacy = FigurePattern.model_validate(
            valid_pattern_data(font_family="Avenir Next")
        )

        self.assertEqual(controlled.font_family, models.FontFamily.HELVETICA)
        self.assertEqual(legacy.font_family, "Avenir Next")

    def test_rejects_non_string_normalizer_inputs(self):
        invalid_updates = (
            {"source_doi": ["10.1038/example"]},
            {"source_figure": {"label": "Figure 3"}},
            {"chart_type": "other", "chart_type_description": 123},
        )

        for updates in invalid_updates:
            with self.subTest(updates=updates), self.assertRaises(ValidationError):
                FigurePattern.model_validate(valid_pattern_data(**updates))

    def test_failed_cross_field_assignments_preserve_original_state(self):
        pattern = FigurePattern.model_validate(valid_pattern_data())

        with self.assertRaises(ValidationError):
            pattern.chart_type = "other"
        self.assertEqual(pattern.chart_type, models.ChartType.GROUPED_BAR)
        self.assertIsNone(pattern.chart_type_description)

        with self.assertRaises(ValidationError):
            pattern.color_scheme = "other"
        self.assertEqual(pattern.color_scheme, models.ColorScheme.NATURE_NMI_PASTEL)
        self.assertIsNone(pattern.color_strategy_description)

        with self.assertRaises(ValidationError):
            pattern.novel_pattern = True
        self.assertFalse(pattern.novel_pattern)
        self.assertIsNone(pattern.novel_pattern_name)

    def test_clearing_required_paired_text_preserves_original_state(self):
        other_chart = FigurePattern.model_validate(
            valid_pattern_data(chart_type="other", chart_type_description="custom chart")
        )
        other_color = FigurePattern.model_validate(
            valid_pattern_data(color_scheme="other", color_strategy_description="custom colors")
        )
        novel = FigurePattern.model_validate(
            valid_pattern_data(novel_pattern=True, novel_pattern_name="new layout")
        )

        with self.assertRaises(ValidationError):
            other_chart.chart_type_description = " "
        self.assertEqual(other_chart.chart_type_description, "custom chart")

        with self.assertRaises(ValidationError):
            other_color.color_strategy_description = None
        self.assertEqual(other_color.color_strategy_description, "custom colors")

        with self.assertRaises(ValidationError):
            novel.novel_pattern_name = ""
        self.assertEqual(novel.novel_pattern_name, "new layout")

    def test_strips_free_text_scalars_and_blank_values_become_none(self):
        text_values = {
            "source_journal": " Nature ",
            "source_paper_title": " A study ",
            "source_url": " https://example.org/figure ",
            "recommendation_rationale": " Strong evidence ",
            "scientific_claim": " Intervention improves outcome ",
            "evidence_hierarchy": " hero: panel b ",
            "hero_panel": " panel b ",
            "statistical_annotations": " SEM ",
            "grid_structure": " 2x2 ",
            "backend": " matplotlib ",
            "font_family": " Custom Sans ",
            "export_formats": [" png ", " pdf "],
        }
        pattern = FigurePattern.model_validate(valid_pattern_data(**text_values))

        self.assertEqual(pattern.source_journal, "Nature")
        self.assertEqual(pattern.source_paper_title, "A study")
        self.assertEqual(pattern.source_url, "https://example.org/figure")
        self.assertEqual(pattern.recommendation_rationale, "Strong evidence")
        self.assertEqual(pattern.scientific_claim, "Intervention improves outcome")
        self.assertEqual(pattern.evidence_hierarchy, "hero: panel b")
        self.assertEqual(pattern.hero_panel, "panel b")
        self.assertEqual(pattern.statistical_annotations, "SEM")
        self.assertEqual(pattern.grid_structure, "2x2")
        self.assertEqual(pattern.backend, "matplotlib")
        self.assertEqual(pattern.font_family, "Custom Sans")
        self.assertEqual(pattern.export_formats, ["png", "pdf"])

        for field in text_values:
            if field == "export_formats":
                continue
            with self.subTest(field=field):
                blank = FigurePattern.model_validate(valid_pattern_data(**{field: " "}))
                self.assertIsNone(getattr(blank, field))

    def test_rejects_blank_or_non_string_export_formats(self):
        for formats in (["png", " "], ["png", 123]):
            with self.subTest(formats=formats), self.assertRaises(ValidationError):
                FigurePattern.model_validate(valid_pattern_data(export_formats=formats))

    def test_index_entry_projection_deep_copies_memory_score(self):
        pattern = FigurePattern.model_validate(
            valid_pattern_data(
                memory_score={
                    "total": 82.5,
                    "components": {
                        "quality": 24,
                        "validation": 20,
                        "reuse": 8.5,
                        "feedback": 20,
                        "recency": 10,
                    },
                    "formula": "quality30+validation25+reuse15+feedback20+recency10",
                }
            )
        )
        entry = IndexEntry.from_pattern(pattern, "patterns/pattern-001.md")

        assert entry.memory_score is not None
        entry.memory_score.components.quality = 1

        assert pattern.memory_score is not None
        self.assertEqual(pattern.memory_score.components.quality, 24)

    def test_persistent_font_family_maps_controlled_values_and_keeps_custom_fonts(self):
        controlled = FigurePattern.model_validate(valid_pattern_data(font_family="Helvetica"))
        custom = FigurePattern.model_validate(valid_pattern_data(font_family=" Custom Font "))

        self.assertIs(controlled.font_family, models.FontFamily.HELVETICA)
        self.assertEqual(custom.font_family, "Custom Font")

    def test_coerced_control_assignments_are_rejected_without_mutation(self):
        pattern = FigurePattern.model_validate(valid_pattern_data())

        with self.assertRaises(ValidationError):
            pattern.chart_type = b"other"
        self.assertEqual(pattern.chart_type, models.ChartType.GROUPED_BAR)

        with self.assertRaises(ValidationError):
            pattern.color_scheme = b"other"
        self.assertEqual(pattern.color_scheme, models.ColorScheme.NATURE_NMI_PASTEL)

        for value in (1, "true", "yes"):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                pattern.novel_pattern = value
            self.assertFalse(pattern.novel_pattern)
            self.assertIsNone(pattern.novel_pattern_name)

    def test_rejects_binary_values_before_text_and_control_coercion(self):
        invalid_updates = (
            {"source_doi": b"10.1038/example"},
            {"source_figure": bytearray(b"Figure 3")},
            {"source_journal": b"Nature"},
            {"font_family": bytearray(b"Arial")},
            {"id": b"pattern-001"},
            {"source_type": b"image"},
            {"chart_type": b"grouped-bar"},
            {"layout_archetype": bytearray(b"quantitative-grid")},
            {"color_scheme": b"nature-nmi-pastel"},
            {"novel_pattern": "true", "novel_pattern_name": "new layout"},
            {"tags": [b"benchmark"]},
            {"extracted_colors": [bytearray(b"#AABBCC")]},
            {"export_formats": [b"png"]},
            {"sub_chart_types": [b"scatter"]},
        )

        for updates in invalid_updates:
            with self.subTest(updates=updates), self.assertRaises(ValidationError):
                FigurePattern.model_validate(valid_pattern_data(**updates))

    def test_ordinary_json_yaml_string_inputs_remain_valid(self):
        pattern = FigurePattern.model_validate(
            valid_pattern_data(
                source_type="image",
                chart_type="grouped-bar",
                sub_chart_types=["scatter"],
                layout_archetype="quantitative-grid",
                color_scheme="nature-nmi-pastel",
                novel_pattern=False,
                tags=["benchmark"],
                extracted_colors=["#aabbcc"],
                export_formats=["png"],
            )
        )

        self.assertEqual(pattern.source_type, models.SourceType.IMAGE)
        self.assertEqual(pattern.chart_type, models.ChartType.GROUPED_BAR)
        self.assertEqual(pattern.sub_chart_types, [models.ChartType.SCATTER])
        self.assertEqual(pattern.layout_archetype, models.LayoutArchetype.QUANTITATIVE_GRID)
        self.assertEqual(pattern.color_scheme, models.ColorScheme.NATURE_NMI_PASTEL)
        self.assertFalse(pattern.novel_pattern)

    def test_other_color_scheme_requires_description(self):
        with self.assertRaises(ValidationError):
            FigurePattern.model_validate(valid_pattern_data(color_scheme="other"))

    def test_code_entry_accepts_optional_rendering_fields(self):
        pattern = FigurePattern.model_validate(
            valid_pattern_data(
                source_type="code",
                backend="matplotlib",
                figsize=(6.5, 4.0),
                export_formats=["png", "pdf"],
                dpi=300,
            )
        )

        self.assertEqual(pattern.backend, "matplotlib")
        self.assertEqual(pattern.figsize, (6.5, 4.0))
        self.assertEqual(pattern.export_formats, ["png", "pdf"])
        self.assertEqual(pattern.dpi, 300)

    def test_extensions_accept_json_compatible_values(self):
        pattern = FigurePattern.model_validate(
            valid_pattern_data(
                extensions={"analyst": {"name": "Ada"}, "scores": [1, 2, None]}
            )
        )

        self.assertEqual(pattern.extensions["analyst"], {"name": "Ada"})

    def test_mutable_defaults_are_isolated(self):
        first = FigurePattern.model_validate(valid_pattern_data())
        second = FigurePattern.model_validate(valid_pattern_data(id="pattern-002"))

        first.tags.append("first-only")
        first.extracted_colors.append("#112233")
        first.extensions["first_only"] = True
        first.relations.similar_to.append("pattern-003")

        self.assertEqual(second.tags, [])
        self.assertEqual(second.extracted_colors, ["#AABBCC"])
        self.assertEqual(second.extensions, {})
        self.assertEqual(second.relations.similar_to, [])

    def test_index_entry_is_projected_from_pattern(self):
        pattern = FigurePattern.model_validate(
            valid_pattern_data(
                tags=[" ML-Benchmark "],
                quality_rating=4.5,
                validation_score=5,
                application_count=2,
                matched_nature_figure_pattern=3,
            )
        )

        entry = IndexEntry.from_pattern(
            pattern, "patterns\\chart-type\\grouped-bar\\pattern-001.md"
        )

        self.assertEqual(entry.id, pattern.id)
        self.assertEqual(entry.file, "patterns/chart-type/grouped-bar/pattern-001.md")
        self.assertEqual(entry.chart_type, pattern.chart_type)
        self.assertEqual(entry.tags, ["ML-Benchmark"])
        self.assertEqual(entry.quality_rating, 4.5)
        self.assertEqual(entry.validation_score, 5)
        self.assertEqual(entry.application_count, 2)
        self.assertEqual(entry.matched_nature_figure_pattern, 3)
