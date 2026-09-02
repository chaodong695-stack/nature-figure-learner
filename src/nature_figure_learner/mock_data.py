"""Deterministic, typed synthetic data for supported figure families."""

from __future__ import annotations

import hashlib

import numpy as np

from .models import (
    BarMockData,
    ChartType,
    CLIWarning,
    DistributionMockData,
    FigurePattern,
    LineMockData,
    MatrixMockData,
    MockDataResult,
    MockDataSpec,
    MockDataStatus,
    ScatterMockData,
)


def stable_seed(pattern_id: str) -> int:
    """Derive a process-independent unsigned seed from a pattern ID."""
    digest = hashlib.sha256(pattern_id.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big", signed=False)


class MockDataGenerator:
    """Generate reproducible payloads without touching NumPy global RNG state."""

    _BAR_TYPES = frozenset(
        {ChartType.GROUPED_BAR, ChartType.STACKED_BAR, ChartType.HORIZONTAL_BAR}
    )
    _LINE_TYPES = frozenset({ChartType.LINE_TREND, ChartType.MULTI_LINE})
    _SCATTER_TYPES = frozenset({ChartType.SCATTER, ChartType.BUBBLE})
    _DISTRIBUTION_TYPES = frozenset(
        {ChartType.VIOLIN, ChartType.BOX, ChartType.DENSITY}
    )

    def generate(
        self, pattern: FigurePattern, spec: MockDataSpec | None = None
    ) -> MockDataResult:
        spec = MockDataSpec() if spec is None else spec
        seed = spec.seed if spec.seed is not None else stable_seed(pattern.id)
        seed = int(seed)
        rng = np.random.default_rng(seed)
        chart_type = pattern.chart_type
        inferred: dict[str, int] = {}
        warnings = self._irrelevant_warnings(chart_type, spec)

        if chart_type in self._BAR_TYPES:
            categories = self._count(spec.categories, 4, "categories", inferred)
            groups = self._count(spec.groups, 3, "groups", inferred)
            values = rng.uniform(1.0, 10.0, size=(categories, groups))
            # Group offsets make adjacent series visually separable while remaining positive.
            values += np.arange(groups, dtype=float)[None, :] * 2.0
            payload = BarMockData(
                categories=[f"Category {i + 1}" for i in range(categories)],
                groups=[f"Group {i + 1}" for i in range(groups)],
                values=values.tolist(),
            )
        elif chart_type in self._LINE_TYPES:
            groups = self._count(spec.groups, 3, "groups", inferred)
            points = self._count(spec.points, 10, "points", inferred)
            x = np.arange(points, dtype=float)
            baseline = np.arange(groups, dtype=float)[:, None] * 2.0 + 1.0
            y = baseline + np.cumsum(rng.uniform(0.05, 1.0, size=(groups, points)), axis=1)
            payload = LineMockData(
                x=x.tolist(),
                y=y.tolist(),
                labels=[f"Series {i + 1}" for i in range(groups)],
            )
        elif chart_type in self._SCATTER_TYPES:
            points = self._count(spec.points, 20, "points", inferred)
            x = rng.uniform(0.5, 10.0, size=points)
            y = 0.8 * x + rng.uniform(0.2, 2.0, size=points)
            size = None
            if chart_type is ChartType.BUBBLE:
                size = rng.uniform(20.0, 120.0, size=points)
            payload = ScatterMockData(x=x.tolist(), y=y.tolist(), size=None if size is None else size.tolist())
        elif chart_type is ChartType.HEATMAP:
            rows = self._count(spec.matrix_rows, 5, "matrix_rows", inferred)
            cols = self._count(spec.matrix_cols, 6, "matrix_cols", inferred)
            matrix = rng.uniform(0.5, 10.0, size=(rows, cols))
            payload = MatrixMockData(matrix=matrix.tolist())
        elif chart_type in self._DISTRIBUTION_TYPES:
            categories = self._count(spec.categories, 4, "categories", inferred)
            samples = self._count(
                spec.distribution_samples, 50, "distribution_samples", inferred
            )
            distributions = [
                rng.normal(loc=2.0 + i * 1.5, scale=0.35, size=samples).clip(0.05).tolist()
                for i in range(categories)
            ]
            payload = DistributionMockData(
                categories=[f"Category {i + 1}" for i in range(categories)],
                distributions=distributions,
            )
        else:
            warnings.append(
                CLIWarning(
                    code="MOCK_UNSUPPORTED",
                    message=f"No mock data generator for chart type {chart_type.value}",
                    details={"chart_type": chart_type.value},
                )
            )
            return MockDataResult(
                status=MockDataStatus.UNSUPPORTED,
                seed=seed,
                spec=spec,
                inferred_defaults=inferred,
                warnings=warnings,
                data=None,
            )

        return MockDataResult(
            status=MockDataStatus.SUCCESS,
            seed=seed,
            spec=spec,
            inferred_defaults=inferred,
            warnings=warnings,
            data=payload,
        )

    @staticmethod
    def _count(value: int | None, default: int, name: str, inferred: dict[str, int]) -> int:
        if value is None:
            inferred[name] = default
            return default
        return value

    @classmethod
    def _irrelevant_warnings(
        cls, chart_type: ChartType, spec: MockDataSpec
    ) -> list[CLIWarning]:
        relevant: set[str]
        if chart_type in cls._BAR_TYPES:
            relevant = {"categories", "groups"}
        elif chart_type in cls._LINE_TYPES:
            relevant = {"groups", "points"}
        elif chart_type in cls._SCATTER_TYPES:
            relevant = {"points"}
        elif chart_type is ChartType.HEATMAP:
            relevant = {"matrix_rows", "matrix_cols"}
        elif chart_type in cls._DISTRIBUTION_TYPES:
            relevant = {"categories", "distribution_samples"}
        else:
            relevant = set()
        warnings: list[CLIWarning] = []
        for field_name in (
            "categories",
            "groups",
            "points",
            "matrix_rows",
            "matrix_cols",
            "distribution_samples",
        ):
            if field_name not in relevant and getattr(spec, field_name) is not None:
                warnings.append(
                    CLIWarning(
                        code="MOCK_SPEC_IRRELEVANT",
                        message=f"{field_name} is ignored for {chart_type.value}",
                        details={"field": field_name, "chart_type": chart_type.value},
                    )
                )
        return warnings


__all__ = ["MockDataGenerator", "stable_seed"]
