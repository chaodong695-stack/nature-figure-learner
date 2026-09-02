"""Unified JSON-envelope command line interface for the Figure KB."""

from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from pathlib import Path
from typing import Any, Callable

from pydantic import ValidationError

from .models import (
    CLIEnvelope,
    CLIError,
    ChartType,
    FigurePattern,
    LayoutArchetype,
    ColorScheme,
    MockDataSpec,
    QuerySpec,
    SourceType,
)
from .query import query_kb
from .repository import (
    DuplicatePolicy,
    KBDuplicateError,
    KBIntegrityError,
    KBLockedError,
    PatternDocumentError,
    audit_kb,
    read_pattern_document,
    rebuild_index,
    save_pattern,
    iter_pattern_files,
)
from .validation import run_self_validation


ERROR_CODES = {
    "KB_NOT_CONFIGURED", "SCHEMA_INVALID", "KB_DUPLICATE", "KB_LOCKED",
    "KB_IO_ERROR", "QUERY_INVALID", "RENDER_ERROR", "INTERNAL_ERROR",
}


class CLIArgumentError(Exception):
    """Raised for parser failures that must use the normal JSON envelope."""


class _EnvelopeParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise CLIArgumentError(message)


def _error(command: str, code: str, message: str, *, details: dict[str, Any] | None = None,
           error_type: str = "CLIError", retryable: bool = False) -> CLIEnvelope[Any]:
    return CLIEnvelope.failure(command, CLIError(type=error_type, code=code,
                                                   message=message,
                                                   details=details or {},
                                                   retryable=retryable))


def _read_json(path: str) -> Any:
    text = sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8")
    return json.loads(text)


def _kb_path(value: str | None) -> Path | None:
    if value:
        return Path(value).expanduser().resolve(strict=False)
    env = os.environ.get("FIGURE_KB_HOME")
    if env:
        return Path(env).expanduser().resolve(strict=False)
    configured = None
    try:
        import importlib.util
        manager_path = Path(__file__).resolve().parents[2] / "scripts" / "kb_location_manager.py"
        spec = importlib.util.spec_from_file_location("_figure_kb_location_manager", manager_path)
        if spec and spec.loader:
            manager = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(manager)
            configured = manager.get_kb_path()
    except Exception:
        configured = None
    return Path(configured).expanduser().resolve(strict=False) if configured else None


def _require_kb(command: str, value: str | None) -> tuple[Path | None, CLIEnvelope[Any] | None]:
    path = _kb_path(value)
    if path is None:
        return None, _error(command, "KB_NOT_CONFIGURED", "figure KB location is not configured")
    return path, None


def _pattern_from_input(path: str) -> FigurePattern:
    return FigurePattern.model_validate(_read_json(path))


def _query_spec(args: argparse.Namespace) -> QuerySpec:
    values: dict[str, Any] = {}
    for key in ("ids", "source_types", "chart_types", "journals", "layout_archetypes", "color_schemes", "tags_all", "tags_any"):
        value = getattr(args, key, None)
        if value:
            values[key] = value
    for key in ("year_from", "year_to", "min_quality", "min_validation", "min_memory_score", "min_application_count", "reference_id", "sort_by", "limit"):
        value = getattr(args, key, None)
        if value is not None:
            values[key] = value
    return QuerySpec.model_validate(values)


def _schema_export(_: argparse.Namespace) -> CLIEnvelope[Any]:
    return CLIEnvelope.success("schema export", {"schema": FigurePattern.model_json_schema()})


def _pattern_validate(args: argparse.Namespace) -> CLIEnvelope[Any]:
    pattern = _pattern_from_input(args.input)
    return CLIEnvelope.success("pattern validate", {"valid": True, "pattern": pattern.model_dump(mode="json")})


def _pattern_save(args: argparse.Namespace) -> CLIEnvelope[Any]:
    path, failure = _require_kb("pattern save", args.kb_path)
    if failure:
        return failure
    pattern = _pattern_from_input(args.input)
    narrative = Path(args.narrative).read_text(encoding="utf-8")
    result = save_pattern(path, pattern, narrative, duplicate_policy=DuplicatePolicy(args.duplicate_policy))
    return CLIEnvelope.success("pattern save", {"status": result.status.value, "affected_ids": list(result.affected_ids)})


def _query(args: argparse.Namespace) -> CLIEnvelope[Any]:
    path, failure = _require_kb("query", args.kb_path)
    if failure:
        return failure
    try:
        spec = _query_spec(args)
    except ValidationError as exc:
        return _error("query", "QUERY_INVALID", str(exc), error_type="ValidationError")
    result = query_kb(path, spec)
    if result.error is not None:
        return _error("query", "QUERY_INVALID", result.error.message, details=result.error.details, error_type="QueryError")
    return CLIEnvelope.success("query", result.model_dump(mode="json"), warnings=result.warnings)


def _index_audit(args: argparse.Namespace) -> CLIEnvelope[Any]:
    path, failure = _require_kb("index audit", args.kb_path)
    if failure:
        return failure
    audit = audit_kb(path)
    return CLIEnvelope.success("index audit", {"valid_count": audit.valid_count, "invalid_count": audit.invalid_count,
                                                "issues": [{"path": str(i.path), "location": i.location, "message": i.message} for i in audit.issues]})


def _index_rebuild(args: argparse.Namespace) -> CLIEnvelope[Any]:
    path, failure = _require_kb("index rebuild", args.kb_path)
    if failure:
        return failure
    result = rebuild_index(path)
    return CLIEnvelope.success("index rebuild", {"entry_count": result.entry_count, "index_path": str(result.index_path)})


def _find_pattern(path: Path, pattern_id: str) -> FigurePattern:
    for file in iter_pattern_files(path):
        document = read_pattern_document(file)
        if document.pattern.id == pattern_id:
            return document.pattern
    raise FileNotFoundError(f"pattern not found: {pattern_id}")


def _self_validate(args: argparse.Namespace) -> CLIEnvelope[Any]:
    path, failure = _require_kb("self-validate", args.kb_path)
    if failure:
        return failure
    pattern = _find_pattern(path, args.pattern_id)
    spec = MockDataSpec.model_validate(_read_json(args.spec)) if args.spec else None
    result = run_self_validation(pattern, spec=spec, output_dir=Path(args.output_dir))
    if result.render.status.value == "unsupported":
        return CLIEnvelope.unsupported("self-validate", result.model_dump(mode="json"))
    if result.render.status.value == "error":
        message = result.render.error.message if result.render.error else "render failed"
        return _error("self-validate", "RENDER_ERROR", message, details={"pattern_id": pattern.id}, error_type="RenderError")
    return CLIEnvelope.success("self-validate", result.model_dump(mode="json"), warnings=result.validation.warnings)


def _build_parser() -> argparse.ArgumentParser:
    parser = _EnvelopeParser(prog="figure_kb")
    parser.add_argument("--kb-path", dest="kb_path", default=None)
    parser.add_argument("--debug", action="store_true")
    sub = parser.add_subparsers(dest="command_group", required=True)

    schema = sub.add_parser("schema"); schema_sub = schema.add_subparsers(dest="schema_command", required=True)
    schema_sub.add_parser("export").set_defaults(handler=_schema_export)

    pattern = sub.add_parser("pattern"); pattern_sub = pattern.add_subparsers(dest="pattern_command", required=True)
    validate = pattern_sub.add_parser("validate"); validate.add_argument("--input", required=True); validate.set_defaults(handler=_pattern_validate)
    save = pattern_sub.add_parser("save"); save.add_argument("--input", required=True); save.add_argument("--narrative", required=True); save.add_argument("--duplicate-policy", choices=[p.value for p in DuplicatePolicy], default="error"); save.add_argument("--kb-path", dest="kb_path", default=argparse.SUPPRESS); save.set_defaults(handler=_pattern_save)

    query = sub.add_parser("query")
    query.add_argument("--kb-path", dest="kb_path", default=argparse.SUPPRESS); query.add_argument("--shortcut", action="store_true")
    query.add_argument("--id", dest="ids", action="append"); query.add_argument("--source-type", dest="source_types", action="append", choices=[x.value for x in SourceType]); query.add_argument("--chart-type", dest="chart_types", action="append", choices=[x.value for x in ChartType]); query.add_argument("--journal", dest="journals", action="append"); query.add_argument("--year-from", type=int); query.add_argument("--year-to", type=int); query.add_argument("--layout-archetype", dest="layout_archetypes", action="append", choices=[x.value for x in LayoutArchetype]); query.add_argument("--color-scheme", dest="color_schemes", action="append", choices=[x.value for x in ColorScheme]); query.add_argument("--tag-all", dest="tags_all", action="append"); query.add_argument("--tag-any", dest="tags_any", action="append"); query.add_argument("--min-quality", type=float); query.add_argument("--min-validation", type=int); query.add_argument("--min-memory-score", type=float); query.add_argument("--min-application-count", type=int); query.add_argument("--reference-id"); query.add_argument("--sort-by", default="default"); query.add_argument("--limit", type=int, default=5); query.set_defaults(handler=_query)

    index = sub.add_parser("index"); index_sub = index.add_subparsers(dest="index_command", required=True)
    audit = index_sub.add_parser("audit"); audit.add_argument("--kb-path", dest="kb_path", default=argparse.SUPPRESS); audit.set_defaults(handler=_index_audit)
    rebuild = index_sub.add_parser("rebuild"); rebuild.add_argument("--kb-path", dest="kb_path", default=argparse.SUPPRESS); rebuild.set_defaults(handler=_index_rebuild)

    selfval = sub.add_parser("self-validate"); selfval.add_argument("--pattern-id", required=True); selfval.add_argument("--spec"); selfval.add_argument("--output-dir", required=True); selfval.add_argument("--kb-path", dest="kb_path", default=argparse.SUPPRESS); selfval.set_defaults(handler=_self_validate)
    return parser


def _command_name(args: argparse.Namespace) -> str:
    if args.command_group == "schema": return "schema export"
    if args.command_group == "pattern": return f"pattern {args.pattern_command}"
    return args.command_group


def _command_name_from_argv(argv: list[str]) -> str:
    if not argv:
        return "cli"
    if argv[0] == "schema" and len(argv) > 1:
        return "schema " + argv[1]
    if argv[0] == "pattern" and len(argv) > 1:
        return "pattern " + argv[1]
    return argv[0]


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    raw_argv = list(argv if argv is not None else sys.argv[1:])
    debug = "--debug" in raw_argv
    if debug:
        raw_argv = [item for item in raw_argv if item != "--debug"]
    command_hint = _command_name_from_argv(raw_argv)
    try:
        args = parser.parse_args(raw_argv)
        envelope = args.handler(args)
    except CLIArgumentError as exc:
        code = "QUERY_INVALID" if command_hint == "query" else "SCHEMA_INVALID"
        envelope = _error(command_hint, code, str(exc), error_type="ArgumentError")
    except (ValidationError, json.JSONDecodeError, OSError, UnicodeError, PatternDocumentError) as exc:
        code = "SCHEMA_INVALID" if isinstance(exc, (ValidationError, json.JSONDecodeError, PatternDocumentError)) else "KB_IO_ERROR"
        envelope = _error(_command_name(args) if "args" in locals() and hasattr(args, "command_group") else "cli", code, str(exc), error_type=type(exc).__name__)
    except KBDuplicateError as exc:
        envelope = _error(_command_name(args), "KB_DUPLICATE", str(exc), details={"affected_ids": list(exc.affected_ids)}, error_type=type(exc).__name__)
    except KBLockedError as exc:
        envelope = _error(_command_name(args), "KB_LOCKED", str(exc), error_type=type(exc).__name__, retryable=True)
    except KBIntegrityError as exc:
        envelope = _error(_command_name(args), "SCHEMA_INVALID", str(exc), details={"invalid_count": exc.audit.invalid_count}, error_type=type(exc).__name__)
    except Exception as exc:
        if debug:
            traceback.print_exc(file=sys.stderr)
        envelope = _error(_command_name(args) if "args" in locals() and hasattr(args, "command_group") else "cli", "INTERNAL_ERROR", str(exc), error_type=type(exc).__name__)
    print(json.dumps(envelope.model_dump(mode="json"), ensure_ascii=False, separators=(",", ":")))
    return 0 if envelope.status.value in ("success", "unsupported") else 1


__all__ = ["main"]
