"""Tests for the WS1 Session I nats-core contract additions (five items).

Covers, per the WS1 outer-loop build plan §9 + the backward-edge episode
schema contract 2026-07-07:

  1. Planning lifecycle events (PlanningStarted/Complete/Failed) + the
     spec-ready handoff event (SpecReadyForBuildPayload) carrying
     correlation_id AND the Mode-P-minted feat_id.
  2. The normative plan-{correlation_id} approval-topic convention.
  3. NotificationPayload round-trip fields (thread_ts / parent_request_id /
     target_user / blocks).
  4. The originating_adapter validate_default fix on BOTH queued payloads
     (omitted adapter + triggered_by='jarvis' now fails at the wire).
  5. Structured per-assumption dispositions on ApprovalResponsePayload, with
     the accepted|modified|rejected|deferred vocabulary + synonym map.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from pydantic import ValidationError

from nats_core.envelope import EventType, payload_class_for_event_type
from nats_core.events import (
    ApprovalResponsePayload,
    AssumptionDisposition,
    BuildQueuedPayload,
    NotificationPayload,
    PlanningCompletePayload,
    PlanningFailedPayload,
    PlanningQueuedPayload,
    PlanningStartedPayload,
    SpecReadyForBuildPayload,
)
from nats_core.topics import Topics

pytestmark = pytest.mark.unit

_NOW = datetime(2026, 7, 8, 9, 0, 0, tzinfo=UTC)
_CID = "plan-2026-07-08T09-00-00-abcd"


# ---------------------------------------------------------------------------
# Item 4 — originating_adapter validate_default fix (the GATE property)
# ---------------------------------------------------------------------------


class TestOriginatingAdapterOmittedFieldPath:
    """Omitting originating_adapter with triggered_by='jarvis' must FAIL."""

    def _build_kwargs(self) -> dict[str, Any]:
        return {
            "feature_id": "FEAT-ABC",
            "repo": "guardkit/lpa-platform",
            "feature_yaml_path": "features/x.yaml",
            "correlation_id": "c1",
            "requested_at": _NOW,
            "queued_at": _NOW,
        }

    def _planning_kwargs(self) -> dict[str, Any]:
        return {
            "request_text": "an idea",
            "originating_user": "U0JAMES01",
            "correlation_id": _CID,
            "requested_at": _NOW,
            "queued_at": _NOW,
        }

    def test_build_queued_jarvis_omitted_adapter_fails(self) -> None:
        with pytest.raises(ValidationError, match="originating_adapter"):
            BuildQueuedPayload(triggered_by="jarvis", **self._build_kwargs())

    def test_planning_queued_jarvis_omitted_adapter_fails(self) -> None:
        with pytest.raises(ValidationError, match="originating_adapter"):
            PlanningQueuedPayload(triggered_by="jarvis", **self._planning_kwargs())

    def test_build_queued_jarvis_with_adapter_still_valid(self) -> None:
        payload = BuildQueuedPayload(
            triggered_by="jarvis", originating_adapter="slack", **self._build_kwargs()
        )
        assert payload.originating_adapter == "slack"

    def test_planning_queued_jarvis_with_adapter_still_valid(self) -> None:
        payload = PlanningQueuedPayload(
            triggered_by="jarvis",
            originating_adapter="slack",
            **self._planning_kwargs(),
        )
        assert payload.originating_adapter == "slack"

    def test_build_queued_cli_omitted_adapter_ok(self) -> None:
        payload = BuildQueuedPayload(triggered_by="cli", **self._build_kwargs())
        assert payload.originating_adapter is None

    def test_planning_queued_cli_omitted_adapter_ok(self) -> None:
        payload = PlanningQueuedPayload(triggered_by="cli", **self._planning_kwargs())
        assert payload.originating_adapter is None


# ---------------------------------------------------------------------------
# Item 1 — planning lifecycle events
# ---------------------------------------------------------------------------


class TestPlanningStartedPayload:
    def test_minimal_valid(self) -> None:
        payload = PlanningStartedPayload(
            correlation_id=_CID, originator="U0JAMES01", started_at=_NOW
        )
        assert payload.mode == "mode_p"
        assert payload.target_repo is None

    def test_target_repo_validated(self) -> None:
        with pytest.raises(ValidationError, match="target_repo"):
            PlanningStartedPayload(
                correlation_id=_CID,
                originator="U0JAMES01",
                started_at=_NOW,
                target_repo="bare-name",
            )
        ok = PlanningStartedPayload(
            correlation_id=_CID,
            originator="U0JAMES01",
            started_at=_NOW,
            target_repo="guardkit/lpa-platform",
        )
        assert ok.target_repo == "guardkit/lpa-platform"

    def test_explicit_none_target_repo_accepted(self) -> None:
        payload = PlanningStartedPayload(
            correlation_id=_CID,
            originator="U0JAMES01",
            started_at=_NOW,
            target_repo=None,
        )
        assert payload.target_repo is None


class TestPlanningCompletePayload:
    def test_terminal_state_defaults_to_planned_handoff(self) -> None:
        payload = PlanningCompletePayload(
            correlation_id=_CID, originator="U0JAMES01", completed_at=_NOW
        )
        assert payload.terminal_state == "planned_handoff"
        assert payload.feat_id is None

    def test_feat_id_pattern_enforced(self) -> None:
        with pytest.raises(ValidationError, match="feat_id"):
            PlanningCompletePayload(
                correlation_id=_CID,
                originator="U0JAMES01",
                completed_at=_NOW,
                feat_id="not-a-feat-id",
            )
        ok = PlanningCompletePayload(
            correlation_id=_CID,
            originator="U0JAMES01",
            completed_at=_NOW,
            feat_id="FEAT-ABC123",
            assumption_count=8,
            approval_cycles_used=2,
            duration_seconds=1200,
        )
        assert ok.feat_id == "FEAT-ABC123"
        assert ok.approval_cycles_used == 2

    def test_explicit_none_feat_id_accepted(self) -> None:
        payload = PlanningCompletePayload(
            correlation_id=_CID,
            originator="U0JAMES01",
            completed_at=_NOW,
            feat_id=None,
        )
        assert payload.feat_id is None

    def test_negative_counts_rejected(self) -> None:
        with pytest.raises(ValidationError):
            PlanningCompletePayload(
                correlation_id=_CID,
                originator="U0JAMES01",
                completed_at=_NOW,
                assumption_count=-1,
            )


class TestPlanningFailedPayload:
    def test_failed_terminal(self) -> None:
        payload = PlanningFailedPayload(
            correlation_id=_CID,
            originator="U0JAMES01",
            terminal_state="failed",
            failure_reason="PO dispatch degraded",
            failed_at=_NOW,
        )
        assert payload.recoverable is False

    def test_timed_out_terminal(self) -> None:
        payload = PlanningFailedPayload(
            correlation_id=_CID,
            originator="U0JAMES01",
            terminal_state="timed_out",
            failure_reason="escalation ceiling reached",
            failed_at=_NOW,
            recoverable=True,
        )
        assert payload.terminal_state == "timed_out"
        assert payload.recoverable is True

    def test_invalid_terminal_rejected(self) -> None:
        with pytest.raises(ValidationError):
            PlanningFailedPayload(
                correlation_id=_CID,
                originator="U0JAMES01",
                terminal_state="planned_handoff",  # not a failure terminal
                failure_reason="x",
                failed_at=_NOW,
            )


class TestSpecReadyForBuildPayload:
    """The spec-ready handoff: correlation_id + Mode-P-minted feat_id + outputs."""

    def test_valid_handoff_links_correlation_and_feat_id(self) -> None:
        payload = SpecReadyForBuildPayload(
            correlation_id=_CID,
            feat_id="FEAT-ABC123",
            spec_path="feature_spec_inputs/abcd.md",
            roadmap_path="roadmaps/abcd-roadmap.md",
            originator="U0JAMES01",
            target_repo="guardkit/lpa-platform",
            source_commands=["/feature-spec"],
            created_at=_NOW,
        )
        assert payload.correlation_id == _CID
        assert payload.feat_id == "FEAT-ABC123"
        assert payload.mode == "mode_p"
        assert payload.roadmap_path == "roadmaps/abcd-roadmap.md"

    def test_feat_id_required(self) -> None:
        with pytest.raises(ValidationError):
            SpecReadyForBuildPayload(
                correlation_id=_CID,
                spec_path="feature_spec_inputs/abcd.md",
                created_at=_NOW,
            )

    def test_feat_id_pattern_enforced(self) -> None:
        with pytest.raises(ValidationError, match="feat_id"):
            SpecReadyForBuildPayload(
                correlation_id=_CID,
                feat_id="plan-abcd",
                spec_path="feature_spec_inputs/abcd.md",
                created_at=_NOW,
            )

    def test_target_repo_validated(self) -> None:
        with pytest.raises(ValidationError, match="target_repo"):
            SpecReadyForBuildPayload(
                correlation_id=_CID,
                feat_id="FEAT-ABC123",
                spec_path="s.md",
                created_at=_NOW,
                target_repo="bad",
            )

    def test_defaults_when_optional_omitted(self) -> None:
        payload = SpecReadyForBuildPayload(
            correlation_id=_CID,
            feat_id="FEAT-ABC123",
            spec_path="s.md",
            created_at=_NOW,
        )
        assert payload.roadmap_path is None
        assert payload.originator is None
        assert payload.source_commands == []

    def test_explicit_none_target_repo_accepted(self) -> None:
        payload = SpecReadyForBuildPayload(
            correlation_id=_CID,
            feat_id="FEAT-ABC123",
            spec_path="s.md",
            created_at=_NOW,
            target_repo=None,
        )
        assert payload.target_repo is None


class TestPlanningLifecycleWiring:
    """New EventTypes resolve to their payloads and topics."""

    @pytest.mark.parametrize(
        ("event_type", "payload_cls"),
        [
            (EventType.PLANNING_STARTED, PlanningStartedPayload),
            (EventType.PLANNING_COMPLETE, PlanningCompletePayload),
            (EventType.PLANNING_FAILED, PlanningFailedPayload),
            (EventType.SPEC_READY_FOR_BUILD, SpecReadyForBuildPayload),
        ],
    )
    def test_registry_wiring(self, event_type: EventType, payload_cls: type) -> None:
        assert payload_class_for_event_type(event_type) is payload_cls

    def test_topics_keyed_on_correlation_id(self) -> None:
        for template in (
            Topics.Pipeline.PLANNING_STARTED,
            Topics.Pipeline.PLANNING_COMPLETE,
            Topics.Pipeline.PLANNING_FAILED,
            Topics.Pipeline.SPEC_READY_FOR_BUILD,
        ):
            resolved = Topics.resolve(template, correlation_id="abc-123")
            assert resolved.endswith("abc-123")
            assert template in Topics.ALL_TOPICS


# ---------------------------------------------------------------------------
# Item 2 — plan-{cid} approval-topic convention (normative)
# ---------------------------------------------------------------------------


class TestPlanningApprovalTopicConvention:
    def test_plan_cid_request_subject_resolves(self) -> None:
        resolved = Topics.resolve(
            Topics.Agents.PLANNING_APPROVAL_REQUEST,
            agent_id="forge",
            correlation_id="abcd",
        )
        assert resolved == "agents.approval.forge.plan-abcd"

    def test_plan_cid_response_subject_resolves(self) -> None:
        resolved = Topics.resolve(
            Topics.Agents.PLANNING_APPROVAL_RESPONSE,
            agent_id="forge",
            correlation_id="abcd",
        )
        assert resolved == "agents.approval.forge.plan-abcd.response"

    def test_convention_documented_as_normative(self) -> None:
        # The normative convention lives in the Agents namespace docstring so
        # jarvis / WS2 consumers can pin against it.
        assert "NORMATIVE" in (Topics.Agents.__doc__ or "")
        assert "plan-{correlation_id}" in (Topics.Agents.__doc__ or "")

    def test_convention_topics_in_all_topics(self) -> None:
        assert Topics.Agents.PLANNING_APPROVAL_REQUEST in Topics.ALL_TOPICS
        assert Topics.Agents.PLANNING_APPROVAL_RESPONSE in Topics.ALL_TOPICS


# ---------------------------------------------------------------------------
# Item 3 — NotificationPayload round-trip fields
# ---------------------------------------------------------------------------


class TestNotificationRoundTripFields:
    def test_new_fields_default_none(self) -> None:
        payload = NotificationPayload(message="hi", adapter="slack")
        assert payload.thread_ts is None
        assert payload.parent_request_id is None
        assert payload.target_user is None
        assert payload.blocks is None

    def test_threaded_notification_round_trips(self) -> None:
        payload = NotificationPayload(
            message="Planning complete",
            adapter="slack",
            thread_ts="1700000000.000100",
            parent_request_id="1700000000.000100",
            target_user="U0RICH001",
            blocks=[{"type": "section", "text": {"type": "mrkdwn", "text": "hi"}}],
        )
        restored = NotificationPayload.model_validate_json(payload.model_dump_json())
        assert restored.thread_ts == "1700000000.000100"
        assert restored.parent_request_id == "1700000000.000100"
        assert restored.target_user == "U0RICH001"
        assert restored.blocks is not None
        assert restored.blocks[0]["type"] == "section"

    def test_producer_omitting_fields_still_validates(self) -> None:
        # ASSUM-001: a producer that pre-dates the fields omits them unchanged.
        restored = NotificationPayload.model_validate({"message": "legacy", "adapter": "slack"})
        assert restored.parent_request_id is None


# ---------------------------------------------------------------------------
# Item 5 — structured per-assumption dispositions
# ---------------------------------------------------------------------------


class TestAssumptionDisposition:
    def test_canonical_vocabulary(self) -> None:
        for value in ("accepted", "modified", "rejected", "deferred", "undecided"):
            d = AssumptionDisposition(assumption_id="A1", disposition=value)
            assert d.disposition == value

    @pytest.mark.parametrize(
        ("verb", "canonical"),
        [
            ("approve", "accepted"),
            ("edit", "modified"),
            ("reject", "rejected"),
            ("defer", "deferred"),
        ],
    )
    def test_synonym_map_normalises(self, verb: str, canonical: str) -> None:
        d = AssumptionDisposition(assumption_id="A1", disposition=verb)
        assert d.disposition == canonical

    def test_invalid_disposition_rejected(self) -> None:
        with pytest.raises(ValidationError):
            AssumptionDisposition(assumption_id="A1", disposition="maybe")

    def test_non_string_disposition_passes_through_to_literal_rejection(self) -> None:
        # The before-validator only normalises strings; a non-string falls
        # through untouched and is rejected by the Literal constraint.
        with pytest.raises(ValidationError):
            AssumptionDisposition(assumption_id="A1", disposition=5)  # type: ignore[arg-type]

    def test_edit_delta_and_notes_optional(self) -> None:
        d = AssumptionDisposition(
            assumption_id="A1",
            disposition="edit",
            edit_delta="- old\n+ new",
            notes="tightened the scope",
        )
        assert d.disposition == "modified"
        assert d.edit_delta == "- old\n+ new"


class TestApprovalResponseDispositions:
    def test_dispositions_default_none(self) -> None:
        payload = ApprovalResponsePayload(
            request_id="r1", decision="approve", decided_by="U0RICH001"
        )
        assert payload.dispositions is None

    def test_structured_dispositions_round_trip(self) -> None:
        payload = ApprovalResponsePayload(
            request_id="r1",
            decision="approve",
            decided_by="U0RICH001",
            dispositions=[
                {"assumption_id": "ASSUM-001", "disposition": "approve"},
                {
                    "assumption_id": "ASSUM-002",
                    "disposition": "edit",
                    "edit_delta": "- a\n+ b",
                },
                {"assumption_id": "ASSUM-003", "disposition": "defer"},
            ],
        )
        restored = ApprovalResponsePayload.model_validate_json(payload.model_dump_json())
        assert restored.dispositions is not None
        assert [d.disposition for d in restored.dispositions] == [
            "accepted",
            "modified",
            "deferred",
        ]

    def test_notes_bridge_still_available(self) -> None:
        # The JSON-in-notes ASSUM-003 bridge coexists with the structured field.
        payload = ApprovalResponsePayload(
            request_id="r1",
            decision="approve",
            decided_by="U0RICH001",
            notes='{"cycle": 1, "dispositions": []}',
        )
        assert payload.notes is not None
        assert payload.dispositions is None

    def test_dispositions_registered_payload_via_envelope_type(self) -> None:
        assert payload_class_for_event_type(EventType.APPROVAL_RESPONSE) is ApprovalResponsePayload
