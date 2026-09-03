import tempfile
import unittest
from pathlib import Path

import matplotlib.pyplot as plt
from PIL import Image

from nature_figure_learner.mock_data import MockDataGenerator
from nature_figure_learner.models import ChartType, RenderStatus
from nature_figure_learner.renderers import (
    BarRenderer,
    DuplicateRendererError,
    RendererRegistry,
    build_default_registry,
    render_pattern,
)
from tests.helpers import make_pattern


SUPPORTED_TYPES = (
    ChartType.GROUPED_BAR,
    ChartType.STACKED_BAR,
    ChartType.HORIZONTAL_BAR,
    ChartType.LINE_TREND,
    ChartType.MULTI_LINE,
    ChartType.SCATTER,
    ChartType.BUBBLE,
    ChartType.HEATMAP,
    ChartType.VIOLIN,
    ChartType.BOX,
)


class RendererRegistryTests(unittest.TestCase):
    def test_default_registry_resolves_supported_types(self):
        registry = build_default_registry()
        for chart_type in SUPPORTED_TYPES:
            with self.subTest(chart_type=chart_type):
                self.assertIsNotNone(registry.get(chart_type))

    def test_duplicate_registration_is_rejected_without_mutation(self):
        registry = RendererRegistry()
        first = BarRenderer()
        registry.register(first)
        with self.assertRaises(DuplicateRendererError):
            registry.register(BarRenderer())
        self.assertIs(registry.get(ChartType.GROUPED_BAR), first)

    def test_sankey_is_unsupported_not_error(self):
        pattern = make_pattern(chart_type=ChartType.SANKEY)
        result = render_pattern(pattern, None, Path(tempfile.gettempdir()))
        self.assertEqual(result.status, RenderStatus.UNSUPPORTED)
        self.assertIsNone(result.error)

    def test_density_is_unsupported_in_first_renderer(self):
        pattern = make_pattern(chart_type=ChartType.DENSITY)
        result = render_pattern(pattern, None, Path(tempfile.gettempdir()))
        self.assertEqual(result.status, RenderStatus.UNSUPPORTED)
        self.assertIsNone(result.error)


class RendererSmokeTests(unittest.TestCase):
    def test_render_does_not_mutate_global_matplotlib_font_settings(self):
        pattern = make_pattern(id="pattern-font-scope", chart_type=ChartType.LINE_TREND)
        mock = MockDataGenerator().generate(pattern)
        before = list(plt.rcParams["font.family"])
        with tempfile.TemporaryDirectory() as temp_dir:
            result = build_default_registry().get(ChartType.LINE_TREND).render(
                pattern, mock, Path(temp_dir)
            )
        self.assertEqual(result.status, RenderStatus.SUCCESS)
        self.assertEqual(list(plt.rcParams["font.family"]), before)

    def test_heatmap_uses_extracted_palette_in_pixels(self):
        pattern = make_pattern(
            id="pattern-heatmap-palette",
            chart_type=ChartType.HEATMAP,
            panel_count=1,
            extracted_colors=["#FF0000", "#0000FF"],
        )
        mock = MockDataGenerator().generate(pattern)
        with tempfile.TemporaryDirectory() as temp_dir:
            result = build_default_registry().get(ChartType.HEATMAP).render(
                pattern, mock, Path(temp_dir)
            )
            self.assertEqual(result.status, RenderStatus.SUCCESS)
            self.assertEqual(result.metadata["effective_palette"], ["#FF0000", "#0000FF"])
            assert result.output_file is not None
            with Image.open(result.output_file).convert("RGB") as image:
                pixels = list(image.getdata())
            self.assertTrue(any(red > 180 and blue < 100 for red, green, blue in pixels))
            self.assertTrue(any(blue > 180 and red < 100 for red, green, blue in pixels))

    def test_all_supported_types_render_png_with_metadata(self):
        generator = MockDataGenerator()
        registry = build_default_registry()
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            for chart_type in SUPPORTED_TYPES:
                with self.subTest(chart_type=chart_type):
                    pattern = make_pattern(
                        id=f"pattern-{chart_type.value.replace('-', '-')}",
                        chart_type=chart_type,
                        panel_count=2,
                        extracted_colors=["#336699", "#CC6633"],
                        font_family="Definitely Missing Font",
                    )
                    mock = generator.generate(pattern)
                    result = registry.get(chart_type).render(pattern, mock, output_dir)
                    self.assertEqual(result.status, RenderStatus.SUCCESS)
                    self.assertIsNotNone(result.output_file)
                    assert result.output_file is not None
                    output_file = Path(result.output_file)
                    self.assertTrue(output_file.exists())
                    with Image.open(output_file) as image:
                        self.assertGreater(image.width, 0)
                        self.assertGreater(image.height, 0)
                    self.assertEqual(result.metadata["panel_count"], pattern.panel_count)
                    self.assertTrue(result.metadata["effective_palette"])
                    self.assertIn("font_family", result.metadata)
                    self.assertIn("layout", result.metadata)


if __name__ == "__main__":
    unittest.main()
