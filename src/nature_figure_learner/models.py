"""Strict, serializable contracts for Figure KB records and their index."""

from __future__ import annotations

import re
from collections.abc import Mapping
from copy import deepcopy
from datetime import date as Date
from enum import Enum
from math import isfinite
from pathlib import Path
from typing import Annotated, Generic, Literal, TypeVar

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    ValidationInfo,
    field_validator,
    model_validator,
)


EnumType = TypeVar("EnumType", bound=Enum)


def _strip_optional_text(value: object) -> object:
    """Trim optional text while leaving non-strings for Pydantic to reject."""
    if not isinstance(value, str):
        return value
    return value.strip() or None


def _require_optional_string(value: object, field_name: str) -> object:
    """Reject non-string text values before Pydantic can coerce them."""
    if value is None or isinstance(value, str):
        return value
    raise ValueError(f"{field_name} must be a string or null")


def _require_enum_control(
    value: object, enum_type: type[EnumType], field_name: str
) -> object:
    """Allow only a controlled enum instance or its serialized string value."""
    if isinstance(value, (enum_type, str)):
        return value
    raise ValueError(f"{field_name} must be a string or {enum_type.__name__}")


def _require_string_list(value: object, field_name: str) -> object:
    """Reject non-string list members before sequence item coercion."""
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{field_name} must be a list or tuple of strings")
    if any(not isinstance(item, str) for item in value):
        raise ValueError(f"{field_name} entries must be strings")
    return value


def _has_text(value: object) -> bool:
    """Return whether a candidate value contains non-whitespace text."""
    return isinstance(value, str) and bool(value.strip())


def _validate_json_compatible(
    value: object, path: str = "value", active_ids: set[int] | None = None
) -> None:
    """Reject values that cannot be serialized as strict JSON."""
    if active_ids is None:
        active_ids = set()
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        if not isfinite(value):
            raise ValueError(f"{path} must contain only finite numbers")
        return
    if isinstance(value, Enum):
        _validate_json_compatible(value.value, path, active_ids)
        return
    if isinstance(value, BaseModel):
        value_id = id(value)
        if value_id in active_ids:
            raise ValueError(f"{path} contains a cyclic container")
        active_ids.add(value_id)
        try:
            serialized = value.model_dump(mode="json")
        except Exception as exc:
            raise ValueError(f"{path} must be JSON serializable") from exc
        try:
            _validate_json_compatible(serialized, path, active_ids)
        finally:
            active_ids.remove(value_id)
        return
    if isinstance(value, Mapping):
        value_id = id(value)
        if value_id in active_ids:
            raise ValueError(f"{path} contains a cyclic container")
        active_ids.add(value_id)
        try:
            for key, item in value.items():
                if not isinstance(key, str):
                    raise ValueError(f"{path} object keys must be strings")
                _validate_json_compatible(item, f"{path}.{key}", active_ids)
        finally:
            active_ids.remove(value_id)
        return
    if isinstance(value, (list, tuple)):
        value_id = id(value)
        if value_id in active_ids:
            raise ValueError(f"{path} contains a cyclic container")
        active_ids.add(value_id)
        try:
            for index, item in enumerate(value):
                _validate_json_compatible(item, f"{path}[{index}]", active_ids)
        finally:
            active_ids.remove(value_id)
        return
    raise ValueError(f"{path} contains a non-JSON-compatible value")


class StrictModel(BaseModel):
    """Base model that rejects undocumented data and validates assignments."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class SourceType(str, Enum):
    IMAGE = "image"
    CODE = "code"
    MANUAL = "manual"


class ChartType(str, Enum):
    GROUPED_BAR = "grouped-bar"
    STACKED_BAR = "stacked-bar"
    HORIZONTAL_BAR = "horizontal-bar"
    LINE_TREND = "line-trend"
    MULTI_LINE = "multi-line"
    HEATMAP = "heatmap"
    SCATTER = "scatter"
    BUBBLE = "bubble"
    RADAR_POLAR = "radar-polar"
    FOREST_PLOT = "forest-plot"
    VIOLIN = "violin"
    BOX = "box"
    DENSITY = "density"
    PIE_DONUT = "pie-donut"
    FILL_BETWEEN = "fill-between"
    SANKEY = "sankey"
    UPSET = "upset"
    IMAGE_PLATE = "image-plate"
    SCHEMATIC = "schematic"
    NETWORK = "network"
    OTHER = "other"


class LayoutArchetype(str, Enum):
    QUANTITATIVE_GRID = "quantitative-grid"
    SCHEMATIC_LED_COMPOSITE = "schematic-led-composite"
    IMAGE_PLATE_QUANT = "image-plate-quant"
    ASYMMETRIC_MIXED_MODALITY = "asymmetric-mixed-modality"


class ColorScheme(str, Enum):
    NATURE_NMI_PASTEL = "nature-nmi-pastel"
    NATURE_IMAGING = "nature-imaging"
    NATURE_CLINICAL = "nature-clinical"
    NATURE_GENOMICS = "nature-genomics"
    NATURE_MATERIAL = "nature-material"
    CATEGORICAL_HIGH_CONTRAST = "categorical-high-contrast"
    SEQUENTIAL_SINGLE_HUE = "sequential-single-hue"
    DIVERGING = "diverging"
    MONOCHROME = "monochrome"
    OTHER = "other"


class FontFamily(str, Enum):
    ARIAL = "Arial"
    HELVETICA = "Helvetica"
    TIMES = "Times"
    SERIF = "serif"
    SANS_SERIF = "sans-serif"
    OTHER = "other"


class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class EnvelopeStatus(str, Enum):
    SUCCESS = "success"
    UNSUPPORTED = "unsupported"
    ERROR = "error"


class CLIWarning(StrictModel):
    code: str
    message: str
    details: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("details")
    @classmethod
    def validate_json_details(cls, value: dict[str, JsonValue]) -> dict[str, JsonValue]:
        _validate_json_compatible(value, "details")
        return value


class CLIError(StrictModel):
    type: str
    code: str
    message: str
    details: dict[str, JsonValue] = Field(default_factory=dict)
    retryable: bool = False

    @field_validator("details")
    @classmethod
    def validate_json_details(cls, value: dict[str, JsonValue]) -> dict[str, JsonValue]:
        _validate_json_compatible(value, "details")
        return value


T = TypeVar("T")


class CLIEnvelope(StrictModel, Generic[T]):
    """Stable result contract shared by command-line operations."""

    status: EnvelopeStatus
    command: str
    schema_version: Literal["1.0"] = "1.0"
    data: T | None
    warnings: list[CLIWarning] = Field(default_factory=list)
    error: CLIError | None = None

    @model_validator(mode="before")
    @classmethod
    def validate_candidate_state(cls, data: object) -> object:
        """Reject invalid assignment candidates before state mutation."""
        if not isinstance(data, dict):
            return data
        if "status" not in data:
            return data
        status = data["status"]
        if not isinstance(status, (EnvelopeStatus, str)):
            raise ValueError("status must be a string or EnvelopeStatus")
        status_value = status.value if isinstance(status, EnvelopeStatus) else status
        if status_value in (
            EnvelopeStatus.SUCCESS.value,
            EnvelopeStatus.UNSUPPORTED.value,
        ):
            if data.get("data") is None:
                raise ValueError(
                    f"{status_value} envelope requires a non-null data payload"
                )
            if data.get("error") is not None:
                raise ValueError(
                    f"{status_value} envelope cannot include an error payload"
                )
        elif status_value == EnvelopeStatus.ERROR.value:
            if data.get("data") is not None:
                raise ValueError("error envelope requires a null data payload")
            if data.get("error") is None:
                raise ValueError("error envelope requires an error payload")
        return data

    @field_validator("command", mode="before")
    @classmethod
    def normalize_command(cls, value: object) -> object:
        if not isinstance(value, str):
            raise ValueError("command must be a string")
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("command must not be blank")
        return normalized

    @field_validator("data")
    @classmethod
    def validate_json_data(cls, value: T | None) -> T | None:
        if value is None:
            return value
        _validate_json_compatible(value, "data")
        return value

    @model_validator(mode="after")
    def validate_status_payload(self) -> "CLIEnvelope[T]":
        if self.status in (EnvelopeStatus.SUCCESS, EnvelopeStatus.UNSUPPORTED):
            if self.data is None:
                raise ValueError(
                    f"{self.status.value} envelope requires a non-null data payload"
                )
            if self.error is not None:
                raise ValueError(
                    f"{self.status.value} envelope cannot include an error payload"
                )
        elif self.status is EnvelopeStatus.ERROR:
            if self.data is not None:
                raise ValueError("error envelope requires a null data payload")
            if self.error is None:
                raise ValueError("error envelope requires an error payload")
        return self

    @classmethod
    def success(
        cls,
        command: str,
        data: T,
        *,
        warnings: list[CLIWarning] | None = None,
    ) -> "CLIEnvelope[T]":
        return cls(
            status=EnvelopeStatus.SUCCESS,
            command=command,
            data=deepcopy(data),
            warnings=[] if warnings is None else deepcopy(warnings),
        )

    @classmethod
    def unsupported(
        cls,
        command: str,
        data: T,
        *,
        warnings: list[CLIWarning] | None = None,
    ) -> "CLIEnvelope[T]":
        return cls(
            status=EnvelopeStatus.UNSUPPORTED,
            command=command,
            data=deepcopy(data),
            warnings=[] if warnings is None else deepcopy(warnings),
        )

    @classmethod
    def failure(
        cls,
        command: str,
        error: CLIError,
        *,
        warnings: list[CLIWarning] | None = None,
    ) -> "CLIEnvelope[T]":
        return cls(
            status=EnvelopeStatus.ERROR,
            command=command,
            data=None,
            warnings=[] if warnings is None else deepcopy(warnings),
            error=deepcopy(error),
        )


class Feedback(StrictModel):
    date: Date
    rating: float = Field(ge=1, le=5)
    notes: str

    @field_validator("notes")
    @classmethod
    def strip_notes(cls, value: str) -> str:
        return value.strip()


class CaseNote(StrictModel):
    date: Date | None = None
    note: str

    @field_validator("note")
    @classmethod
    def strip_note(cls, value: str) -> str:
        return value.strip()


class MemoryScoreComponents(StrictModel):
    quality: float = Field(ge=0)
    validation: float = Field(ge=0)
    reuse: float = Field(ge=0)
    feedback: float = Field(ge=0)
    recency: float = Field(ge=0)


class MemoryScore(StrictModel):
    total: float = Field(ge=0, le=100)
    components: MemoryScoreComponents
    formula: str


class PatternRelations(StrictModel):
    similar_to: list[str] = Field(default_factory=list)
    superseded_by: list[str] = Field(default_factory=list)
    contraindicated_for: list[str] = Field(default_factory=list)


class FigurePattern(StrictModel):
    """Validated source-of-truth record for one reusable figure pattern."""

    schema_version: Literal["1.0"] = "1.0"
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,127}$")

    source_type: SourceType
    source_doi: str | None = None
    source_journal: str | None = None
    source_year: int | None = Field(default=None, ge=1600, le=2200)
    source_figure: str | None = None
    source_paper_title: str | None = None
    source_url: str | None = None

    chart_type: ChartType
    chart_type_description: str | None = None
    sub_chart_types: list[ChartType] = Field(default_factory=list)
    layout_archetype: LayoutArchetype
    panel_count: int = Field(ge=1)

    color_scheme: ColorScheme
    color_strategy_description: str | None = None
    extracted_colors: list[str] = Field(default_factory=list)
    font_family: FontFamily | str | None = None
    base_font_size_pt: float | None = Field(default=None, gt=0, le=72)

    matched_nature_figure_pattern: int | None = Field(default=None, ge=1, le=16)
    novel_pattern: bool = False
    novel_pattern_name: str | None = None
    tags: list[str] = Field(default_factory=list)
    quality_rating: float | None = Field(default=None, ge=1, le=5)
    confidence: Confidence = Confidence.MEDIUM
    analysis_date: Date

    validation_score: int | None = Field(default=None, ge=1, le=5)
    application_count: int = Field(default=0, ge=0)
    last_applied: Date | None = None
    application_feedback: list[Feedback] = Field(default_factory=list)
    comparative_notes: list[dict[str, JsonValue]] = Field(default_factory=list)
    memory_score: MemoryScore | None = None
    success_cases: list[CaseNote] = Field(default_factory=list)
    failure_cases: list[CaseNote] = Field(default_factory=list)
    recommendation_rationale: str | None = None
    relations: PatternRelations = Field(default_factory=PatternRelations)

    scientific_claim: str | None = None
    evidence_hierarchy: str | None = None
    hero_panel: str | None = None
    statistical_annotations: str | None = None
    grid_structure: str | None = None

    backend: str | None = None
    figsize: tuple[float, float] | None = None
    export_formats: list[str] = Field(default_factory=list)
    dpi: int | None = Field(default=None, ge=72, le=2400)
    extensions: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("source_doi", mode="before")
    @classmethod
    def normalize_doi(cls, value: object) -> object:
        if value is None:
            return None
        _require_optional_string(value, "source_doi")
        normalized = value.strip()
        normalized = re.sub(r"^doi:\s*", "", normalized, flags=re.IGNORECASE)
        normalized = re.sub(
            r"^(?:https?://)?(?:dx\.)?doi\.org/",
            "",
            normalized,
            flags=re.IGNORECASE,
        )
        return normalized.strip().lower() or None

    @field_validator("source_figure", mode="before")
    @classmethod
    def normalize_source_figure(cls, value: object) -> object:
        if value is None:
            return None
        _require_optional_string(value, "source_figure")
        return _strip_optional_text(value)

    @field_validator("id", mode="before")
    @classmethod
    def validate_id_input(cls, value: object) -> object:
        return _require_optional_string(value, "id")

    @field_validator(
        "source_type", "chart_type", "layout_archetype", "color_scheme", mode="before"
    )
    @classmethod
    def validate_control_input(cls, value: object, info: ValidationInfo) -> object:
        enum_types: dict[str, type[Enum]] = {
            "source_type": SourceType,
            "chart_type": ChartType,
            "layout_archetype": LayoutArchetype,
            "color_scheme": ColorScheme,
        }
        return _require_enum_control(value, enum_types[info.field_name], info.field_name)

    @field_validator("novel_pattern", mode="before")
    @classmethod
    def validate_novel_pattern_input(cls, value: object) -> object:
        if type(value) is not bool:
            raise ValueError("novel_pattern must be a boolean")
        return value

    @field_validator("sub_chart_types", mode="before")
    @classmethod
    def validate_sub_chart_type_input(cls, value: object) -> object:
        _require_string_list(value, "sub_chart_types")
        for item in value:
            _require_enum_control(item, ChartType, "sub_chart_types entries")
        return value

    @field_validator("tags", "extracted_colors", "export_formats", mode="before")
    @classmethod
    def validate_string_list_input(cls, value: object, info: ValidationInfo) -> object:
        return _require_string_list(value, info.field_name)

    @field_validator("extracted_colors")
    @classmethod
    def normalize_colors(cls, value: list[str]) -> list[str]:
        colors: list[str] = []
        for color in value:
            normalized = color.strip()
            if not re.fullmatch(r"#[0-9A-Fa-f]{6}", normalized):
                raise ValueError("each extracted color must be a #RRGGBB hex value")
            colors.append(normalized.upper())
        return colors

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, value: list[str]) -> list[str]:
        return [tag.strip() for tag in value]

    @field_validator(
        "source_journal",
        "source_paper_title",
        "source_url",
        "chart_type_description",
        "color_strategy_description",
        "novel_pattern_name",
        "recommendation_rationale",
        "scientific_claim",
        "evidence_hierarchy",
        "hero_panel",
        "statistical_annotations",
        "grid_structure",
        "backend",
        mode="before",
    )
    @classmethod
    def strip_optional_descriptions(
        cls, value: object, info: ValidationInfo
    ) -> object:
        if value is None:
            return None
        _require_optional_string(value, info.field_name)
        return _strip_optional_text(value)

    @field_validator("font_family", mode="before")
    @classmethod
    def normalize_font_family(cls, value: object) -> object:
        if value is None:
            return None
        _require_optional_string(value, "font_family")
        normalized = _strip_optional_text(value)
        if normalized is None or not isinstance(normalized, str):
            return normalized
        try:
            return FontFamily(normalized)
        except ValueError:
            return normalized

    @field_validator("export_formats")
    @classmethod
    def normalize_export_formats(cls, value: list[str]) -> list[str]:
        normalized = [format_name.strip() for format_name in value]
        if any(not format_name for format_name in normalized):
            raise ValueError("export_formats entries must be non-blank strings")
        return normalized

    @model_validator(mode="before")
    @classmethod
    def validate_candidate_requirements(cls, data: object) -> object:
        """Reject incomplete cross-field assignment candidates before mutation."""
        if not isinstance(data, dict):
            return data

        chart_type = data.get("chart_type")
        _require_enum_control(chart_type, ChartType, "chart_type")
        if chart_type in (ChartType.OTHER, ChartType.OTHER.value) and not _has_text(
            data.get("chart_type_description")
        ):
            raise ValueError("chart_type_description is required when chart_type is other")

        color_scheme = data.get("color_scheme")
        _require_enum_control(color_scheme, ColorScheme, "color_scheme")
        if color_scheme in (ColorScheme.OTHER, ColorScheme.OTHER.value) and not _has_text(
            data.get("color_strategy_description")
        ):
            raise ValueError(
                "color_strategy_description is required when color_scheme is other"
            )

        novel_pattern = data.get("novel_pattern", False)
        if "novel_pattern" in data and type(novel_pattern) is not bool:
            raise ValueError("novel_pattern must be a boolean")
        if novel_pattern and not _has_text(
            data.get("novel_pattern_name")
        ):
            raise ValueError("novel_pattern_name is required when novel_pattern is true")
        return data

    @model_validator(mode="after")
    def validate_interdependent_fields(self) -> "FigurePattern":
        if self.chart_type is ChartType.OTHER and not self.chart_type_description:
            raise ValueError("chart_type_description is required when chart_type is other")
        if self.color_scheme is ColorScheme.OTHER and not self.color_strategy_description:
            raise ValueError(
                "color_strategy_description is required when color_scheme is other"
            )
        if self.novel_pattern and not self.novel_pattern_name:
            raise ValueError("novel_pattern_name is required when novel_pattern is true")
        return self


class IndexEntry(StrictModel):
    """Derived, query-oriented projection of a validated FigurePattern."""

    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,127}$")
    file: str
    source_type: SourceType
    source_journal: str | None = None
    source_year: int | None = Field(default=None, ge=1600, le=2200)
    chart_type: ChartType
    color_scheme: ColorScheme
    layout_archetype: LayoutArchetype
    tags: list[str] = Field(default_factory=list)
    quality_rating: float | None = Field(default=None, ge=1, le=5)
    validation_score: int | None = Field(default=None, ge=1, le=5)
    application_count: int = Field(default=0, ge=0)
    memory_score: MemoryScore | None = None
    success_cases: list[CaseNote] = Field(default_factory=list)
    failure_cases: list[CaseNote] = Field(default_factory=list)
    recommendation_rationale: str | None = None
    relations: PatternRelations = Field(default_factory=PatternRelations)
    matched_nature_figure_pattern: int | None = Field(default=None, ge=1, le=16)
    analysis_date: Date

    @classmethod
    def from_pattern(cls, pattern: FigurePattern, file: str | Path) -> "IndexEntry":
        """Derive an index record from a validated pattern instead of hand assembly."""
        return cls(
            id=pattern.id,
            file=str(file).replace("\\", "/"),
            source_type=pattern.source_type,
            source_journal=pattern.source_journal,
            source_year=pattern.source_year,
            chart_type=pattern.chart_type,
            color_scheme=pattern.color_scheme,
            layout_archetype=pattern.layout_archetype,
            tags=list(pattern.tags),
            quality_rating=pattern.quality_rating,
            validation_score=pattern.validation_score,
            application_count=pattern.application_count,
            memory_score=(
                pattern.memory_score.model_copy(deep=True)
                if pattern.memory_score is not None
                else None
            ),
            success_cases=[case.model_copy(deep=True) for case in pattern.success_cases],
            failure_cases=[case.model_copy(deep=True) for case in pattern.failure_cases],
            recommendation_rationale=pattern.recommendation_rationale,
            relations=pattern.relations.model_copy(deep=True),
            matched_nature_figure_pattern=pattern.matched_nature_figure_pattern,
            analysis_date=pattern.analysis_date,
        )


class QuerySpec(StrictModel):
    """Pure, serializable constraints for deterministic pattern queries."""

    ids: list[str] = Field(default_factory=list)
    source_types: list[SourceType] = Field(default_factory=list)
    chart_types: list[ChartType] = Field(default_factory=list)
    journals: list[str] = Field(default_factory=list)
    year_from: int | None = Field(default=None, ge=1600, le=2200)
    year_to: int | None = Field(default=None, ge=1600, le=2200)
    layout_archetypes: list[LayoutArchetype] = Field(default_factory=list)
    color_schemes: list[ColorScheme] = Field(default_factory=list)
    tags_all: list[str] = Field(default_factory=list)
    tags_any: list[str] = Field(default_factory=list)
    min_quality: float | None = Field(default=None, ge=1, le=5)
    min_validation: int | None = Field(default=None, ge=1, le=5)
    min_memory_score: float | None = Field(default=None, ge=0, le=100)
    min_application_count: int | None = Field(default=None, ge=0)
    reference_id: str | None = None
    sort_by: str = "default"
    limit: int = Field(default=5, ge=1, le=100)

    @field_validator(
        "ids", "journals", "tags_all", "tags_any", mode="before"
    )
    @classmethod
    def validate_text_lists(cls, value: object, info: ValidationInfo) -> object:
        return _require_string_list(value, info.field_name)

    @field_validator("reference_id", "sort_by", mode="before")
    @classmethod
    def normalize_query_text(cls, value: object, info: ValidationInfo) -> object:
        if value is None and info.field_name == "reference_id":
            return None
        if not isinstance(value, str):
            raise ValueError(f"{info.field_name} must be a string")
        normalized = value.strip()
        if info.field_name == "reference_id":
            return normalized or None
        return normalized or "default"

    @field_validator("ids", "journals", "tags_all", "tags_any")
    @classmethod
    def strip_query_text_lists(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item.strip()]

    @model_validator(mode="after")
    def validate_year_range(self) -> "QuerySpec":
        if self.year_from is not None and self.year_to is not None:
            if self.year_from > self.year_to:
                raise ValueError("year_from must be less than or equal to year_to")
        return self


class QueryError(StrictModel):
    """Structured query failure that does not require raising an exception."""

    code: str
    message: str
    details: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("details")
    @classmethod
    def validate_json_details(cls, value: dict[str, JsonValue]) -> dict[str, JsonValue]:
        _validate_json_compatible(value, "details")
        return value


class QueryMatch(StrictModel):
    """One immutable query result projection and its ranking explanation."""

    entry: IndexEntry
    similarity_score: float | None = Field(default=None, ge=0, le=1)
    match_reasons: list[str] = Field(default_factory=list)

    @field_validator("match_reasons", mode="before")
    @classmethod
    def validate_match_reasons(cls, value: object) -> object:
        return _require_string_list(value, "match_reasons")


class QueryResult(StrictModel):
    """Deterministic query output including warnings and structured failures."""

    total_matches: int = Field(default=0, ge=0)
    returned_count: int = Field(default=0, ge=0)
    truncated: bool = False
    sort_by: str = "default"
    matches: list[QueryMatch] = Field(default_factory=list)
    warnings: list[CLIWarning] = Field(default_factory=list)
    error: QueryError | None = None

    @model_validator(mode="after")
    def validate_counts(self) -> "QueryResult":
        if self.returned_count != len(self.matches):
            raise ValueError("returned_count must equal the number of matches")
        if self.returned_count > self.total_matches:
            raise ValueError("returned_count cannot exceed total_matches")
        if self.truncated != (self.returned_count < self.total_matches):
            raise ValueError("truncated must reflect total_matches and returned_count")
        return self


class MockDataStatus(str, Enum):
    SUCCESS = "success"
    UNSUPPORTED = "unsupported"


class RenderStatus(str, Enum):
    SUCCESS = "success"
    UNSUPPORTED = "unsupported"
    ERROR = "error"


class ValidationStatus(str, Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    NOT_RUN = "not-run"


class ValidationCheck(StrictModel):
    """One reproducible objective validation observation."""

    id: str
    status: ValidationStatus
    expected: JsonValue | None = None
    observed: JsonValue | None = None
    message: str


class ValidationResult(StrictModel):
    """Objective validation without scientific or LLM-derived judgement."""

    status: ValidationStatus
    objective_score: float | None = Field(default=None, ge=0, le=100)
    checks: list[ValidationCheck] = Field(default_factory=list)
    failed_check_ids: list[str] = Field(default_factory=list)
    warnings: list[CLIWarning] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_summary(self) -> "ValidationResult":
        failed = [check.id for check in self.checks if check.status is ValidationStatus.FAIL]
        if failed and not self.failed_check_ids:
            object.__setattr__(self, "failed_check_ids", failed)
        if self.failed_check_ids != failed:
            raise ValueError("failed_check_ids must match failed checks")
        if self.status is ValidationStatus.NOT_RUN and self.objective_score is not None:
            raise ValueError("not-run validation cannot have an objective score")
        return self


class ScientificReview(StrictModel):
    """Optional LLM-owned review, kept separate from objective validation."""

    scientific_claim: str | None = None
    hero_panel: str | None = None
    evidence_hierarchy: str | None = None
    overall_visual_semantics: str | None = None


class RenderResult(StrictModel):
    """Structured outcome and effective settings for one render attempt."""

    pattern_id: str
    renderer_id: str
    status: RenderStatus
    output_file: str | None = None
    metadata: dict[str, JsonValue] = Field(default_factory=dict)
    warnings: list[CLIWarning] = Field(default_factory=list)
    error: CLIError | None = None

    @model_validator(mode="after")
    def validate_payload(self) -> "RenderResult":
        if self.status is RenderStatus.SUCCESS:
            if self.output_file is None:
                raise ValueError("successful render requires output_file")
            if self.error is not None:
                raise ValueError("successful render cannot include an error")
        elif self.status is RenderStatus.UNSUPPORTED:
            if self.error is not None:
                raise ValueError("unsupported render cannot include an error")
        elif self.status is RenderStatus.ERROR:
            if self.error is None:
                raise ValueError("error render requires an error payload")
            if self.output_file is not None:
                raise ValueError("error render cannot include output_file")
        _validate_json_compatible(self.metadata, "metadata")
        return self


class MockDataSpec(StrictModel):
    """Optional controls for deterministic synthetic figure data."""

    seed: int | None = None
    categories: int | None = Field(default=None, ge=1)
    groups: int | None = Field(default=None, ge=1)
    points: int | None = Field(default=None, ge=2)
    matrix_rows: int | None = Field(default=None, ge=2)
    matrix_cols: int | None = Field(default=None, ge=2)
    distribution_samples: int | None = Field(default=None, ge=2)


class BarMockData(StrictModel):
    kind: Literal["bar"] = "bar"
    categories: list[str]
    groups: list[str]
    values: list[list[float]]
    synthetic: Literal[True] = True


class LineMockData(StrictModel):
    kind: Literal["line"] = "line"
    x: list[float]
    y: list[list[float]]
    labels: list[str] = Field(default_factory=list)
    synthetic: Literal[True] = True


class ScatterMockData(StrictModel):
    kind: Literal["scatter"] = "scatter"
    x: list[float]
    y: list[float]
    size: list[float] | None = None
    synthetic: Literal[True] = True


class MatrixMockData(StrictModel):
    kind: Literal["matrix"] = "matrix"
    matrix: list[list[float]]
    synthetic: Literal[True] = True


class DistributionMockData(StrictModel):
    kind: Literal["distribution"] = "distribution"
    categories: list[str]
    distributions: list[list[float]]
    synthetic: Literal[True] = True


MockPayload = Annotated[
    BarMockData
    | LineMockData
    | ScatterMockData
    | MatrixMockData
    | DistributionMockData,
    Field(discriminator="kind"),
]


class MockDataResult(StrictModel):
    status: MockDataStatus
    seed: int
    spec: MockDataSpec
    inferred_defaults: dict[str, int] = Field(default_factory=dict)
    warnings: list[CLIWarning] = Field(default_factory=list)
    data: MockPayload | None = None

    @model_validator(mode="after")
    def validate_payload(self) -> "MockDataResult":
        if self.status is MockDataStatus.SUCCESS and self.data is None:
            raise ValueError("successful mock data requires a payload")
        if self.status is MockDataStatus.UNSUPPORTED and self.data is not None:
            raise ValueError("unsupported mock data cannot include a payload")
        return self


class SelfValidationResult(StrictModel):
    """Outputs from mock generation, rendering, and objective validation."""

    pattern_id: str
    mock: MockDataResult
    render: RenderResult
    validation: ValidationResult
