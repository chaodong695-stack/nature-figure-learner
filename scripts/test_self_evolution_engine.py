import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from self_evolution_engine import EvolutionEngine


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
            entries = [make_entry(i, quality=4 + (i % 2), validation=4, uses=i) for i in range(1, 6)]
            (kb_path / "index.json").write_text(json.dumps(entries), encoding="utf-8")

            engine = EvolutionEngine(kb_path)
            results = engine.run_full_evolution()
            updated = json.loads((kb_path / "index.json").read_text(encoding="utf-8"))

            self.assertTrue(all("memory_score" in entry for entry in updated))
            self.assertTrue(all("success_cases" in entry for entry in updated))
            self.assertTrue(all("failure_cases" in entry for entry in updated))
            self.assertTrue(any(entry.get("relations", {}).get("similar_to") for entry in updated))
            self.assertGreaterEqual(len(results.get("style_reflections", [])), 1)
            self.assertGreaterEqual(len(results.get("recommendations", [])), 1)


if __name__ == "__main__":
    unittest.main()
