from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.helpers import make_pattern, write_pattern_fixture, valid_pattern_data


ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "scripts" / "figure_kb.py"


class CLITests(unittest.TestCase):
    def run_cli(self, *args: str, env: dict[str, str] | None = None) -> tuple[int, dict, str]:
        merged = os.environ.copy()
        if env:
            merged.update(env)
        completed = subprocess.run([sys.executable, str(LAUNCHER), *args], cwd=ROOT,
                                   capture_output=True, text=True, env=merged)
        return completed.returncode, json.loads(completed.stdout), completed.stderr

    def write_json(self, directory: str, payload: object, name: str = "pattern.json") -> Path:
        path = Path(directory) / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_schema_export_is_enveloped(self):
        code, result, stderr = self.run_cli("schema", "export")
        self.assertEqual(code, 0)
        self.assertEqual(set(result), {"status", "command", "schema_version", "data", "warnings", "error"})
        self.assertEqual(result["status"], "success")
        self.assertIn("schema", result["data"])
        self.assertEqual(stderr, "")

    def test_pattern_validate_valid_and_invalid(self):
        with tempfile.TemporaryDirectory() as directory:
            valid = self.write_json(directory, valid_pattern_data())
            code, result, _ = self.run_cli("pattern", "validate", "--input", str(valid))
            self.assertEqual(code, 0)
            self.assertEqual(result["status"], "success")
            invalid = self.write_json(directory, {"id": "bad"}, "invalid.json")
            code, result, _ = self.run_cli("pattern", "validate", "--input", str(invalid))
            self.assertNotEqual(code, 0)
            self.assertEqual(result["status"], "error")
            self.assertEqual(result["error"]["code"], "SCHEMA_INVALID")

    def test_query_no_match_and_sankey_unsupported(self):
        with tempfile.TemporaryDirectory() as directory:
            kb = Path(directory) / "kb"
            write_pattern_fixture(kb, make_pattern())
            code, result, _ = self.run_cli("query", "--kb-path", str(kb), "--id", "missing")
            self.assertEqual(code, 0)
            self.assertEqual(result["status"], "success")
            self.assertEqual(result["data"]["returned_count"], 0)
            sankey = make_pattern(id="sankey-001", chart_type="sankey")
            write_pattern_fixture(kb, sankey)
            code, result, _ = self.run_cli("self-validate", "--kb-path", str(kb), "--pattern-id", sankey.id, "--output-dir", str(Path(directory) / "preview"))
            self.assertEqual(code, 0)
            self.assertEqual(result["status"], "unsupported")

    def test_duplicate_save_maps_stable_error(self):
        with tempfile.TemporaryDirectory() as directory:
            kb = Path(directory) / "kb"
            pattern = self.write_json(directory, valid_pattern_data())
            narrative = Path(directory) / "notes.md"; narrative.write_text("notes\n", encoding="utf-8")
            args = ("pattern", "save", "--kb-path", str(kb), "--input", str(pattern), "--narrative", str(narrative))
            self.assertEqual(self.run_cli(*args)[0], 0)
            code, result, _ = self.run_cli(*args)
            self.assertNotEqual(code, 0)
            self.assertEqual(result["error"]["code"], "KB_DUPLICATE")

    def test_unexpected_exception_stdout_is_json_and_debug_traceback_is_stderr(self):
        from nature_figure_learner import cli
        with patch.object(cli, "_schema_export", side_effect=RuntimeError("boom")):
            with patch.object(sys, "argv", ["figure_kb", "schema", "export"]):
                from io import StringIO
                stdout, stderr = StringIO(), StringIO()
                with patch("sys.stdout", stdout), patch("sys.stderr", stderr):
                    code = cli.main()
        self.assertNotEqual(code, 0)
        result = json.loads(stdout.getvalue())
        self.assertEqual(result["error"]["code"], "INTERNAL_ERROR")
        self.assertNotIn("Traceback", stdout.getvalue())

    def test_parse_errors_are_json_envelopes_with_nonzero_status(self):
        cases = [
            (("query", "--unknown"), "QUERY_INVALID"),
            (("query", "--chart-type", "not-a-chart"), "QUERY_INVALID"),
            (("pattern", "validate"), "SCHEMA_INVALID"),
        ]
        for args, expected_code in cases:
            with self.subTest(args=args):
                code, result, _ = self.run_cli(*args)
                self.assertNotEqual(code, 0)
                self.assertEqual(result["status"], "error")
                self.assertEqual(result["error"]["code"], expected_code)


if __name__ == "__main__":
    unittest.main()
