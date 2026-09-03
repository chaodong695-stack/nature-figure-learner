import unittest

from nature_figure_learner.mock_data import MockDataGenerator, stable_seed
from nature_figure_learner.models import (
    BarMockData,
    ChartType,
    DistributionMockData,
    LineMockData,
    MatrixMockData,
    MockDataResult,
    MockDataSpec,
    MockDataStatus,
    ScatterMockData,
)
from tests.helpers import make_pattern


class MockDataModelTests(unittest.TestCase):
    def test_spec_constraints_and_defaults(self):
        spec = MockDataSpec(categories=4, groups=3, points=10)
        self.assertEqual(spec.categories, 4)
        with self.assertRaises(ValueError):
            MockDataSpec(points=1)

    def test_stable_seed_is_sha256_prefix(self):
        self.assertEqual(stable_seed("pattern-001"), stable_seed("pattern-001"))
        self.assertNotEqual(stable_seed("pattern-001"), stable_seed("pattern-002"))


class MockDataGeneratorTests(unittest.TestCase):
    def setUp(self):
        self.generator = MockDataGenerator()

    def test_generator_seed_is_controlled_by_spec_only(self):
        with self.assertRaises(TypeError):
            MockDataGenerator(seed=1)

    def test_grouped_bar_is_typed_and_deterministic(self):
        pattern = make_pattern(chart_type=ChartType.GROUPED_BAR)
        spec = MockDataSpec(categories=4, groups=3)
        first = self.generator.generate(pattern, spec)
        second = self.generator.generate(pattern, spec)
        self.assertEqual(first, second)
        self.assertEqual(first.status, MockDataStatus.SUCCESS)
        self.assertIsInstance(first.data, BarMockData)
        self.assertEqual(len(first.data.values), 4)
        self.assertEqual(len(first.data.values[0]), 3)
        self.assertTrue(first.data.synthetic)
        self.assertEqual(first.inferred_defaults, {})

    def test_default_result_records_full_stable_seed(self):
        pattern = make_pattern(chart_type=ChartType.SCATTER)
        result = self.generator.generate(pattern, MockDataSpec(points=4))
        self.assertEqual(result.seed, stable_seed(pattern.id))

    def test_line_scatter_matrix_distribution_shapes(self):
        cases = [
            (ChartType.MULTI_LINE, MockDataSpec(groups=3, points=10), LineMockData, (3, 10)),
            (ChartType.SCATTER, MockDataSpec(points=20), ScatterMockData, (20,)),
            (ChartType.BUBBLE, MockDataSpec(points=20), ScatterMockData, (20,)),
            (ChartType.HEATMAP, MockDataSpec(matrix_rows=5, matrix_cols=6), MatrixMockData, (5, 6)),
            (ChartType.VIOLIN, MockDataSpec(categories=4, distribution_samples=50), DistributionMockData, (4, 50)),
        ]
        for chart_type, spec, payload_type, shape in cases:
            with self.subTest(chart_type=chart_type):
                result = self.generator.generate(make_pattern(chart_type=chart_type), spec)
                self.assertEqual(result.status, MockDataStatus.SUCCESS)
                self.assertIsInstance(result.data, payload_type)
                if isinstance(result.data, LineMockData):
                    self.assertEqual(len(result.data.x), shape[1])
                    self.assertEqual((len(result.data.y), len(result.data.y[0])), shape)
                elif isinstance(result.data, ScatterMockData):
                    self.assertEqual(len(result.data.x), shape[0])
                    self.assertEqual(len(result.data.y), shape[0])
                    if chart_type == ChartType.BUBBLE:
                        self.assertEqual(len(result.data.size), shape[0])
                elif isinstance(result.data, MatrixMockData):
                    self.assertEqual((len(result.data.matrix), len(result.data.matrix[0])), shape)
                else:
                    self.assertEqual((len(result.data.distributions), len(result.data.distributions[0])), shape)

    def test_explicit_seed_changes_data(self):
        pattern = make_pattern(chart_type=ChartType.SCATTER)
        first = self.generator.generate(pattern, MockDataSpec(seed=1, points=8))
        second = self.generator.generate(pattern, MockDataSpec(seed=2, points=8))
        self.assertNotEqual(first.data, second.data)
        self.assertEqual(first.seed, 1)

    def test_defaults_are_recorded_and_irrelevant_fields_warn(self):
        pattern = make_pattern(chart_type=ChartType.HEATMAP)
        result = self.generator.generate(pattern, MockDataSpec(points=7, groups=2))
        self.assertIn("matrix_rows", result.inferred_defaults)
        self.assertIn("matrix_cols", result.inferred_defaults)
        codes = {warning.code for warning in result.warnings}
        self.assertIn("MOCK_SPEC_IRRELEVANT", codes)

    def test_unsupported_chart_returns_typed_result_without_data(self):
        result = self.generator.generate(make_pattern(chart_type=ChartType.SANKEY), MockDataSpec())
        self.assertIsInstance(result, MockDataResult)
        self.assertEqual(result.status, MockDataStatus.UNSUPPORTED)
        self.assertIsNone(result.data)


if __name__ == "__main__":
    unittest.main()
