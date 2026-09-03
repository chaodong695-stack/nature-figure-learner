import json
import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import self_evolution_engine as evolution_module
from self_evolution_engine import EvolutionEngine
from nature_figure_learner.models import FigurePattern
from nature_figure_learner.repository import rebuild_index, read_pattern_document, save_pattern


def make_entry(index, chart_type="grouped-bar", quality=4, validation=4, uses=1):
    return {
        "id": f"pattern-{index:03d}",
        "file": f"patterns/chart-type/{chart_type}/pattern-{index:03d}.md",
        "source_type": "image",
        "source_journal": "Nature",
        "source_year": 2026,
        "chart_type": chart_type,
        "color_scheme": "nature-nmi-pastel",
        "layout_archetype": "quantitative-grid",
        "tags": ["method-comparison", "benchmark"],
        "quality_rating": quality,
        "validation_score": validation,
        "application_count": uses,
        "analysis_date": (datetime.now() - timedelta(days=index)).date().isoformat(),
        "application_feedback": [
            {"date": "2026-06-01", "rating": quality, "notes": "Good color discipline and compact legend"},
            {"date": "2026-06-02", "rating": max(1, quality - 2), "notes": "Legend too small for dense panels"},
        ],
    }


class SelfEvolutionEngineTests(unittest.TestCase):
    def test_memory_score_prefers_validated_reused_recent_patterns(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = EvolutionEngine(tmp)
            strong = make_entry(1, quality=5, validation=5, uses=8)
            weak = make_entry(200, quality=2, validation=2, uses=0)

            strong_score = engine.compute_memory_score(strong, now=datetime.now())
            weak_score = engine.compute_memory_score(weak, now=datetime.now())

            self.assertGreater(strong_score["total"], weak_score["total"])
            self.assertGreaterEqual(strong_score["total"], 80)
            self.assertLessEqual(weak_score["total"], 45)

    def test_full_evolution_backfills_memory_artifacts_and_reflections(self):
        with tempfile.TemporaryDirectory() as tmp:
            kb_path = Path(tmp)
            for i in range(1, 6):
                pattern = FigurePattern.model_validate({
                    "id": f"pattern-{i:03d}",
                    "source_type": "image",
                    "source_journal": "Nature",
                    "source_year": 2026,
                    "chart_type": "grouped-bar",
                    "layout_archetype": "quantitative-grid",
                    "panel_count": 3,
                    "color_scheme": "nature-nmi-pastel",
                    "tags": ["method-comparison", "benchmark"],
                    "quality_rating": 4 + (i % 2),
                    "validation_score": 4,
                    "application_count": i,
                    "analysis_date": (datetime.now() - timedelta(days=i)).date().isoformat(),
                    "application_feedback": [
                        {"date": "2026-06-01", "rating": 5, "notes": "Good color discipline and compact legend"},
                        {"date": "2026-06-02", "rating": max(1, 4 + (i % 2) - 2), "notes": "Legend too small for dense panels"},
                    ],
                })
                save_pattern(kb_path, pattern, "# Original narrative\n")

            engine = EvolutionEngine(kb_path)
            results = engine.run_full_evolution()
            updated = json.loads((kb_path / "index.json").read_text(encoding="utf-8"))

            self.assertTrue(all("memory_score" in entry for entry in updated))
            self.assertTrue(all("success_cases" in entry for entry in updated))
            self.assertTrue(all("failure_cases" in entry for entry in updated))
            self.assertTrue(any(entry.get("relations", {}).get("similar_to") for entry in updated))
            self.assertGreaterEqual(len(results.get("style_reflections", [])), 1)
            self.assertGreaterEqual(len(results.get("recommendations", [])), 1)

    def test_full_evolution_persists_enrichment_to_markdown(self):
        with tempfile.TemporaryDirectory() as tmp:
            kb_path = Path(tmp)
            for i in range(1, 6):
                pattern = FigurePattern.model_validate({
                    "id": f"pattern-{i:03d}",
                    "source_type": "image",
                    "source_journal": "Nature",
                    "source_year": 2026,
                    "chart_type": "grouped-bar",
                    "layout_archetype": "quantitative-grid",
                    "panel_count": 3,
                    "color_scheme": "nature-nmi-pastel",
                    "tags": ["method-comparison", "benchmark"],
                    "quality_rating": 4 + (i % 2),
                    "validation_score": 4,
                    "application_count": i,
                    "analysis_date": (datetime.now() - timedelta(days=i)).date().isoformat(),
                    "application_feedback": [
                        {"date": "2026-06-01", "rating": 5, "notes": "Good color discipline"},
                        {"date": "2026-06-02", "rating": 2, "notes": "Legend too small"},
                    ],
                })
                save_pattern(kb_path, pattern, "# Original narrative\n")

            engine = EvolutionEngine(kb_path)
            results = engine.run_full_evolution()
            rebuild_index(kb_path)
            updated = json.loads((kb_path / "index.json").read_text(encoding="utf-8"))

            documents = [
                read_pattern_document(kb_path / entry["file"])
                for entry in updated
            ]
            self.assertTrue(all(document.pattern.memory_score is not None for document in documents))
            self.assertTrue(all(document.pattern.success_cases for document in documents))
            self.assertTrue(all(document.pattern.failure_cases for document in documents))
            self.assertTrue(all(document.pattern.recommendation_rationale for document in documents))
            self.assertTrue(any(document.pattern.relations.similar_to for document in documents))
            self.assertGreaterEqual(len(results.get("style_reflections", [])), 1)
            self.assertFalse(any(entry["id"].startswith(("meta-", "reflection-")) for entry in updated))

    def test_progress_logging_does_not_pollute_stdout(self):
        with tempfile.TemporaryDirectory() as tmp:
            stdout = io.StringIO()
            progress = io.StringIO()
            engine = EvolutionEngine(tmp, stream=progress)
            with redirect_stdout(stdout):
                result = engine.run_full_evolution()
            self.assertEqual(result, {"error": "KB is empty"})
            self.assertEqual(stdout.getvalue(), "")
            self.assertIn("Loading KB index...", progress.getvalue())

    def test_none_validation_score_is_not_treated_as_extraction_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = EvolutionEngine(tmp)
            pattern = FigurePattern.model_validate({
                "id": "pattern-001",
                "source_type": "image",
                "chart_type": "grouped-bar",
                "layout_archetype": "quantitative-grid",
                "panel_count": 1,
                "color_scheme": "nature-nmi-pastel",
                "analysis_date": "2026-08-31",
                "validation_score": None,
            })
            entry = pattern.model_dump(mode="json", exclude_none=False)
            entry["file"] = "patterns/chart-type/grouped-bar/pattern-001.md"

            self.assertIsNone(engine.analyze_extraction_failures([entry]))

    def test_relative_kb_path_is_resolved_before_markdown_projection(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            kb_path = Path(tmp).resolve()
            pattern = FigurePattern.model_validate({
                "id": "pattern-001",
                "source_type": "image",
                "chart_type": "grouped-bar",
                "layout_archetype": "quantitative-grid",
                "panel_count": 1,
                "color_scheme": "nature-nmi-pastel",
                "analysis_date": "2026-08-31",
            })
            save_pattern(kb_path, pattern, "# Narrative\n")
            relative_kb = os.path.relpath(kb_path, Path.cwd())

            engine = EvolutionEngine(relative_kb)

            self.assertTrue(engine.kb_path.is_absolute())
            self.assertEqual([entry["id"] for entry in engine.load_index()], ["pattern-001"])

    def test_archive_rejects_entry_path_outside_kb_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            kb_path = Path(tmp).resolve()
            outside = kb_path.parent / f"{kb_path.name}-outside.md"
            outside.write_text("outside\n", encoding="utf-8")
            try:
                engine = EvolutionEngine(kb_path)

                archived = engine._archive_pattern(
                    {"id": "evil", "file": "../" + outside.name},
                    "never-used",
                )

                self.assertFalse(archived)
                self.assertTrue(outside.exists())
            finally:
                outside.unlink(missing_ok=True)

    def test_archive_rejects_absolute_entry_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            kb_path = Path(tmp).resolve()
            source = kb_path / "patterns/chart-type/grouped-bar/pattern-001.md"
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_text("source\n", encoding="utf-8")
            engine = EvolutionEngine(kb_path)

            archived = engine._archive_pattern(
                {"id": "pattern-001", "file": str(source)},
                "never-used",
            )

            self.assertFalse(archived)
            self.assertTrue(source.exists())

    def test_archive_rebuild_failure_restores_moved_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            kb_path = Path(tmp)
            pattern = FigurePattern.model_validate({
                "id": "pattern-001",
                "source_type": "image",
                "chart_type": "grouped-bar",
                "layout_archetype": "quantitative-grid",
                "panel_count": 1,
                "color_scheme": "nature-nmi-pastel",
                "application_count": 0,
                "analysis_date": "2020-01-01",
            })
            save_pattern(kb_path, pattern, "# Narrative\n")
            source = kb_path / "patterns/chart-type/grouped-bar/pattern-001.md"
            engine = EvolutionEngine(kb_path)

            with patch.object(evolution_module, "rebuild_index", side_effect=OSError("rebuild failed")):
                with self.assertRaises(OSError):
                    engine.prune_patterns(engine.load_index())

            self.assertTrue(source.exists())
            self.assertFalse((kb_path / "archive/never-used/pattern-001.md").exists())

    def test_batch_update_failure_restores_already_updated_markdown(self):
        with tempfile.TemporaryDirectory() as tmp:
            kb_path = Path(tmp)
            for index in (1, 2):
                pattern = FigurePattern.model_validate({
                    "id": f"pattern-{index:03d}",
                    "source_type": "image",
                    "chart_type": "grouped-bar",
                    "layout_archetype": "quantitative-grid",
                    "panel_count": 1,
                    "color_scheme": "nature-nmi-pastel",
                    "application_count": index,
                    "analysis_date": "2026-08-31",
                })
                save_pattern(kb_path, pattern, "# Narrative\n")

            source_bytes = {
                path: path.read_bytes()
                for path in (kb_path / "patterns/chart-type/grouped-bar").glob("*.md")
            }
            engine = EvolutionEngine(kb_path)
            real_update = evolution_module.update_pattern
            calls = 0

            def fail_second_update(*args, **kwargs):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError("update failed")
                return real_update(*args, **kwargs)

            with patch.object(evolution_module, "update_pattern", side_effect=fail_second_update):
                with self.assertRaises(OSError):
                    engine.enrich_memory_artifacts(engine.load_index())

            self.assertEqual(
                source_bytes,
                {
                    path: path.read_bytes()
                    for path in source_bytes
                },
            )


if __name__ == "__main__":
    unittest.main()
