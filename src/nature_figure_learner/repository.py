"""Deterministic Markdown persistence helpers for Figure KB records.

Markdown documents are the durable source of truth.  The JSON index is always
derived from valid Markdown and may be rebuilt without changing those sources.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

import yaml
from pydantic import ValidationError

from .models import FigurePattern, IndexEntry


_DELIMITER = "---"
_SAFE_ID = re.compile(r"^[a-z0-9][a-z0-9-]{1,127}$")


class PatternDocumentError(ValueError):
    """A document error with a stable source and field/frontmatter location."""

    def __init__(self, source: str | Path, location: str, message: str) -> None:
        self.source = str(source)
        self.location = location
        self.message = message
        super().__init__(f"{self.source}:{self.location}: {self.message}")


@dataclass(frozen=True)
class PatternDocument:
    """A validated pattern together with its human-readable Markdown narrative."""

    pattern: FigurePattern
    narrative: str
    path: Path | None = None


@dataclass(frozen=True)
class AuditIssue:
    """One invalid KB document discovered by a read-only audit."""

    path: Path
    location: str
    message: str


@dataclass(frozen=True)
class KBAudit:
    """Stable summary of valid and invalid source documents."""

    valid_count: int
    invalid_count: int
    issues: tuple[AuditIssue, ...]


class KBIntegrityError(ValueError):
    """Raised when strict index rebuild encounters invalid source Markdown."""

    def __init__(self, audit: KBAudit) -> None:
        self.audit = audit
        super().__init__(
            f"KB audit failed: {audit.invalid_count} invalid pattern document(s)"
        )


@dataclass(frozen=True)
class IndexRebuildResult:
    """Result of a successful derived-index replacement."""

    entry_count: int
    index_path: Path


class DuplicatePolicy(str, Enum):
    ERROR = "error"
    SKIP = "skip"
    OVERWRITE = "overwrite"
    CREATE_COPY = "create-copy"


class SaveStatus(str, Enum):
    CREATED = "created"
    OVERWRITTEN = "overwritten"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class SaveResult:
    status: SaveStatus
    affected_ids: tuple[str, ...]


class KBDuplicateError(ValueError):
    code = "KB_DUPLICATE"

    def __init__(self, message: str, affected_ids: tuple[str, ...] = ()) -> None:
        self.affected_ids = affected_ids
        super().__init__(message)


class KBLockedError(RuntimeError):
    code = "KB_LOCKED"


class KBWriteLock:
    """Small process lock backed by an exclusively-created JSON marker file."""

    def __init__(self, kb_path: Path, *, stale_after_seconds: float = 3600) -> None:
        self.root = Path(kb_path).resolve(strict=False)
        self.path = self.root / ".kb.lock"
        self.lock_path = self.path
        self.stale_after_seconds = stale_after_seconds
        self._owned = False
        self._marker_content: bytes | None = None

    def acquire(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        payload = {
            "pid": os.getpid(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
        flags |= getattr(os, "O_BINARY", 0)
        try:
            fd = os.open(self.path, flags)
        except FileExistsError:
            if self._remove_stale():
                return self.acquire()
            raise KBLockedError(f"KB is locked: {self.path}")
        marker_content = (json.dumps(payload) + "\n").encode("utf-8")
        written_content = bytearray()
        try:
            offset = 0
            while offset < len(marker_content):
                written = os.write(fd, marker_content[offset:])
                if written <= 0:
                    raise OSError("lock marker write made no progress")
                written_content.extend(marker_content[offset : offset + written])
                offset += written
        except Exception:
            try:
                os.close(fd)
            finally:
                self._remove_owned_marker(bytes(written_content))
            raise
        try:
            os.close(fd)
        except Exception:
            self._remove_owned_marker(bytes(written_content))
            raise
        self._marker_content = marker_content
        self._owned = True

    def _remove_owned_marker(self, marker_content: bytes) -> None:
        try:
            current = self.path.read_bytes().replace(b"\r\n", b"\n")
            if current == marker_content:
                self.path.unlink()
        except OSError:
            pass

    def _remove_stale(self) -> bool:
        try:
            marker_before = self.path.read_bytes()
            payload = json.loads(marker_before.decode("utf-8"))
            timestamp = datetime.fromisoformat(payload["timestamp"])
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
            age = (datetime.now(timezone.utc) - timestamp).total_seconds()
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
            return False
        if age <= self.stale_after_seconds:
            return False
        try:
            if self.path.read_bytes() != marker_before:
                return False
        except FileNotFoundError:
            return False
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass
        return True

    def release(self) -> None:
        if self._owned:
            try:
                current_content = self.path.read_bytes().replace(b"\r\n", b"\n")
                if self._marker_content is not None and current_content == self._marker_content:
                    self.path.unlink()
            except OSError:
                pass
            self._owned = False
            self._marker_content = None

    def __enter__(self) -> "KBWriteLock":
        self.acquire()
        return self

    def __exit__(self, *_: object) -> None:
        self.release()


def _normalize_newlines(text: str) -> str:
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _format_validation_location(error: dict[str, object]) -> str:
    location = error.get("loc", ())
    if not isinstance(location, tuple):
        return "frontmatter"
    return ".".join(str(part) for part in location) or "frontmatter"


def _validated_pattern(pattern: FigurePattern) -> FigurePattern:
    """Reject constructed or otherwise bypassed models before using them as paths."""
    if not isinstance(pattern, FigurePattern):
        raise TypeError("pattern must be a FigurePattern")
    try:
        payload = {
            field_name: getattr(pattern, field_name)
            for field_name in FigurePattern.model_fields
        }
        return FigurePattern.model_validate(payload)
    except ValidationError as exc:
        first = exc.errors()[0]
        raise ValueError(
            f"unvalidated FigurePattern at {_format_validation_location(first)}: "
            f"{first['msg']}"
        ) from exc


def parse_pattern_markdown(text: str, *, source: str | Path = "<memory>") -> PatternDocument:
    """Parse YAML frontmatter and validate it through the authoritative model."""
    normalized = _normalize_newlines(text)
    lines = normalized.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\n") != _DELIMITER:
        raise PatternDocumentError(
            source, "frontmatter", "must start with a standalone --- delimiter"
        )

    closing_index: int | None = None
    for index, line in enumerate(lines[1:], start=1):
        if line.rstrip("\n") == _DELIMITER:
            closing_index = index
            break
    if closing_index is None:
        raise PatternDocumentError(source, "frontmatter", "missing closing --- delimiter")

    frontmatter_text = "".join(lines[1:closing_index])
    narrative = "".join(lines[closing_index + 1 :])
    try:
        raw_pattern = yaml.safe_load(frontmatter_text)
    except yaml.YAMLError as exc:
        raise PatternDocumentError(source, "frontmatter", f"invalid YAML: {exc}") from exc
    if not isinstance(raw_pattern, dict):
        raise PatternDocumentError(source, "frontmatter", "must be a mapping")

    try:
        pattern = FigurePattern.model_validate(raw_pattern)
    except ValidationError as exc:
        first = exc.errors()[0]
        raise PatternDocumentError(
            source,
            _format_validation_location(first),
            str(first["msg"]),
        ) from exc
    return PatternDocument(pattern=pattern, narrative=narrative)


def read_pattern_document(path: Path) -> PatternDocument:
    """Read and parse a single Markdown source document without modifying it."""
    document_path = Path(path)
    try:
        text = document_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise PatternDocumentError(document_path, "file", str(exc)) from exc
    document = parse_pattern_markdown(text, source=document_path)
    return PatternDocument(
        pattern=document.pattern, narrative=document.narrative, path=document_path
    )


def serialize_pattern_document(pattern: FigurePattern, narrative: str) -> str:
    """Serialize an already validated record with a newline-normalized narrative."""
    validated = _validated_pattern(pattern)
    normalized_narrative = _normalize_newlines(narrative).rstrip("\n")
    if normalized_narrative:
        normalized_narrative += "\n"
    frontmatter = yaml.safe_dump(
        validated.model_dump(mode="json", exclude_none=False), sort_keys=False
    )
    return f"{_DELIMITER}\n{frontmatter}{_DELIMITER}\n{normalized_narrative}"


def pattern_path(kb_path: Path, pattern: FigurePattern) -> Path:
    """Return the only permitted source path for a validated pattern."""
    validated = _validated_pattern(pattern)
    chart_type = validated.chart_type.value
    pattern_id = validated.id
    if not _SAFE_ID.fullmatch(pattern_id) or any(
        separator in pattern_id for separator in ("/", "\\", ":")
    ):
        raise ValueError("pattern id is not safe for a filesystem path")
    if not chart_type or any(separator in chart_type for separator in ("/", "\\", ":")):
        raise ValueError("chart_type is not safe for a filesystem path")

    root = Path(kb_path).resolve(strict=False)
    candidate = (
        root / "patterns" / "chart-type" / chart_type / f"{pattern_id}.md"
    ).resolve(strict=False)
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("pattern path escapes KB root") from exc
    return candidate


def iter_pattern_files(kb_path: Path):
    """Yield direct pattern Markdown children in deterministic relative-path order."""
    root = Path(kb_path).resolve(strict=False)
    pattern_root = root / "patterns" / "chart-type"
    if not pattern_root.is_dir():
        return
    files = sorted(
        (path for path in pattern_root.glob("*/*.md") if path.is_file()),
        key=lambda path: path.relative_to(root).as_posix(),
    )
    yield from files


def audit_kb(kb_path: Path) -> KBAudit:
    """Audit source documents without rewriting or repairing the KB."""
    valid_count = 0
    issues: list[AuditIssue] = []
    for path in iter_pattern_files(kb_path):
        try:
            read_pattern_document(path)
        except PatternDocumentError as exc:
            issues.append(
                AuditIssue(path=path, location=exc.location, message=exc.message)
            )
        else:
            valid_count += 1
    return KBAudit(
        valid_count=valid_count,
        invalid_count=len(issues),
        issues=tuple(issues),
    )


def build_index_entries(kb_path: Path) -> list[IndexEntry]:
    """Project valid Markdown sources into deterministically ordered index entries."""
    root = Path(kb_path).resolve(strict=False)
    entries: list[IndexEntry] = []
    for path in iter_pattern_files(root):
        try:
            document = read_pattern_document(path)
        except PatternDocumentError:
            continue
        entries.append(IndexEntry.from_pattern(document.pattern, path.relative_to(root)))
    return sorted(entries, key=lambda entry: (entry.id, entry.file))


def rebuild_index(kb_path: Path) -> IndexRebuildResult:
    """Strictly rebuild ``index.json`` through a same-directory atomic replacement."""
    root = Path(kb_path).resolve(strict=False)
    audit = audit_kb(root)
    if audit.invalid_count:
        raise KBIntegrityError(audit)

    entries = build_index_entries(root)
    root.mkdir(parents=True, exist_ok=True)
    index_path = root / "index.json"
    serialized = json.dumps(
        [entry.model_dump(mode="json", exclude_none=False) for entry in entries],
        ensure_ascii=False,
        indent=2,
    ) + "\n"

    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=index_path.parent,
            prefix=".index.json.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(serialized)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_path, index_path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
    return IndexRebuildResult(entry_count=len(entries), index_path=index_path)


def _atomic_write(path: Path, content: str) -> None:
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent,
            prefix=f".{path.name}.", suffix=".tmp", delete=False
        ) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(content)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def _atomic_write_bytes(path: Path, content: bytes) -> None:
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
        ) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(content)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def _restore_snapshot(path: Path, content: bytes | None) -> None:
    if content is None:
        if path.exists():
            path.unlink()
        return
    _atomic_write_bytes(path, content)


def save_pattern(
    kb_path: Path,
    pattern: FigurePattern,
    narrative: str,
    *,
    duplicate_policy: DuplicatePolicy = DuplicatePolicy.ERROR,
) -> SaveResult:
    """Persist a validated Markdown source and its derived index transactionally."""
    validated = _validated_pattern(pattern)
    if not isinstance(duplicate_policy, DuplicatePolicy):
        duplicate_policy = DuplicatePolicy(duplicate_policy)
    root = Path(kb_path).resolve(strict=False)
    target = pattern_path(root, validated)
    serialized = serialize_pattern_document(validated, narrative)

    with KBWriteLock(root):
        documents: list[PatternDocument] = []
        paths_by_id: dict[str, Path] = {}
        for path in iter_pattern_files(root):
            try:
                document = read_pattern_document(path)
            except PatternDocumentError:
                continue
            expected_name = f"{document.pattern.id}.md"
            if path.name != expected_name:
                raise KBDuplicateError(
                    f"pattern filename does not match frontmatter id: {path.name}",
                    (document.pattern.id,),
                )
            if document.pattern.id in paths_by_id:
                raise KBDuplicateError(
                    f"duplicate pattern id: {document.pattern.id}",
                    (document.pattern.id,),
                )
            documents.append(document)
            paths_by_id[document.pattern.id] = path

        same_id = paths_by_id.get(validated.id)
        doi_figure_ids = tuple(
            sorted(
                document.pattern.id
                for document in documents
                if validated.source_doi
                and validated.source_figure
                and document.pattern.source_doi == validated.source_doi
                and document.pattern.source_figure == validated.source_figure
            )
        )
        conflicts = tuple(sorted(set(([validated.id] if same_id else []) + list(doi_figure_ids))))
        if conflicts:
            if duplicate_policy is DuplicatePolicy.SKIP and not same_id:
                return SaveResult(SaveStatus.SKIPPED, doi_figure_ids)
            if duplicate_policy is DuplicatePolicy.OVERWRITE:
                if not same_id or (doi_figure_ids and doi_figure_ids != (validated.id,)):
                    raise KBDuplicateError("duplicate conflict", conflicts)
            elif duplicate_policy is DuplicatePolicy.CREATE_COPY:
                if same_id:
                    raise KBDuplicateError("duplicate conflict", conflicts)
            elif duplicate_policy is DuplicatePolicy.ERROR:
                raise KBDuplicateError("duplicate conflict", conflicts)
            elif duplicate_policy is DuplicatePolicy.SKIP:
                raise KBDuplicateError("duplicate id conflict", conflicts)

        root.mkdir(parents=True, exist_ok=True)
        target.parent.mkdir(parents=True, exist_ok=True)
        index_path = root / "index.json"
        old_target_bytes = target.read_bytes() if target.exists() else None
        old_target_path = same_id
        old_old_path_bytes = (
            old_target_path.read_bytes()
            if old_target_path is not None and old_target_path != target and old_target_path.exists()
            else None
        )
        old_index_bytes = index_path.read_bytes() if index_path.exists() else None
        try:
            _atomic_write(target, serialized)
            if old_target_path is not None and old_target_path != target and old_target_path.exists():
                old_target_path.unlink()
            rebuild_index(root)
        except Exception:
            try:
                _restore_snapshot(target, old_target_bytes)
                if old_target_path is not None and old_target_path != target:
                    if old_old_path_bytes is not None:
                        old_target_path.parent.mkdir(parents=True, exist_ok=True)
                        _restore_snapshot(old_target_path, old_old_path_bytes)
                    elif old_target_path.exists():
                        old_target_path.unlink()
                _restore_snapshot(index_path, old_index_bytes)
            finally:
                raise
        status = SaveStatus.OVERWRITTEN if same_id else SaveStatus.CREATED
        return SaveResult(status, (validated.id,))


def update_pattern(
    kb_path: Path,
    pattern_id: str,
    updates: Mapping[str, object],
) -> SaveResult:
    """Update one Markdown-backed pattern while preserving its narrative.

    Markdown remains the source of truth: the existing document is loaded,
    updates are applied to a copied model and revalidated, then persisted via
    :func:`save_pattern` so the source and derived index change together.
    """
    if not isinstance(pattern_id, str) or not pattern_id.strip():
        raise ValueError("pattern_id must be a non-blank string")
    if not isinstance(updates, Mapping):
        raise TypeError("updates must be a mapping")
    if any(not isinstance(key, str) for key in updates):
        raise ValueError("updates keys must be strings")
    if "id" in updates:
        raise ValueError("pattern id cannot be updated")
    unknown_fields = sorted(set(updates) - set(FigurePattern.model_fields))
    if unknown_fields:
        raise ValueError(f"unknown FigurePattern field(s): {', '.join(unknown_fields)}")

    root = Path(kb_path).resolve(strict=False)
    normalized_id = pattern_id.strip()
    for path in iter_pattern_files(root):
        try:
            document = read_pattern_document(path)
        except PatternDocumentError:
            continue
        if document.pattern.id != normalized_id:
            continue
        candidate = document.pattern.model_copy(update=dict(updates), deep=True)
        validated = _validated_pattern(candidate)
        return save_pattern(
            root,
            validated,
            document.narrative,
            duplicate_policy=DuplicatePolicy.OVERWRITE,
        )
    raise FileNotFoundError(f"pattern not found: {normalized_id}")
