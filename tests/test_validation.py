import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from nature_figure_learner.mock_data import MockDataGenerator
from nature_figure_learner.models import (
    ChartType,
    MockDataSpec,
    RenderResult,
    RenderStatus,
    ValidationStatus,
)
from nature_figure_learner.validation import run_self_validation, validate_render
from tests.helpers import make_pattern


class ValidationTests(unittest.TestCase):
    def test_unsupported_render_produces_not_run_validation(self):
        pattern = make_pattern(id="pattern-sankey", chart_type=ChartType.SANKEY)
        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_self_validation(pattern, MockDataSpec(), Path(temp_dir))
        self.assertEqual(result.render.status, RenderStatus.UNSUPPORTED)
        self.assertEqual(result.validation.status, ValidationStatus.NOT_RUN)

    def test_render_error_is_not_validation_failure(self):
        pattern = make_pattern()
        mock = MockDataGenerator().generate(pattern)
        render = RenderResult(
            pattern_id=pattern.id,
            renderer_id="bar",
            status=RenderStatus.ERROR,
            error={"type": "RenderError", "code": "RENDER_FAILED", "message": "failed"},
        )
        result = validate_render(render, pattern, mock)
        self.assertEqual(result.status, ValidationStatus.NOT_RUN)
        self.assertEqual(result.objective_score, None)

    def test_blank_image_fails_objective_check(self):
        pattern = make_pattern()
        mock = MockDataGenerator().generate(pattern)
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "blank.png"
            Image.new("RGB", (600, 450), "white").save(path)
            render = RenderResult(
                pattern_id=pattern.id,
                renderer_id="bar",
                status=RenderStatus.SUCCESS,
                output_file=str(path),
                metadata={"panel_count": pattern.panel_count},
            )
            result = validate_render(render, pattern, mock)
        self.assertEqual(result.status, ValidationStatus.FAIL)
        self.assertIn("image_nonblank", result.failed_check_ids)

    def test_readable_render_checks_dimensions_panel_and_palette(self):
        pattern = make_pattern(
            id="pattern-validation",
            panel_count=1,
            figsize=(4.0, 3.0),
            dpi=100,
            extracted_colors=["#FF0000"],
        )
        mock = MockDataGenerator().generate(pattern)
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "preview.png"
            image = Image.new("RGB", (400, 300), "white")
            pixels = np.asarray(image).copy()
            pixels[100:200, 100:200] = (255, 0, 0)
            Image.fromarray(pixels).save(path)
            render = RenderResult(
                pattern_id=pattern.id,
                renderer_id="bar",
                status=RenderStatus.SUCCESS,
                output_file=str(path),
                metadata={
                    "panel_count": 1,
                    "effective_palette": ["#FF0000"],
                    "layout": {"figsize": [4.0, 3.0], "panel_count": 1},
                },
            )
            result = validate_render(render, pattern, mock)
        self.assertIn(result.status, (ValidationStatus.PASS, ValidationStatus.WARN))
        self.assertNotIn("image_nonblank", result.failed_check_ids)
        self.assertEqual(pattern.validation_score, None)

    def test_non_list_palette_metadata_is_structured_warning(self):
        pattern = make_pattern(
            id="pattern-invalid-palette-metadata",
            panel_count=1,
            figsize=(4.0, 3.0),
            dpi=100,
            extracted_colors=[],
        )
        mock = MockDataGenerator().generate(pattern)
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "preview.png"
            image = Image.new("RGB", (400, 300), "white")
            pixels = np.asarray(image).copy()
            pixels[100:200, 100:200] = (255, 0, 0)
            Image.fromarray(pixels).save(path)
            render = RenderResult(
                pattern_id=pattern.id,
                renderer_id="bar",
                status=RenderStatus.SUCCESS,
                output_file=str(path),
                metadata={
                    "panel_count": 1,
                    "effective_palette": 123,
                    "layout": {"figsize": [4.0, 3.0], "panel_count": 1},
                },
            )
            result = validate_render(render, pattern, mock)
        palette_check = next(check for check in result.checks if check.id == "palette_presence")
        self.assertEqual(palette_check.status, ValidationStatus.WARN)
        self.assertIn("palette_presence", {check.id for check in result.checks})

    def test_layout_metadata_mismatch_fails_objective_check(self):
        pattern = make_pattern(id="pattern-layout-metadata", panel_count=1, figsize=(4.0, 3.0), dpi=100)
        mock = MockDataGenerator().generate(pattern)
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "preview.png"
            Image.new("RGB", (400, 300), "white").save(path)
            render = RenderResult(
                pattern_id=pattern.id,
                renderer_id="bar",
                status=RenderStatus.SUCCESS,
                output_file=str(path),
                metadata={
                    "panel_count": 1,
                    "layout": {"figsize": [5.0, 3.0], "panel_count": 1},
                },
            )
            result = validate_render(render, pattern, mock)
        self.assertEqual(result.status, ValidationStatus.FAIL)
        self.assertIn("layout_metadata", result.failed_check_ids)


if __name__ == "__main__":
    unittest.main()
