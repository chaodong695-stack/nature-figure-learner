"""Deterministic, read-only filtering and ranking for Figure KB entries."""

from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from pathlib import Path

from pydantic import ValidationError

from .models import (
    CLIWarning,
    IndexEntry,
    QueryError,
    QueryMatch,
    QueryResult,
    QuerySpec,
)
from .repository import PatternDocumentError, iter_pattern_files, read_pattern_document


def _value(value: object) -> object:
    return getattr(value, "value", value)


def _casefold(value: str | None) -> str:
    return (value or "").casefold()


def _score(value: float | int | None) -> float:
    """Return a descending-sort key where missing scores sort last."""
    return -float(value) if value is not None else float("inf")


def _tag_set(tags: Iterable[str]) -> set[str]:
    return {tag.strip().casefold() for tag in tags if tag.strip()}


def _similarity(candidate: IndexEntry, reference: IndexEntry) -> float:
    chart = float(candidate.chart_type == reference.chart_type)
    layout = float(candidate.layout_archetype == reference.layout_archetype)
    color = float(candidate.color_scheme == reference.color_scheme)
    left, right = _tag_set(candidate.tags), _tag_set(reference.tags)
    tag_jaccard = len(left & right) / len(left | right) if left | right else 1.0
    return 0.35 * chart + 0.25 * layout + 0.20 * color + 0.20 * tag_jaccard


def _matches_filters(entry: IndexEntry, spec: QuerySpec) -> tuple[bool, list[str]]:
    reasons: list[str] = []

    if spec.ids and entry.id not in spec.ids:
        return False, reasons
    if spec.source_types and entry.source_type not in spec.source_types:
        return False, reasons
    if spec.chart_types and entry.chart_type not in spec.chart_types:
        return False, reasons
    if spec.journals:
        journals = {_casefold(value) for value in spec.journals}
        if _casefold(entry.source_journal) not in journals:
            return False, reasons
    if spec.year_from is not None and (
        entry.source_year is None or entry.source_year < spec.year_from
    ):
        return False, reasons
    if spec.year_to is not None and (
        entry.source_year is None or entry.source_year > spec.year_to
    ):
        return False, reasons
    if spec.layout_archetypes and entry.layout_archetype not in spec.layout_archetypes:
        return False, reasons
    if spec.color_schemes and entry.color_scheme not in spec.color_schemes:
        return False, reasons

    tags = _tag_set(entry.tags)
    required = _tag_set(spec.tags_all)
    if required and not required.issubset(tags):
        return False, reasons
    any_tags = _tag_set(spec.tags_any)
    if any_tags and not tags.intersection(any_tags):
        return False, reasons

    checks: tuple[tuple[str, float | int | None, float | int | None], ...] = (
        ("quality", entry.quality_rating, spec.min_quality),
        ("validation", entry.validation_score, spec.min_validation),
        (
            "memory_score",
            entry.memory_score.total if entry.memory_score is not None else None,
            spec.min_memory_score,
        ),
        ("application_count", entry.application_count, spec.min_application_count),
    )
    for label, observed, minimum in checks:
        if minimum is not None:
            if observed is None or observed < minimum:
                return False, reasons
            reasons.append(f"{label}>={minimum}")

    if spec.ids and entry.id in spec.ids:
        reasons.append("id")
    if spec.source_types:
        reasons.append("source_type")
    if spec.chart_types:
        reasons.append("chart_type")
    if spec.journals:
        reasons.append("journal")
    if spec.layout_archetypes:
        reasons.append("layout_archetype")
    if spec.color_schemes:
        reasons.append("color_scheme")
    if required:
        reasons.append("tags_all")
    if any_tags:
        reasons.append("tags_any")
    if not reasons:
        reasons.append("all entries")
    return True, reasons


def _sort_key(match: QueryMatch, sort_by: str) -> tuple[object, ...]:
    entry = match.entry
    normalized = sort_by.casefold().replace("-", "_")
    if normalized in {"similarity", "similarity_score"}:
        return (-float(match.similarity_score or 0.0), entry.id)
    if normalized in {"quality", "quality_rating"}:
        return (_score(entry.quality_rating), entry.id)
    if normalized in {"validation", "validation_score"}:
        return (_score(entry.validation_score), entry.id)
    if normalized in {"memory", "memory_score", "memory_total"}:
        total = entry.memory_score.total if entry.memory_score is not None else None
        return (_score(total), entry.id)
    if normalized in {"usage", "application_count"}:
        return (-entry.application_count, entry.id)
    if normalized == "id":
        return (entry.id,)
    memory = entry.memory_score.total if entry.memory_score is not None else None
    return (_score(memory), _score(entry.quality_rating), _score(entry.validation_score), -entry.application_count, entry.id)


def query_entries(entries: Sequence[IndexEntry], spec: QuerySpec) -> QueryResult:
    """Filter and rank entries without mutating the supplied sequence or models."""
    query_spec = spec if isinstance(spec, QuerySpec) else QuerySpec.model_validate(spec)
    source_entries = list(entries)
    reference: IndexEntry | None = None
    if query_spec.reference_id is not None:
        reference = next(
            (entry for entry in source_entries if entry.id == query_spec.reference_id), None
        )
        if reference is None:
            return QueryResult(
                total_matches=0,
                returned_count=0,
                truncated=False,
                sort_by=query_spec.sort_by,
                matches=[],
                error=QueryError(
                    code="QUERY_REFERENCE_NOT_FOUND",
                    message=f"reference pattern not found: {query_spec.reference_id}",
                    details={"reference_id": query_spec.reference_id},
                ),
            )

    matches: list[QueryMatch] = []
    for entry in source_entries:
        matched, reasons = _matches_filters(entry, query_spec)
        if not matched:
            continue
        similarity = _similarity(entry, reference) if reference is not None else None
        if reference is not None:
            reasons = [*reasons, f"similarity={similarity:.6f}"]
        matches.append(
            QueryMatch(
                entry=entry.model_copy(deep=True),
                similarity_score=similarity,
                match_reasons=reasons,
            )
        )

    matches.sort(key=lambda match: _sort_key(match, query_spec.sort_by))
    total = len(matches)
    limited = matches[: query_spec.limit]
    return QueryResult(
        total_matches=total,
        returned_count=len(limited),
        truncated=len(limited) < total,
        sort_by=query_spec.sort_by,
        matches=limited,
    )


def _warning(code: str, message: str, **details: object) -> CLIWarning:
    return CLIWarning(code=code, message=message, details=details)


def _load_index_entries(root: Path) -> tuple[list[IndexEntry], list[CLIWarning], bool]:
    index_path = root / "index.json"
    warnings: list[CLIWarning] = []
    if index_path.is_file():
        try:
            raw = json.loads(index_path.read_text(encoding="utf-8"))
            if not isinstance(raw, list):
                raise ValueError("index must be a JSON array")
            entries: list[IndexEntry] = []
            for position, item in enumerate(raw):
                try:
                    entries.append(IndexEntry.model_validate(item))
                except ValidationError as exc:
                    warnings.append(
                        _warning(
                            "QUERY_INVALID_INDEX_ENTRY",
                            f"invalid index entry at position {position}",
                            position=position,
                            error=str(exc),
                        )
                    )
            return entries, warnings, True
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            warnings.append(
                _warning(
                    "QUERY_INDEX_FALLBACK",
                    "index.json is missing or corrupt; scanned Markdown",
                    error=str(exc),
                )
            )
            return [], warnings, False
    warnings.append(_warning("QUERY_INDEX_FALLBACK", "index.json is missing or corrupt; scanned Markdown"))
    return [], warnings, False


def _scan_markdown_entries(root: Path) -> tuple[list[IndexEntry], list[CLIWarning]]:
    entries: list[IndexEntry] = []
    warnings: list[CLIWarning] = []
    for path in iter_pattern_files(root):
        try:
            document = read_pattern_document(path)
            entries.append(IndexEntry.from_pattern(document.pattern, path.relative_to(root)))
        except PatternDocumentError as exc:
            warnings.append(
                _warning("QUERY_INVALID_PATTERN", "invalid pattern file skipped", path=str(path), location=exc.location, error=exc.message)
            )
    return entries, warnings


def query_kb(kb_path: Path, spec: QuerySpec) -> QueryResult:
    """Query a KB index, falling back to a read-only Markdown scan when needed."""
    root = Path(kb_path).resolve(strict=False)
    entries, warnings, index_valid = _load_index_entries(root)
    if not index_valid:
        entries, scan_warnings = _scan_markdown_entries(root)
        warnings.extend(scan_warnings)
    result = query_entries(entries, spec)
    if warnings:
        result = result.model_copy(update={"warnings": warnings}, deep=True)
    return result
