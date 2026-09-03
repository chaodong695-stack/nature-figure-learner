"""Deterministic image checks and self-validation orchestration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, UnidentifiedImageError

from .mock_data import MockDataGenerator
from .models import (
    BarMockData,
    ChartType,
    DistributionMockData,
    FigurePattern,
    LineMockData,
    MatrixMockData,
    MockDataResult,
    RenderResult,
    RenderStatus,
    ScatterMockData,
    SelfValidationResult,
    ValidationCheck,
    ValidationResult,
    ValidationStatus,
)
from .renderers import RendererRegistry, build_default_registry, render_pattern


def _check(identifier: str, status: ValidationStatus, expected: Any, observed: Any, message: str) -> ValidationCheck:
    return ValidationCheck(
        id=identifier,
        status=status,
        expected=expected,
        observed=observed,
        message=message,
    )


def _payload_shape(pattern: FigurePattern, mock: MockDataResult) -> tuple[bool, Any, Any]:
    """Check typed mock dimensions against the requested or inferred dimensions."""
    payload = mock.data
    if payload is None:
        return False, "typed payload", None
    spec = mock.spec
    inferred = mock.inferred_defaults

    def wanted(name: str) -> int | None:
        value = getattr(spec, name)
        return value if value is not None else inferred.get(name)

    if isinstance(payload, BarMockData):
        observed = [len(payload.categories), len(payload.groups), [len(row) for row in payload.values]]
        expected = [wanted("categories"), wanted("groups"), "each row has groups entries"]
        ok = (
            len(payload.categories) == (wanted("categories") or len(payload.categories))
            and len(payload.groups) == (wanted("groups") or len(payload.groups))
            and len(payload.values) == len(payload.categories)
            and all(len(row) == len(payload.groups) for row in payload.values)
        )
    elif isinstance(payload, LineMockData):
        observed = [len(payload.x), len(payload.y), [len(row) for row in payload.y]]
        expected = [wanted("points"), wanted("groups"), "each series has points entries"]
        ok = (
            len(payload.x) == (wanted("points") or len(payload.x))
            and len(payload.y) == (wanted("groups") or len(payload.y))
            and all(len(row) == len(payload.x) for row in payload.y)
        )
    elif isinstance(payload, ScatterMockData):
        observed = [len(payload.x), len(payload.y), None if payload.size is None else len(payload.size)]
        expected = [wanted("points"), wanted("points"), "bubble size matches points when supplied"]
        ok = (
            len(payload.x) == len(payload.y)
            and len(payload.x) == (wanted("points") or len(payload.x))
            and (payload.size is None or len(payload.size) == len(payload.x))
        )
    elif isinstance(payload, MatrixMockData):
        rows = len(payload.matrix)
        cols = len(payload.matrix[0]) if payload.matrix else 0
        observed = [rows, cols]
        expected = [wanted("matrix_rows"), wanted("matrix_cols")]
        ok = rows == (wanted("matrix_rows") or rows) and cols == (wanted("matrix_cols") or cols) and all(len(row) == cols for row in payload.matrix)
    elif isinstance(payload, DistributionMockData):
        observed = [len(payload.categories), len(payload.distributions), [len(row) for row in payload.distributions]]
        expected = [wanted("categories"), wanted("distribution_samples"), "each distribution has samples entries"]
        ok = (
            len(payload.categories) == (wanted("categories") or len(payload.categories))
            and len(payload.distributions) == len(payload.categories)
            and all(len(row) == (wanted("distribution_samples") or len(row)) for row in payload.distributions)
        )
    else:
        return False, "known typed payload", type(payload).__name__
    return ok, expected, observed


def _rgb(value: str) -> tuple[int, int, int] | None:
    text = value.strip().lstrip("#")
    if len(text) != 6:
        return None
    try:
        return tuple(int(text[index : index + 2], 16) for index in (0, 2, 4))  # type: ignore[return-value]
    except ValueError:
        return None


def _expected_pixels(pattern: FigurePattern) -> tuple[int, int]:
    count = pattern.panel_count
    cols = max(1, int(count**0.5))
    while cols * cols < count:
        cols += 1
    rows = (count + cols - 1) // cols
    figsize = pattern.figsize or (4.0, 3.0)
    dpi = pattern.dpi or 150
    return (round(figsize[0] * cols * dpi), round(figsize[1] * rows * dpi))


def _not_run() -> ValidationResult:
    return ValidationResult(status=ValidationStatus.NOT_RUN, objective_score=None)


def validate_render(
    render: RenderResult,
    pattern: FigurePattern,
    mock: MockDataResult,
) -> ValidationResult:
    """Run objective checks for a successful render.

    Unsupported capabilities and renderer errors deliberately produce NOT_RUN;
    they are not evidence that a pattern failed validation.
    """
    if render.status is not RenderStatus.SUCCESS:
        return _not_run()

    checks: list[ValidationCheck] = []
    checks.append(
        _check(
            "schema_valid",
            ValidationStatus.PASS,
            "validated FigurePattern",
            pattern.schema_version,
            "pattern conforms to the FigurePattern schema",
        )
    )
    shape_ok, shape_expected, shape_observed = _payload_shape(pattern, mock)
    checks.append(_check(
        "mock_payload_dimensions",
        ValidationStatus.PASS if shape_ok else ValidationStatus.FAIL,
        shape_expected,
        shape_observed,
        "typed mock payload dimensions are consistent" if shape_ok else "typed mock payload dimensions are inconsistent",
    ))
    checks.append(_check("renderer_success", ValidationStatus.PASS, "success", render.status.value, "renderer completed successfully"))

    image: Image.Image | None = None
    pixels: np.ndarray | None = None
    try:
        if not render.output_file:
            raise FileNotFoundError("render output_file is missing")
        image = Image.open(render.output_file)
        image.load()
        image = image.convert("RGB")
        pixels = np.asarray(image, dtype=np.uint8)
        checks.append(_check("image_readable", ValidationStatus.PASS, "readable RGB image", list(image.size), "image can be opened and decoded"))
    except (OSError, UnidentifiedImageError, ValueError) as exc:
        checks.append(_check("image_readable", ValidationStatus.FAIL, "readable RGB image", None, f"image could not be read: {exc}"))

    if pixels is None or image is None:
        return _result(checks, [])

    variance = pixels.reshape(-1, 3).var(axis=0)
    nonblank = bool(float(variance.max()) > 0.5)
    checks.append(_check("image_nonblank", ValidationStatus.PASS if nonblank else ValidationStatus.FAIL, "non-zero channel variance", variance.round(3).tolist(), "image contains visual variation" if nonblank else "image is blank or effectively uniform"))

    expected_size = _expected_pixels(pattern)
    actual_size = tuple(image.size)
    checks.append(_check("expected_dimensions", ValidationStatus.PASS if actual_size == expected_size else ValidationStatus.FAIL, list(expected_size), list(actual_size), "image dimensions match pattern layout" if actual_size == expected_size else "image dimensions do not match pattern layout"))

    expected_panels = pattern.panel_count
    observed_panels = render.metadata.get("panel_count")
    panel_ok = observed_panels == expected_panels
    checks.append(_check("panel_count_metadata", ValidationStatus.PASS if panel_ok else ValidationStatus.FAIL, expected_panels, observed_panels, "panel metadata matches pattern" if panel_ok else "panel metadata is missing or mismatched"))

    expected_figsize = [float(value) for value in (pattern.figsize or (4.0, 3.0))]
    layout = render.metadata.get("layout")
    layout_ok = (
        isinstance(layout, dict)
        and layout.get("panel_count") == expected_panels
        and layout.get("figsize") == expected_figsize
    )
    checks.append(_check(
        "layout_metadata",
        ValidationStatus.PASS if layout_ok else ValidationStatus.FAIL,
        {"figsize": expected_figsize, "panel_count": expected_panels},
        layout,
        "layout metadata matches pattern" if layout_ok else "layout metadata is missing or mismatched",
    ))

    palette_value = render.metadata.get("effective_palette")
    palette_metadata_invalid = False
    if palette_value is None:
        palette = list(pattern.extracted_colors)
    elif isinstance(palette_value, (list, tuple)):
        palette = list(palette_value)
    else:
        palette_metadata_invalid = True
        checks.append(_check(
            "palette_presence",
            ValidationStatus.WARN,
            "list of RGB hex colors",
            palette_value,
            "effective_palette metadata is not a list; palette inspection was skipped",
        ))
        palette = []
    colors = [_rgb(item) for item in palette if isinstance(item, str)]
    colors = [item for item in colors if item is not None]
    if colors:
        flat = pixels.reshape(-1, 3).astype(int)
        matches = [int(np.min(np.sqrt(((flat - np.asarray(color)) ** 2).sum(axis=1)))) <= 30 for color in colors]
        palette_ok = all(matches)
        observed_palette = {str(color): bool(match) for color, match in zip(palette, matches)}
        checks.append(_check("palette_presence", ValidationStatus.PASS if palette_ok else ValidationStatus.WARN, "each configured RGB color within tolerance 30", observed_palette, "configured palette colors appear in image" if palette_ok else "one or more configured palette colors were not found within tolerance"))
    elif not palette_metadata_invalid:
        checks.append(_check("palette_presence", ValidationStatus.WARN, "configured RGB palette", [], "no valid palette colors were available to inspect"))

    fallback = any(warning.code == "FONT_FALLBACK" for warning in render.warnings)
    checks.append(_check("font_fallback", ValidationStatus.WARN if fallback else ValidationStatus.PASS, "requested font or explicit fallback warning", "fallback" if fallback else "requested", "font fallback was used" if fallback else "requested font was accepted"))
    return _result(checks, list(render.warnings))


class ObjectiveValidator:
    """Stateless facade for callers that prefer an explicit validator object."""

    def validate(
        self,
        pattern: FigurePattern,
        mock: MockDataResult,
        render: RenderResult,
    ) -> ValidationResult:
        return validate_render(render, pattern, mock)


def _result(checks: list[ValidationCheck], warnings: list[Any]) -> ValidationResult:
    failed = [check.id for check in checks if check.status is ValidationStatus.FAIL]
    ran = [check for check in checks if check.status in (ValidationStatus.PASS, ValidationStatus.WARN, ValidationStatus.FAIL)]
    if not ran:
        status = ValidationStatus.NOT_RUN
        score = None
    elif failed:
        status = ValidationStatus.FAIL
        score = sum(100.0 if check.status is ValidationStatus.PASS else 50.0 if check.status is ValidationStatus.WARN else 0.0 for check in ran) / len(ran)
    elif any(check.status is ValidationStatus.WARN for check in ran):
        status = ValidationStatus.WARN
        score = sum(100.0 if check.status is ValidationStatus.PASS else 50.0 for check in ran) / len(ran)
    else:
        status = ValidationStatus.PASS
        score = 100.0
    return ValidationResult(status=status, objective_score=score, checks=checks, failed_check_ids=failed, warnings=list(warnings))


def run_self_validation(
    pattern: FigurePattern,
    spec: Any = None,
    output_dir: Path | str = Path("preview"),
    registry: RendererRegistry | None = None,
) -> SelfValidationResult:
    """Generate deterministic mock data, render it, and validate the result."""
    mock = MockDataGenerator().generate(pattern, spec)
    render = render_pattern(pattern, mock, Path(output_dir), registry or build_default_registry())
    validation = validate_render(render, pattern, mock)
    return SelfValidationResult(pattern_id=pattern.id, mock=mock, render=render, validation=validation)


__all__ = ["ObjectiveValidator", "run_self_validation", "validate_render"]
