import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SkillContractTests(unittest.TestCase):
    def test_skill_routes_query_save_and_validation_to_cli(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        for command in ("pattern save", "query", "self-validate"):
            self.assertIn(command, text)

    def test_skill_requires_explicit_workflow_intent(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("A supplied file is an eligible input, not a trigger", text)
        self.assertIn("Receiving a file alone is not sufficient", text)
        self.assertIn("Explicit request to analyze/learn", text)

    def test_wf1_and_wf2_validate_before_persisting(self):
        for name in ("WF1-image.md", "WF2-code.md"):
            text = (ROOT / "references" / name).read_text(encoding="utf-8")
            validate_at = text.index("python scripts/figure_kb.py pattern validate")
            save_at = text.index("python scripts/figure_kb.py pattern save")
            self_validate_at = text.index("python scripts/figure_kb.py self-validate")
            self.assertLess(validate_at, save_at, name)
            self.assertLess(save_at, self_validate_at, name)
            self.assertIn("only when the user explicitly requests", text)
            self.assertIn("objective_score", text)

    def test_query_reference_no_longer_reimplements_ranking(self):
        text = (ROOT / "references" / "WF3-query.md").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("def ranking_score", text)
        self.assertIn("scripts/figure_kb.py query", text)


if __name__ == "__main__":
    unittest.main()
