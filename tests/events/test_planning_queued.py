"""Tests for PlanningQueuedPayload (Phase SPL — FEAT-SPL-001/002 prerequisite).

Validates the planning-stage sibling of BuildQueuedPayload:
  - stage literal pinned to "planning"
  - request_text / originating_user non-blank invariants (originating_user is
    REQUIRED here, unlike builds — DF-009 identity-pinned approval routing)
  - target_repo org/name format when present
  - originating_adapter provenance rules mirrored from BuildQueuedPayload
  - forward-compat extra fields, JSON round-trip fidelity
  - Topics.Pipeline.PLANNING_QUEUED resolution and EventType registry wiring
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from pydantic import ValidationError

from nats_core.envelope import EventType, payload_class_for_event_type
from nats_core.events import PlanningQueuedPayload
from nats_core.topics import Topics

pytestmark = pytest.mark.unit

# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------

_NOW = datetime(2026, 7, 5, 8, 15, 0, tzinfo=UTC)


def _make_planning_queued(**overrides: Any) -> PlanningQueuedPayload:
    defaults: dict[str, Any] = {
        "request_text": "What if the tutor could quiz students on their own weak topics?",
        "triggered_by": "jarvis",
        "originating_adapter": "slack",
        "originating_user": "U0JAMES01",
        "correlation_id": "plan-2026-07-05T08-15-00-b3e1",
        "requested_at": _NOW,
        "queued_at": _NOW,
    }
    defaults.update(overrides)
    return PlanningQueuedPayload(**defaults)


# ---------------------------------------------------------------------------
# PlanningQueuedPayload
# ---------------------------------------------------------------------------


class TestPlanningQueuedPayload:
    """PlanningQueuedPayload validation including field validators."""

    def test_valid_slack_intake_payload(self) -> None:
        """The FEAT-SPL-001 shape: Slack free-text from a pinned member id."""
        payload = _make_planning_queued()
        assert payload.stage == "planning"
        assert payload.triggered_by == "jarvis"
        assert payload.originating_adapter == "slack"
        assert payload.originating_user == "U0JAMES01"
        assert payload.request_text.startswith("What if the tutor")

    def test_defaults(self) -> None:
        """Verify sensible defaults for optional fields."""
        payload = _make_planning_queued()
        assert payload.stage == "planning"
        assert payload.target_repo is None
        assert payload.parent_request_id is None
        assert payload.retry_count == 0

    def test_stage_literal_rejects_other_values(self) -> None:
        """stage is pinned to 'planning' — the build-queued value must fail."""
        with pytest.raises(ValidationError, match="stage"):
            _make_planning_queued(stage="build")

    def test_request_text_blank_rejected(self) -> None:
        """Whitespace-only request_text raises ValidationError."""
        with pytest.raises(ValidationError, match="request_text"):
            _make_planning_queued(request_text="   \n\t")

    def test_request_text_is_stripped(self) -> None:
        """Leading/trailing whitespace is normalised away."""
        payload = _make_planning_queued(request_text="  a self-service onboarding flow  ")
        assert payload.request_text == "a self-service onboarding flow"

    def test_originating_user_required(self) -> None:
        """Missing originating_user raises — identity pinning is not optional."""
        data = {
            "request_text": "idea",
            "triggered_by": "cli",
            "correlation_id": "plan-001",
            "requested_at": _NOW,
            "queued_at": _NOW,
        }
        with pytest.raises(ValidationError, match="originating_user"):
            PlanningQueuedPayload(**data)  # type: ignore[arg-type]

    def test_originating_user_blank_rejected(self) -> None:
        """Whitespace-only originating_user raises ValidationError."""
        with pytest.raises(ValidationError, match="originating_user"):
            _make_planning_queued(originating_user="  ")

    def test_correlation_id_required(self) -> None:
        """Missing correlation_id raises ValidationError."""
        data = {
            "request_text": "idea",
            "triggered_by": "cli",
            "originating_user": "rich",
            "requested_at": _NOW,
            "queued_at": _NOW,
        }
        with pytest.raises(ValidationError):
            PlanningQueuedPayload(**data)  # type: ignore[arg-type]

    def test_target_repo_validates_org_name_format(self) -> None:
        """Rejects bare repo name, accepts org/name, accepts None."""
        with pytest.raises(ValidationError, match="target_repo"):
            _make_planning_queued(target_repo="study-tutor")

        payload = _make_planning_queued(target_repo="guardkit/study-tutor")
        assert payload.target_repo == "guardkit/study-tutor"

        explicit_none = _make_planning_queued(target_repo=None)
        assert explicit_none.target_repo is None

    def test_adapter_required_for_jarvis(self) -> None:
        """triggered_by='jarvis' with originating_adapter=None raises."""
        with pytest.raises(ValidationError, match="originating_adapter"):
            _make_planning_queued(triggered_by="jarvis", originating_adapter=None)

    def test_cli_rejects_slack_adapter(self) -> None:
        """triggered_by='cli' allows only terminal/cli-wrapper/None adapters."""
        with pytest.raises(ValidationError, match="CLI trigger"):
            _make_planning_queued(triggered_by="cli", originating_adapter="slack")

    def test_cli_trigger_with_terminal_adapter(self) -> None:
        """A CLI-originated planning request (testing path) validates."""
        payload = _make_planning_queued(
            triggered_by="cli",
            originating_adapter="terminal",
            originating_user="rich",
        )
        assert payload.triggered_by == "cli"

    def test_forward_compat_extra_fields(self) -> None:
        """extra='allow': unknown fields are preserved, not discarded."""
        payload = _make_planning_queued(future_field="hello")
        assert payload.future_field == "hello"  # type: ignore[attr-defined]

    def test_json_round_trip(self) -> None:
        """JSON round-trip fidelity, datetimes included."""
        payload = _make_planning_queued(
            target_repo="guardkit/study-tutor",
            parent_request_id="1751699700.000200",
        )
        dumped = payload.model_dump(mode="json")
        restored = PlanningQueuedPayload.model_validate(dumped)
        assert restored.request_text == payload.request_text
        assert restored.originating_user == payload.originating_user
        assert restored.correlation_id == payload.correlation_id
        assert restored.target_repo == payload.target_repo
        assert restored.parent_request_id == payload.parent_request_id
        assert restored.requested_at == payload.requested_at
        assert restored.queued_at == payload.queued_at


# ---------------------------------------------------------------------------
# Contract-layer wiring (topic + event type registry)
# ---------------------------------------------------------------------------


class TestPlanningQueuedWiring:
    """Topic template and EventType registry entries for planning-queued."""

    def test_topic_resolves_by_correlation_id(self) -> None:
        """The planning run has no feature identity yet — keyed by correlation_id."""
        subject = Topics.resolve(
            Topics.Pipeline.PLANNING_QUEUED,
            correlation_id="plan-2026-07-05T08-15-00-b3e1",
        )
        assert subject == "pipeline.planning-queued.plan-2026-07-05T08-15-00-b3e1"

    def test_topic_in_all_topics(self) -> None:
        assert Topics.Pipeline.PLANNING_QUEUED in Topics.ALL_TOPICS

    def test_event_type_registered(self) -> None:
        """EventType.PLANNING_QUEUED maps to PlanningQueuedPayload."""
        assert EventType.PLANNING_QUEUED.value == "planning_queued"
        assert payload_class_for_event_type(EventType.PLANNING_QUEUED) is PlanningQueuedPayload
