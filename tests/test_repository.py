"""Repository tests use temporary KBs and never create repository data."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from nature_figure_learner.models import ChartType, FigurePattern
from nature_figure_learner.repository import (
    DuplicatePolicy,
    KBLockedError,
    KBDuplicateError,
    KBWriteLock,
    SaveResult,
    KBIntegrityError,
    PatternDocumentError,
    audit_kb,
    build_index_entries,
    iter_pattern_files,
    parse_pattern_markdown,
    pattern_path,
    read_pattern_document,
    rebuild_index,
    serialize_pattern_document,
    save_pattern,
    update_pattern,
)
from tests.helpers import make_pattern, valid_pattern_data, write_pattern_fixture


class PatternDocumentTests(unittest.TestCase):
    def test_round_trip_preserves_validated_pattern_and_narrative(self):
        pattern = make_pattern()
        text = serialize_pattern_document(pattern, "# Analysis\n\nSemantic text.\n")

        document = parse_pattern_markdown(text, source="fixture.md")

        self.assertEqual(document.pattern, pattern)
        self.assertEqual(document.narrative, "# Analysis\n\nSemantic text.\n")
        self.assertIsNone(document.path)

    def test_serializer_normalizes_newlines_and_emits_one_terminal_newline(self):
        text = serialize_pattern_document(make_pattern(), "# Notes\r\n\r\nBody\r\n\r\n")

        self.assertNotIn("\r", text)
        self.assertTrue(text.endswith("\n"))
        self.assertFalse(text.endswith("\n\n"))
        self.assertEqual(
            parse_pattern_markdown(text, source="fixture.md").narrative,
            "# Notes\n\nBody\n",
        )

    def test_frontmatter_errors_have_stable_source_and_location(self):
        cases = (
            ("id: pattern-001\n", "frontmatter", "must start with a standalone --- delimiter"),
            ("---\nid: pattern-001\n", "frontmatter", "missing closing --- delimiter"),
            ("---\n[unterminated\n---\n", "frontmatter", "invalid YAML"),
            ("---\n- not\n- a mapping\n---\n", "frontmatter", "must be a mapping"),
        )
        for text, location, message in cases:
            with self.subTest(text=text), self.assertRaises(PatternDocumentError) as raised:
                parse_pattern_markdown(text, source="broken.md")
            self.assertEqual(raised.exception.source, "broken.md")
            self.assertEqual(raised.exception.location, location)
            self.assertIn(message, raised.exception.message)
            self.assertEqual(str(raised.exception), f"broken.md:{location}: {raised.exception.message}")

    def test_schema_error_reports_pydantic_field_location(self):
        text = "---\n" + "\n".join(
            f"{key}: {json.dumps(value)}" for key, value in valid_pattern_data(id="bad/id").items()
        ) + "\n---\n"

        with self.assertRaises(PatternDocumentError) as raised:
            parse_pattern_markdown(text, source="invalid-schema.md")

        self.assertEqual(raised.exception.source, "invalid-schema.md")
        self.assertEqual(raised.exception.location, "id")
        self.assertIn("String should match pattern", raised.exception.message)

    def test_read_document_records_path(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "one.md"
            path.write_text(serialize_pattern_document(make_pattern(), "text\n"), encoding="utf-8")

            document = read_pattern_document(path)

        self.assertEqual(document.path, path)
        self.assertEqual(document.narrative, "text\n")


class RepositoryPathTests(unittest.TestCase):
    def test_pattern_path_uses_chart_type_tree_and_rejects_constructed_escape_values(self):
        with tempfile.TemporaryDirectory() as directory:
            kb_path = Path(directory)
            destination = pattern_path(kb_path, make_pattern())
            self.assertEqual(
                destination,
                kb_path / "patterns" / "chart-type" / "grouped-bar" / "pattern-001.md",
            )

            base_data = make_pattern().model_dump(mode="python")
            for id_value, chart_type in (
                ("../escape", ChartType.GROUPED_BAR),
                ("C:\\escape", ChartType.GROUPED_BAR),
                ("pattern-001", "..\\escape"),
                ("pattern-001", "/absolute"),
            ):
                with self.subTest(id=id_value, chart_type=chart_type):
                    unsafe = FigurePattern.model_construct(
                        **(base_data | {"id": id_value, "chart_type": chart_type})
                    )
                    with self.assertRaises(ValueError):
                        pattern_path(kb_path, unsafe)

    def test_iter_pattern_files_only_yields_expected_markdown_in_stable_order(self):
        with tempfile.TemporaryDirectory() as directory:
            kb_path = Path(directory)
            first = write_pattern_fixture(kb_path, make_pattern(id="pattern-002"))
            second = write_pattern_fixture(kb_path, make_pattern(id="pattern-001"))
            (kb_path / "patterns" / "ignore.txt").write_text("ignore", encoding="utf-8")
            (kb_path / "outside.md").write_text("ignore", encoding="utf-8")

            files = list(iter_pattern_files(kb_path))

        self.assertEqual(files, [second, first])


class AuditAndIndexTests(unittest.TestCase):
    def test_audit_is_read_only_and_reports_invalid_schema_location(self):
        with tempfile.TemporaryDirectory() as directory:
            kb_path = Path(directory)
            write_pattern_fixture(kb_path, make_pattern())
            invalid = kb_path / "patterns" / "chart-type" / "grouped-bar" / "bad.md"
            invalid.parent.mkdir(parents=True, exist_ok=True)
            invalid.write_text(
                "---\n"
                + "\n".join(
                    f"{key}: {json.dumps(value)}"
                    for key, value in valid_pattern_data(id="../bad").items()
                )
                + "\n---\n",
                encoding="utf-8",
            )
            before = invalid.read_bytes()

            audit = audit_kb(kb_path)

            self.assertEqual(audit.valid_count, 1)
            self.assertEqual(audit.invalid_count, 1)
            self.assertEqual(audit.issues[0].path, invalid)
            self.assertEqual(audit.issues[0].location, "id")
            self.assertEqual(invalid.read_bytes(), before)

    def test_build_index_entries_is_derived_from_valid_markdown_in_stable_order(self):
        with tempfile.TemporaryDirectory() as directory:
            kb_path = Path(directory)
            write_pattern_fixture(kb_path, make_pattern(id="pattern-002"))
            write_pattern_fixture(kb_path, make_pattern(id="pattern-001"))
            (kb_path / "index.json").write_text('[{"id": "stale"}]', encoding="utf-8")

            entries = build_index_entries(kb_path)

        self.assertEqual([entry.id for entry in entries], ["pattern-001", "pattern-002"])
        self.assertEqual(
            [entry.file for entry in entries],
            [
                "patterns/chart-type/grouped-bar/pattern-001.md",
                "patterns/chart-type/grouped-bar/pattern-002.md",
            ],
        )

    def test_strict_rebuild_preserves_existing_index_when_any_document_is_invalid(self):
        with tempfile.TemporaryDirectory() as directory:
            kb_path = Path(directory)
            write_pattern_fixture(kb_path, make_pattern())
            bad = kb_path / "patterns" / "chart-type" / "grouped-bar" / "bad.md"
            bad.parent.mkdir(parents=True, exist_ok=True)
            bad.write_text("---\ninvalid: true\n---\n", encoding="utf-8")
            index_path = kb_path / "index.json"
            index_path.write_text('[{"id":"old"}]\n', encoding="utf-8")
            before = index_path.read_bytes()

            with self.assertRaises(KBIntegrityError) as raised:
                rebuild_index(kb_path)

            self.assertEqual(raised.exception.audit.invalid_count, 1)
            self.assertEqual(index_path.read_bytes(), before)

    def test_successful_rebuild_writes_deterministic_index_by_atomic_replace(self):
        with tempfile.TemporaryDirectory() as directory:
            kb_path = Path(directory)
            write_pattern_fixture(kb_path, make_pattern(id="pattern-002"))
            write_pattern_fixture(kb_path, make_pattern(id="pattern-001"))
            index_path = kb_path / "index.json"
            calls: list[tuple[Path, Path]] = []
            real_replace = os.replace

            def recording_replace(source: str | Path, destination: str | Path) -> None:
                calls.append((Path(source), Path(destination)))
                real_replace(source, destination)

            with patch("nature_figure_learner.repository.os.replace", side_effect=recording_replace):
                result = rebuild_index(kb_path)

            index = json.loads(index_path.read_text(encoding="utf-8"))
            self.assertEqual(result.entry_count, 2)
            self.assertEqual([entry["id"] for entry in index], ["pattern-001", "pattern-002"])
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0][1], index_path)
            self.assertEqual(calls[0][0].parent, index_path.parent)
            self.assertFalse(calls[0][0].exists())

    def test_failed_atomic_replace_preserves_old_index_and_cleans_temporary_file(self):
        with tempfile.TemporaryDirectory() as directory:
            kb_path = Path(directory)
            write_pattern_fixture(kb_path, make_pattern())
            index_path = kb_path / "index.json"
            index_path.write_text('[{"id":"old"}]\n', encoding="utf-8")
            before = index_path.read_bytes()

            with patch("nature_figure_learner.repository.os.replace", side_effect=OSError("disk error")):
                with self.assertRaises(OSError):
                    rebuild_index(kb_path)

            self.assertEqual(index_path.read_bytes(), before)
            self.assertEqual(list(kb_path.glob(".index.json.*.tmp")), [])


class SavePatternTests(unittest.TestCase):
    def test_update_pattern_persists_validated_fields_and_preserves_narrative(self):
        with tempfile.TemporaryDirectory() as directory:
            kb = Path(directory)
            pattern = make_pattern(source_doi=None, source_figure=None)
            save_pattern(kb, pattern, "# Keep this narrative\n")

            result = update_pattern(
                kb,
                pattern.id,
                {"quality_rating": 4.5, "application_count": 3},
            )

            self.assertEqual(result.status, "overwritten")
            document = read_pattern_document(
                kb / "patterns/chart-type/grouped-bar/pattern-001.md"
            )
            self.assertEqual(document.pattern.quality_rating, 4.5)
            self.assertEqual(document.pattern.application_count, 3)
            self.assertEqual(document.narrative, "# Keep this narrative\n")

    def test_update_pattern_rejects_id_updates_without_changing_source(self):
        with tempfile.TemporaryDirectory() as directory:
            kb = Path(directory)
            pattern = make_pattern(source_doi=None, source_figure=None)
            save_pattern(kb, pattern, "# Keep this narrative\n")
            source = kb / "patterns/chart-type/grouped-bar/pattern-001.md"
            before = source.read_bytes()

            with self.assertRaises(ValueError):
                update_pattern(kb, pattern.id, {"id": "pattern-002"})

            self.assertEqual(source.read_bytes(), before)

    def test_create_writes_pattern_and_index(self):
        with tempfile.TemporaryDirectory() as directory:
            kb = Path(directory)
            result = save_pattern(kb, make_pattern(), "# Notes\n")
            self.assertIsInstance(result, SaveResult)
            self.assertEqual(result.status, "created")
            self.assertEqual(result.affected_ids, ("pattern-001",))
            self.assertTrue((kb / "patterns/chart-type/grouped-bar/pattern-001.md").exists())
            index = json.loads((kb / "index.json").read_text())
            self.assertEqual([entry["id"] for entry in index], ["pattern-001"])

    def test_doi_figure_duplicate_error_and_skip_are_byte_stable(self):
        with tempfile.TemporaryDirectory() as directory:
            kb = Path(directory)
            first = make_pattern(id="pattern-001")
            save_pattern(kb, first, "old\n")
            before = {p: p.read_bytes() for p in kb.rglob("*") if p.is_file()}
            duplicate = make_pattern(id="pattern-002")
            with self.assertRaises(KBDuplicateError) as raised:
                save_pattern(kb, duplicate, "new\n")
            self.assertEqual(raised.exception.code, "KB_DUPLICATE")
            skipped = save_pattern(kb, duplicate, "new\n", duplicate_policy=DuplicatePolicy.SKIP)
            self.assertEqual(skipped.status, "skipped")
            self.assertEqual(skipped.affected_ids, ("pattern-001",))
            self.assertEqual(before, {p: p.read_bytes() for p in kb.rglob("*") if p.is_file()})

    def test_overwrite_replaces_same_id_only_and_create_copy_allows_new_id(self):
        with tempfile.TemporaryDirectory() as directory:
            kb = Path(directory)
            first = make_pattern(id="pattern-001")
            save_pattern(kb, first, "old\n")
            changed = make_pattern(id="pattern-001", chart_type="stacked-bar")
            overwritten = save_pattern(kb, changed, "changed\n", duplicate_policy=DuplicatePolicy.OVERWRITE)
            self.assertEqual(overwritten.status, "overwritten")
            self.assertIn("changed", (kb / "patterns/chart-type/stacked-bar/pattern-001.md").read_text())
            copied = save_pattern(kb, make_pattern(id="pattern-002"), "copy\n", duplicate_policy=DuplicatePolicy.CREATE_COPY)
            self.assertEqual(copied.status, "created")
            self.assertEqual(set(copied.affected_ids), {"pattern-002"})

    def test_live_lock_raises_and_stale_lock_is_removed(self):
        with tempfile.TemporaryDirectory() as directory:
            kb = Path(directory)
            lock = KBWriteLock(kb)
            lock.acquire()
            try:
                marker = json.loads(lock.lock_path.read_text(encoding="utf-8"))
                self.assertEqual(marker["pid"], os.getpid())
                self.assertIn("T", marker["timestamp"])
                with self.assertRaises(KBLockedError) as raised:
                    save_pattern(kb, make_pattern(), "blocked\n")
                self.assertEqual(raised.exception.code, "KB_LOCKED")
            finally:
                lock.release()
            stale = kb / ".kb.lock"
            stale.write_text('{"pid": 1, "timestamp": "2000-01-01T00:00:00+00:00"}\n', encoding="utf-8")
            result = save_pattern(kb, make_pattern(), "fresh\n")
            self.assertEqual(result.status, "created")

    def test_index_replace_failure_restores_pattern_and_index(self):
        with tempfile.TemporaryDirectory() as directory:
            kb = Path(directory)
            original = make_pattern(id="pattern-001")
            save_pattern(kb, original, "old\n")
            target = kb / "patterns/chart-type/grouped-bar/pattern-001.md"
            old_pattern = target.read_bytes()
            old_index = (kb / "index.json").read_bytes()
            real_replace = os.replace
            calls = []
            def fail_index(source, destination):
                calls.append(Path(destination))
                if Path(destination).name == "index.json":
                    raise OSError("index replace failed")
                return real_replace(source, destination)
            with patch("nature_figure_learner.repository.os.replace", side_effect=fail_index):
                with patch.object(Path, "write_bytes", side_effect=AssertionError("non-atomic restore")):
                    with self.assertRaises(OSError):
                        save_pattern(kb, make_pattern(id="pattern-001", chart_type="stacked-bar"), "new\n", duplicate_policy=DuplicatePolicy.OVERWRITE)
            self.assertEqual(target.read_bytes(), old_pattern)
            self.assertEqual((kb / "index.json").read_bytes(), old_index)

    def test_index_replace_failure_restores_snapshots_atomically(self):
        with tempfile.TemporaryDirectory() as directory:
            kb = Path(directory)
            save_pattern(kb, make_pattern(id="pattern-001"), "old\n")
            target = kb / "patterns/chart-type/grouped-bar/pattern-001.md"
            old_pattern = target.read_bytes()
            old_index = (kb / "index.json").read_bytes()
            real_replace = os.replace
            calls = []
            failed = False

            def fail_once(source, destination):
                nonlocal failed
                source_path, destination_path = Path(source), Path(destination)
                calls.append((source_path, destination_path))
                if destination_path.name == "index.json" and not failed:
                    failed = True
                    raise OSError("index replace failed")
                return real_replace(source, destination)

            with patch("nature_figure_learner.repository.os.replace", side_effect=fail_once):
                with self.assertRaises(OSError):
                    save_pattern(
                        kb,
                        make_pattern(id="pattern-001", source_journal="Nature Methods"),
                        "new\n",
                        duplicate_policy=DuplicatePolicy.OVERWRITE,
                    )
            self.assertEqual(target.read_bytes(), old_pattern)
            self.assertEqual((kb / "index.json").read_bytes(), old_index)
            self.assertGreaterEqual(sum(destination == target for _, destination in calls), 2)
            self.assertGreaterEqual(sum(destination.name == "index.json" for _, destination in calls), 2)

    def test_lock_write_failure_removes_own_marker(self):
        with tempfile.TemporaryDirectory() as directory:
            lock = KBWriteLock(Path(directory))
            with patch("nature_figure_learner.repository.os.write", side_effect=OSError("write failed")):
                with self.assertRaises(OSError):
                    lock.acquire()
            self.assertFalse(lock.lock_path.exists())

    def test_lock_zero_write_is_failure_and_removes_marker(self):
        with tempfile.TemporaryDirectory() as directory:
            lock = KBWriteLock(Path(directory))
            with patch("nature_figure_learner.repository.os.write", return_value=0):
                with self.assertRaises(OSError):
                    lock.acquire()
            self.assertFalse(lock.lock_path.exists())
            self.assertFalse(lock._owned)

    def test_lock_short_write_retries_until_marker_is_complete(self):
        with tempfile.TemporaryDirectory() as directory:
            lock = KBWriteLock(Path(directory))
            real_write = os.write
            calls = 0

            def short_write(fd, data):
                nonlocal calls
                calls += 1
                if calls == 1:
                    return real_write(fd, data[:3])
                return real_write(fd, data)

            with patch("nature_figure_learner.repository.os.write", side_effect=short_write):
                lock.acquire()
            try:
                marker = json.loads(lock.lock_path.read_text(encoding="utf-8"))
                self.assertEqual(marker["pid"], os.getpid())
                self.assertGreater(calls, 1)
            finally:
                lock.release()

    def test_lock_close_failure_removes_marker_without_claiming_ownership(self):
        with tempfile.TemporaryDirectory() as directory:
            lock = KBWriteLock(Path(directory))
            real_close = os.close

            def failing_close(fd):
                real_close(fd)
                raise OSError("close failed")

            with patch("nature_figure_learner.repository.os.close", side_effect=failing_close):
                with self.assertRaises(OSError):
                    lock.acquire()
            self.assertFalse(lock.lock_path.exists())
            self.assertFalse(lock._owned)

    def test_snapshot_restore_failure_propagates_without_direct_write(self):
        with tempfile.TemporaryDirectory() as directory:
            kb = Path(directory)
            save_pattern(kb, make_pattern(), "old\n")
            target = kb / "patterns/chart-type/grouped-bar/pattern-001.md"
            old_pattern = target.read_bytes()
            old_index = (kb / "index.json").read_bytes()
            real_replace = os.replace
            index_failures = 0

            def fail_index(source, destination):
                nonlocal index_failures
                if Path(destination).name == "index.json":
                    index_failures += 1
                    raise OSError("index replace failed")
                return real_replace(source, destination)

            with patch("nature_figure_learner.repository.os.replace", side_effect=fail_index):
                with patch.object(Path, "write_bytes", side_effect=AssertionError("non-atomic restore")):
                    with self.assertRaises(OSError):
                        save_pattern(
                            kb,
                            make_pattern(source_journal="Nature Methods"),
                            "new\n",
                            duplicate_policy=DuplicatePolicy.OVERWRITE,
                        )
            self.assertEqual(target.read_bytes(), old_pattern)
            self.assertEqual((kb / "index.json").read_bytes(), old_index)
            self.assertEqual(index_failures, 2)

    def test_persistent_restore_replace_failure_does_not_use_direct_write(self):
        with tempfile.TemporaryDirectory() as directory:
            kb = Path(directory)
            save_pattern(kb, make_pattern(), "old\n")
            real_replace = os.replace
            with patch("nature_figure_learner.repository.os.replace", side_effect=OSError("persistent failure")):
                with patch.object(Path, "write_bytes", side_effect=AssertionError("non-atomic restore")):
                    with self.assertRaises(OSError):
                        save_pattern(kb, make_pattern(source_journal="Nature Methods"), "new\n", duplicate_policy=DuplicatePolicy.OVERWRITE)

    def test_stale_lock_is_not_removed_if_marker_changes_during_check(self):
        with tempfile.TemporaryDirectory() as directory:
            kb = Path(directory)
            lock_path = kb / ".kb.lock"
            stale = b'{"pid": 1, "timestamp": "2000-01-01T00:00:00+00:00"}\n'
            changed = b'{"pid": 2, "timestamp": "2000-01-01T00:00:00+00:00"}\n'
            lock_path.write_bytes(stale)
            lock = KBWriteLock(kb)
            real_read_bytes = Path.read_bytes
            reads = 0

            def changing_read(path):
                nonlocal reads
                if path == lock_path:
                    reads += 1
                    return stale if reads == 1 else changed
                return real_read_bytes(path)

            with patch.object(Path, "read_bytes", side_effect=changing_read):
                with self.assertRaises(KBLockedError):
                    lock.acquire()
            self.assertEqual(lock_path.read_bytes(), stale)

    def test_scan_rejects_filename_frontmatter_id_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            kb = Path(directory)
            path = kb / "patterns/chart-type/grouped-bar/pattern-001.md"
            path.parent.mkdir(parents=True)
            path.write_text(serialize_pattern_document(make_pattern(id="pattern-002", source_doi=None, source_figure=None), "text\n"), encoding="utf-8")
            with self.assertRaises(KBDuplicateError):
                save_pattern(kb, make_pattern(id="pattern-003"), "new\n")

    def test_scan_rejects_duplicate_frontmatter_ids_in_multiple_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            kb = Path(directory)
            first = write_pattern_fixture(kb, make_pattern(id="pattern-001", source_doi=None, source_figure=None))
            second = kb / "patterns/chart-type/stacked-bar/pattern-001.md"
            second.parent.mkdir(parents=True)
            second.write_text(first.read_text(encoding="utf-8"), encoding="utf-8")
            with self.assertRaises(KBDuplicateError):
                save_pattern(kb, make_pattern(id="pattern-002"), "new\n")

    def test_lock_write_failure_does_not_remove_replaced_marker(self):
        with tempfile.TemporaryDirectory() as directory:
            kb = Path(directory)
            lock = KBWriteLock(kb)
            real_unlink = Path.unlink
            original = b'{"pid": 123, "timestamp": "2020-01-01T00:00:00+00:00"}\n'
            replacement = b'{"pid": 456, "timestamp": "2020-01-01T00:00:00+00:00"}\n'
            original_unlink = real_unlink
            with patch("nature_figure_learner.repository.os.write", side_effect=OSError("write failed")):
                def replace_before_unlink(*args, **kwargs):
                    path = args[0] if args else lock.lock_path
                    if path == lock.lock_path:
                        path.write_bytes(replacement)
                        return None
                    return original_unlink(path)
                with patch.object(Path, "unlink", side_effect=replace_before_unlink):
                    with self.assertRaises(OSError):
                        lock.acquire()
            self.assertEqual(lock.lock_path.read_bytes(), replacement)

    def test_release_ignores_cleanup_io_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            kb = Path(directory)
            lock = KBWriteLock(kb)
            lock.acquire()
            with patch.object(Path, "read_bytes", side_effect=OSError("read failed")):
                lock.release()
            self.assertTrue(lock._owned is False)

    def test_failed_temporary_write_preserves_old_index_and_cleans_temporary_file(self):
        with tempfile.TemporaryDirectory() as directory:
            kb_path = Path(directory)
            write_pattern_fixture(kb_path, make_pattern())
            index_path = kb_path / "index.json"
            index_path.write_text('[{"id":"old"}]\n', encoding="utf-8")
            before = index_path.read_bytes()
            real_named_temporary_file = tempfile.NamedTemporaryFile

            class FailingWriteTemporaryFile:
                def __init__(self, *args, **kwargs):
                    self._temporary = real_named_temporary_file(*args, **kwargs)
                    self.name = self._temporary.name

                def __enter__(self):
                    self._temporary.__enter__()
                    return self

                def __exit__(self, *args):
                    return self._temporary.__exit__(*args)

                def write(self, _text):
                    raise OSError("write error")

                def flush(self):
                    return self._temporary.flush()

                def fileno(self):
                    return self._temporary.fileno()

            with patch(
                "nature_figure_learner.repository.tempfile.NamedTemporaryFile",
                FailingWriteTemporaryFile,
            ):
                with self.assertRaisesRegex(OSError, "write error"):
                    rebuild_index(kb_path)

            self.assertEqual(index_path.read_bytes(), before)
            self.assertEqual(list(kb_path.glob(".index.json.*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
