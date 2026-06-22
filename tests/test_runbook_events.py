"""Test suite for runbook lifecycle event types and payloads.

Covers the five runbook event types (RUNBOOK_STARTED, STEP_STARTED,
STEP_RESULT, RUNBOOK_COMPLETE, ESCALATED) and their corresponding
Pydantic payload models, validating:
- EventType enum membership
- Payload model field structure and validation
- Registry lookup via payload_class_for_event_type()
- Round-trip serialization through model_dump(mode="json")
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from nats_core.envelope import EventType, payload_class_for_event_type
from nats_core.events import (
    EscalatedPayload,
    RunbookCompletePayload,
    RunbookStartedPayload,
    StepResultPayload,
    StepStartedPayload,
)

# ---------------------------------------------------------------------------
# AC-001: EventType gains exactly the five members
# ---------------------------------------------------------------------------


def test_runbook_event_types_exist():
    """Verify that all five runbook EventType members exist with correct values."""
    assert EventType.RUNBOOK_STARTED.value == "runbook_started"
    assert EventType.STEP_STARTED.value == "step_started"
    assert EventType.STEP_RESULT.value == "step_result"
    assert EventType.RUNBOOK_COMPLETE.value == "runbook_complete"
    assert EventType.ESCALATED.value == "escalated"


# ---------------------------------------------------------------------------
# AC-002: Each payload is a Pydantic model with correct fields
# ---------------------------------------------------------------------------


def test_runbook_started_payload_structure():
    """Verify RunbookStartedPayload accepts required fields."""
    payload = RunbookStartedPayload(
        runbook_id="rbx-001",
        target="service-a",
        step_count=5,
        correlation_id="corr-123",
    )
    assert payload.runbook_id == "rbx-001"
    assert payload.target == "service-a"
    assert payload.step_count == 5
    assert payload.correlation_id == "corr-123"


def test_step_started_payload_structure():
    """Verify StepStartedPayload accepts required fields."""
    payload = StepStartedPayload(
        runbook_id="rbx-001",
        sequence_index=0,
        step_type="http_request",
        correlation_id="corr-123",
    )
    assert payload.runbook_id == "rbx-001"
    assert payload.sequence_index == 0
    assert payload.step_type == "http_request"
    assert payload.correlation_id == "corr-123"


def test_step_result_payload_structure():
    """Verify StepResultPayload accepts required fields."""
    payload = StepResultPayload(
        runbook_id="rbx-001",
        sequence_index=0,
        step_type="http_request",
        status="passed",
        result={"status_code": 200},
        correlation_id="corr-123",
    )
    assert payload.runbook_id == "rbx-001"
    assert payload.sequence_index == 0
    assert payload.step_type == "http_request"
    assert payload.status == "passed"
    assert payload.result == {"status_code": 200}
    assert payload.correlation_id == "corr-123"


def test_step_result_payload_with_null_result():
    """Verify StepResultPayload accepts None for result field."""
    payload = StepResultPayload(
        runbook_id="rbx-001",
        sequence_index=0,
        step_type="http_request",
        status="failed",
        result=None,
        correlation_id="corr-123",
    )
    assert payload.result is None


def test_runbook_complete_payload_structure():
    """Verify RunbookCompletePayload accepts required fields."""
    payload = RunbookCompletePayload(
        runbook_id="rbx-001",
        step_count=5,
        correlation_id="corr-123",
    )
    assert payload.runbook_id == "rbx-001"
    assert payload.step_count == 5
    assert payload.correlation_id == "corr-123"


def test_escalated_payload_structure():
    """Verify EscalatedPayload accepts required fields."""
    payload = EscalatedPayload(
        runbook_id="rbx-001",
        sequence_index=2,
        reason="step_failed",
        correlation_id="corr-123",
    )
    assert payload.runbook_id == "rbx-001"
    assert payload.sequence_index == 2
    assert payload.reason == "step_failed"
    assert payload.correlation_id == "corr-123"


# ---------------------------------------------------------------------------
# AC-002 (continued): Round-trip serialization
# ---------------------------------------------------------------------------


def test_runbook_started_payload_round_trip():
    """Verify RunbookStartedPayload round-trips through JSON without loss."""
    payload = RunbookStartedPayload(
        runbook_id="rbx-001",
        target="service-a",
        step_count=5,
        correlation_id="corr-123",
    )
    dumped = payload.model_dump(mode="json")
    rehydrated = RunbookStartedPayload(**dumped)
    assert rehydrated == payload


def test_step_result_payload_round_trip():
    """Verify StepResultPayload round-trips through JSON without loss."""
    payload = StepResultPayload(
        runbook_id="rbx-001",
        sequence_index=0,
        step_type="http_request",
        status="passed",
        result={"status_code": 200},
        correlation_id="corr-123",
    )
    dumped = payload.model_dump(mode="json")
    rehydrated = StepResultPayload(**dumped)
    assert rehydrated == payload


# ---------------------------------------------------------------------------
# AC-003: payload_class_for_event_type() resolves all five types
# ---------------------------------------------------------------------------


def test_payload_class_for_runbook_started():
    """Verify payload_class_for_event_type returns RunbookStartedPayload."""
    cls = payload_class_for_event_type(EventType.RUNBOOK_STARTED)
    assert cls is RunbookStartedPayload


def test_payload_class_for_step_started():
    """Verify payload_class_for_event_type returns StepStartedPayload."""
    cls = payload_class_for_event_type(EventType.STEP_STARTED)
    assert cls is StepStartedPayload


def test_payload_class_for_step_result():
    """Verify payload_class_for_event_type returns StepResultPayload."""
    cls = payload_class_for_event_type(EventType.STEP_RESULT)
    assert cls is StepResultPayload


def test_payload_class_for_runbook_complete():
    """Verify payload_class_for_event_type returns RunbookCompletePayload."""
    cls = payload_class_for_event_type(EventType.RUNBOOK_COMPLETE)
    assert cls is RunbookCompletePayload


def test_payload_class_for_escalated():
    """Verify payload_class_for_event_type returns EscalatedPayload."""
    cls = payload_class_for_event_type(EventType.ESCALATED)
    assert cls is EscalatedPayload


# ---------------------------------------------------------------------------
# AC-004: StepResultPayload.status accepts the five StepStatus values
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "status_value",
    ["pending", "running", "passed", "failed", "awaiting_approval"],
)
def test_step_result_payload_accepts_valid_status(status_value: str):
    """Verify StepResultPayload accepts all five StepStatus values."""
    payload = StepResultPayload(
        runbook_id="rbx-001",
        sequence_index=0,
        step_type="http_request",
        status=status_value,
        result=None,
        correlation_id="corr-123",
    )
    assert payload.status == status_value


def test_step_result_payload_rejects_invalid_status():
    """Verify StepResultPayload rejects out-of-set status values."""
    with pytest.raises(ValidationError) as exc_info:
        StepResultPayload(
            runbook_id="rbx-001",
            sequence_index=0,
            step_type="http_request",
            status="invalid_status",
            result=None,
            correlation_id="corr-123",
        )
    # Check that validation error mentions the status field
    errors = exc_info.value.errors()
    assert any(e["loc"][0] == "status" for e in errors)


# ---------------------------------------------------------------------------
# Additional validation: escalation reason closed set
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "reason",
    ["unknown_handler", "step_failed", "awaiting_approval"],
)
def test_escalated_payload_accepts_valid_reason(reason: str):
    """Verify EscalatedPayload accepts all three valid escalation reasons."""
    payload = EscalatedPayload(
        runbook_id="rbx-001",
        sequence_index=2,
        reason=reason,
        correlation_id="corr-123",
    )
    assert payload.reason == reason


def test_escalated_payload_rejects_invalid_reason():
    """Verify EscalatedPayload rejects invalid escalation reasons."""
    with pytest.raises(ValidationError) as exc_info:
        EscalatedPayload(
            runbook_id="rbx-001",
            sequence_index=2,
            reason="invalid_reason",
            correlation_id="corr-123",
        )
    # Check that validation error mentions the reason field
    errors = exc_info.value.errors()
    assert any(e["loc"][0] == "reason" for e in errors)
