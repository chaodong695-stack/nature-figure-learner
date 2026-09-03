import json
import math
import unittest

from pydantic import BaseModel, JsonValue, ValidationError

from nature_figure_learner.models import (
    CLIEnvelope,
    CLIError,
    CLIWarning,
    EnvelopeStatus,
)


class Payload(BaseModel):
    count: int


class CLIEnvelopeTests(unittest.TestCase):
    def test_success_contains_data_and_no_error(self):
        envelope = CLIEnvelope[dict].success("query", {"matches": []})

        self.assertEqual(envelope.status, EnvelopeStatus.SUCCESS)
        self.assertEqual(envelope.schema_version, "1.0")
        self.assertEqual(envelope.data, {"matches": []})
        self.assertIsNone(envelope.error)

    def test_unsupported_contains_capability_data_without_error_status(self):
        envelope = CLIEnvelope[dict].unsupported(
            "self-validate", {"chart_type": "sankey"}
        )

        self.assertEqual(envelope.status, EnvelopeStatus.UNSUPPORTED)
        self.assertNotEqual(envelope.status, EnvelopeStatus.ERROR)
        self.assertEqual(envelope.data, {"chart_type": "sankey"})
        self.assertIsNone(envelope.error)

    def test_failure_contains_structured_error_and_no_data(self):
        envelope = CLIEnvelope[dict].failure(
            "pattern save",
            CLIError(
                type="duplicate_conflict",
                code="KB_DUPLICATE",
                message="duplicate",
            ),
        )

        self.assertEqual(envelope.status, EnvelopeStatus.ERROR)
        self.assertIsNone(envelope.data)
        self.assertIsNotNone(envelope.error)
        self.assertEqual(envelope.error.code, "KB_DUPLICATE")
        self.assertEqual(envelope.error.type, "duplicate_conflict")
        self.assertEqual(envelope.error.message, "duplicate")

    def test_success_and_unsupported_require_data(self):
        for status in (EnvelopeStatus.SUCCESS, EnvelopeStatus.UNSUPPORTED):
            with self.subTest(status=status), self.assertRaises(ValidationError):
                CLIEnvelope[dict](status=status, command="query", data=None)

    def test_success_and_unsupported_forbid_error(self):
        error = CLIError(type="internal", code="INTERNAL_ERROR", message="oops")
        for status in (EnvelopeStatus.SUCCESS, EnvelopeStatus.UNSUPPORTED):
            with self.subTest(status=status), self.assertRaises(ValidationError):
                CLIEnvelope[dict](
                    status=status,
                    command="query",
                    data={},
                    error=error,
                )

    def test_error_requires_error_payload(self):
        with self.assertRaises(ValidationError):
            CLIEnvelope[dict](status=EnvelopeStatus.ERROR, command="query", data=None)

    def test_error_forbids_non_null_data(self):
        error = CLIError(type="internal", code="INTERNAL_ERROR", message="oops")
        with self.assertRaises(ValidationError):
            CLIEnvelope[dict](
                status=EnvelopeStatus.ERROR,
                command="query",
                data={"partial": True},
                error=error,
            )

    def test_mutable_defaults_are_isolated(self):
        first_warning = CLIWarning(code="W1", message="first")
        second_warning = CLIWarning(code="W2", message="second")
        first_error = CLIError(type="internal", code="E1", message="first")
        second_error = CLIError(type="internal", code="E2", message="second")
        first_envelope = CLIEnvelope[dict].success("query", {})
        second_envelope = CLIEnvelope[dict].success("query", {})

        first_warning.details["only_first"] = True
        first_error.details["only_first"] = True
        first_envelope.warnings.append(first_warning)

        self.assertEqual(second_warning.details, {})
        self.assertEqual(second_error.details, {})
        self.assertEqual(second_envelope.warnings, [])

    def test_serialization_has_stable_keys_and_json_values(self):
        envelope = CLIEnvelope[dict].unsupported(
            "self-validate", {"chart_type": "sankey"}
        )
        envelope.warnings.append(
            CLIWarning(code="UNSUPPORTED_CHART", message="not implemented")
        )

        serialized = envelope.model_dump(mode="json")

        self.assertEqual(
            set(serialized),
            {"status", "command", "schema_version", "data", "warnings", "error"},
        )
        self.assertEqual(serialized["status"], "unsupported")
        self.assertEqual(serialized["command"], "self-validate")
        self.assertEqual(serialized["schema_version"], "1.0")
        self.assertEqual(serialized["data"], {"chart_type": "sankey"})
        self.assertEqual(serialized["warnings"][0]["code"], "UNSUPPORTED_CHART")
        self.assertIsNone(serialized["error"])
        json.dumps(serialized)

    def test_invalid_assignments_roll_back_the_complete_envelope(self):
        envelope = CLIEnvelope[dict[str, JsonValue]].success(
            "query",
            {"matches": []},
            warnings=[CLIWarning(code="W1", message="warning")],
        )
        original = envelope.model_dump(mode="json")
        error = CLIError(type="internal", code="INTERNAL_ERROR", message="oops")

        invalid_assignments = (
            ("status", EnvelopeStatus.ERROR),
            ("status", b"error"),
            ("data", None),
            ("error", error),
        )
        for field, value in invalid_assignments:
            with self.subTest(field=field, value=value), self.assertRaises(
                ValidationError
            ):
                setattr(envelope, field, value)
            self.assertEqual(envelope.model_dump(mode="json"), original)

        failed = CLIEnvelope[dict].failure("query", error)
        failed_original = failed.model_dump(mode="json")
        with self.assertRaises(ValidationError):
            failed.error = None
        self.assertEqual(failed.model_dump(mode="json"), failed_original)

    def test_strict_json_rejects_non_finite_values_and_arbitrary_objects(self):
        for value in (math.nan, math.inf, -math.inf):
            with self.subTest(location="error", value=value), self.assertRaises(
                ValidationError
            ):
                CLIError(
                    type="internal",
                    code="INTERNAL_ERROR",
                    message="bad details",
                    details={"nested": {"value": value}},
                )
            with self.subTest(location="warning", value=value), self.assertRaises(
                ValidationError
            ):
                CLIWarning(
                    code="NON_FINITE",
                    message="bad details",
                    details={"nested": {"value": value}},
                )
            with self.subTest(location="data", value=value), self.assertRaises(
                ValidationError
            ):
                CLIEnvelope[dict[str, JsonValue]].success(
                    "query", {"nested": {"value": value}}
                )

        with self.assertRaises(ValidationError):
            CLIEnvelope[dict].success("query", {"nested": {"value": object()}})

    def test_valid_data_has_consistent_strict_json_serialization(self):
        envelope = CLIEnvelope[dict[str, JsonValue]].success(
            "query",
            {"ok": True, "values": [1, 2], "nested": {"empty": None}},
        )

        dumped = envelope.model_dump(mode="json")
        dumped_json = json.dumps(dumped, allow_nan=False)
        model_json = envelope.model_dump_json()

        self.assertEqual(json.loads(dumped_json), json.loads(model_json))

    def test_command_is_strictly_normalized_and_blank_values_rejected(self):
        envelope = CLIEnvelope[dict[str, JsonValue]].success(" pattern\t save ", {})
        self.assertEqual(envelope.command, "pattern save")

        for command in (b"query", 123, None, " \t \n "):
            with self.subTest(command=command), self.assertRaises(ValidationError):
                CLIEnvelope[dict].success(command, {})

        original = envelope.command
        with self.assertRaises(ValidationError):
            envelope.command = " \t "
        self.assertEqual(envelope.command, original)

    def test_constructors_snapshot_mutable_inputs(self):
        warning = CLIWarning(
            code="W1", message="warning", details={"nested": {"keep": True}}
        )
        warnings = [warning]
        data = {"items": [{"id": 1}]}
        envelope = CLIEnvelope[dict[str, JsonValue]].success(
            "query", data, warnings=warnings
        )

        warning.details["nested"]["keep"] = False
        warnings.append(CLIWarning(code="W2", message="later"))
        data["items"].append({"id": 2})

        self.assertEqual(envelope.warnings[0].details, {"nested": {"keep": True}})
        self.assertEqual(len(envelope.warnings), 1)
        self.assertEqual(envelope.data, {"items": [{"id": 1}]})

        error = CLIError(
            type="internal",
            code="INTERNAL_ERROR",
            message="error",
            details={"nested": {"keep": True}},
        )
        failed = CLIEnvelope[dict].failure("query", error)
        error.details["nested"]["keep"] = False
        self.assertEqual(failed.error.details, {"nested": {"keep": True}})

    def test_typed_payload_is_retained_after_json_validation(self):
        envelope = CLIEnvelope[Payload].success("query", {"count": "2"})

        self.assertIsInstance(envelope.data, Payload)
        self.assertEqual(envelope.data.count, 2)
        dumped_json = json.dumps(
            envelope.model_dump(mode="json"), allow_nan=False
        )
        self.assertEqual(json.loads(dumped_json), json.loads(envelope.model_dump_json()))

    def test_self_referential_dict_payload_is_rejected_as_validation_error(self):
        payload = {}
        payload["self"] = payload

        with self.assertRaises(ValidationError):
            CLIEnvelope[dict].success("query", payload)


if __name__ == "__main__":
    unittest.main()
