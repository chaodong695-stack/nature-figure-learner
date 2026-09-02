import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SkillContractTests(unittest.TestCase):
    def test_skill_routes_query_save_and_validation_to_cli(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        for command in ("pattern save", "query", "self-validate"):
            self.assertIn(command, text)

    def test_query_reference_no_longer_reimplements_ranking(self):
        text = (ROOT / "references" / "query-templates.md").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("def ranking_score", text)
        self.assertIn("scripts/figure_kb.py query", text)


if __name__ == "__main__":
    unittest.main()
