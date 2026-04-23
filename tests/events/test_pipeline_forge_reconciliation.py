"""Forge-contract reconciliation tests for pipeline payloads (TASK-NCFA-003).

Focused coverage of the four pipeline payloads reconciled / added to match
the Forge ``/system-design`` API contract
(``forge/docs/design/contracts/API-nats-pipeline-events.md`` §3.2):

  - ``StageCompletePayload``   — reconciled canonical field set
  - ``BuildPausedPayload``     — reconciled, excludes ``AUTO_APPROVE`` gate mode
  - ``BuildResumedPayload``    — reconciled canonical field set
  - ``BuildCancelledPayload``  — net-new payload

Covered per task §6:
  - field validation (required fields raise ValidationError when missing)
  - literal rejection (invalid literal values raise ValidationError)
  - serde round-trip (model_dump → model_validate returns an equal instance)
  - forward-compat (extra='allow' — unknown fields preserved on all four)

At least one test in this file imports from the public
``nats_core.events.pipeline`` module to exercise TASK-NCFA-003 AC-1
(``from nats_core.events.pipeline import ...`` works).
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import BaseModel, ValidationError

# One import via the public `pipeline` module to exercise AC-1 of TASK-NCFA-003.
from nats_core.events.pipeline import (
    BuildCancelledPayload,
    BuildPausedPayload,
    BuildResumedPayload,
    StageCompletePayload,
)

pytestmark = pytest.mark.unit

# ---------------------------------------------------------------------------
# Factory helpers (conftest-style factory functions, no mutable-state fixtures)
# ---------------------------------------------------------------------------

_NOW_ISO = "2026-04-23T12:00:00+00:00"


def _make_stage_complete_data(**overrides: Any) -> dict[str, Any]:
    """Return kwargs that construct a valid ``StageCompletePayload``."""
    defaults: dict[str, Any] = {
        "feature_id": "FEAT-NCFA003",
        "build_id": "build-FEAT-NCFA003-20260423120000",
        "stage_label": "system_design",
        "target_kind": "subagent",
        "target_identifier": "system-design-subagent",
        "status": "PASSED",
        "gate_mode": None,
        "coach_score": None,
        "duration_secs": 12.5,
        "completed_at": _NOW_ISO,
        "correlation_id": "corr-ncfa003-sc",
    }
    defaults.update(overrides)
    return defaults


def _make_stage_complete(**overrides: Any) -> StageCompletePayload:
    return StageCompletePayload(**_make_stage_complete_data(**overrides))


def _make_build_paused_data(**overrides: Any) -> dict[str, Any]:
    """Return kwargs that construct a valid ``BuildPausedPayload``."""
    defaults: dict[str, Any] = {
        "feature_id": "FEAT-NCFA003",
        "build_id": "build-FEAT-NCFA003-20260423120000",
        "stage_label": "autobuild",
        "gate_mode": "FLAG_FOR_REVIEW",
        "coach_score": 0.62,
        "rationale": "Coach score below threshold",
        "approval_subject": "agents.approval.forge.FEAT-NCFA003",
        "paused_at": _NOW_ISO,
        "correlation_id": "corr-ncfa003-bp",
    }
    defaults.update(overrides)
    return defaults


def _make_build_paused(**overrides: Any) -> BuildPausedPayload:
    return BuildPausedPayload(**_make_build_paused_data(**overrides))


def _make_build_resumed_data(**overrides: Any) -> dict[str, Any]:
    """Return kwargs that construct a valid ``BuildResumedPayload``."""
    defaults: dict[str, Any] = {
        "feature_id": "FEAT-NCFA003",
        "build_id": "build-FEAT-NCFA003-20260423120000",
        "stage_label": "autobuild",
        "decision": "approve",
        "responder": "rich",
        "resumed_at": _NOW_ISO,
        "correlation_id": "corr-ncfa003-br",
    }
    defaults.update(overrides)
    return defaults


def _make_build_resumed(**overrides: Any) -> BuildResumedPayload:
    return BuildResumedPayload(**_make_build_resumed_data(**overrides))


def _make_build_cancelled_data(**overrides: Any) -> dict[str, Any]:
    """Return kwargs that construct a valid ``BuildCancelledPayload``."""
    defaults: dict[str, Any] = {
        "feature_id": "FEAT-NCFA003",
        "build_id": "build-FEAT-NCFA003-20260423120000",
        "reason": "User cancelled via jarvis command",
        "cancelled_by": "rich",
        "cancelled_at": _NOW_ISO,
        "correlation_id": "corr-ncfa003-bc",
    }
    defaults.update(overrides)
    return defaults


def _make_build_cancelled(**overrides: Any) -> BuildCancelledPayload:
    return BuildCancelledPayload(**_make_build_cancelled_data(**overrides))


# ---------------------------------------------------------------------------
# StageCompletePayload
# ---------------------------------------------------------------------------


class TestStageCompletePayload:
    """Forge-reconciled StageCompletePayload tests (TASK-NCFA-003 §6)."""

    def test_stage_complete_payload_validates_required_fields(self) -> None:
        """Omitting a required field raises ValidationError."""
        data = _make_stage_complete_data()
        del data["feature_id"]
        with pytest.raises(ValidationError):
            StageCompletePayload(**data)

    def test_stage_complete_payload_rejects_invalid_status_literal(self) -> None:
        """status must be one of PASSED / FAILED / GATED / SKIPPED."""
        with pytest.raises(ValidationError):
            _make_stage_complete(status="passed")  # lowercase no longer valid
        with pytest.raises(ValidationError):
            _make_stage_complete(status="SUCCESS")
        with pytest.raises(ValidationError):
            _make_stage_complete(status="")

    def test_stage_complete_payload_rejects_invalid_target_kind(self) -> None:
        """target_kind must be one of local_tool / fleet_capability / subagent."""
        with pytest.raises(ValidationError):
            _make_stage_complete(target_kind="human")
        with pytest.raises(ValidationError):
            _make_stage_complete(target_kind="SUBAGENT")  # case-sensitive

    def test_stage_complete_payload_accepts_null_gate_mode_and_coach_score(
        self,
    ) -> None:
        """gate_mode and coach_score both accept None."""
        payload = _make_stage_complete(gate_mode=None, coach_score=None)
        assert payload.gate_mode is None
        assert payload.coach_score is None

        # Also accepts non-None values for both.
        populated = _make_stage_complete(
            gate_mode="AUTO_APPROVE", coach_score=0.91
        )
        assert populated.gate_mode == "AUTO_APPROVE"
        assert populated.coach_score == pytest.approx(0.91)

    def test_stage_complete_payload_serde_round_trip(self) -> None:
        """model_dump → model_validate returns an equal instance."""
        original = _make_stage_complete(
            status="GATED",
            target_kind="fleet_capability",
            gate_mode="FLAG_FOR_REVIEW",
            coach_score=0.72,
        )
        restored = StageCompletePayload.model_validate(original.model_dump())
        assert restored == original


# ---------------------------------------------------------------------------
# BuildPausedPayload
# ---------------------------------------------------------------------------


class TestBuildPausedPayload:
    """Forge-reconciled BuildPausedPayload tests (TASK-NCFA-003 §6)."""

    def test_build_paused_payload_validates_required_fields(self) -> None:
        """Omitting a required field raises ValidationError."""
        data = _make_build_paused_data()
        del data["approval_subject"]
        with pytest.raises(ValidationError):
            BuildPausedPayload(**data)

    def test_build_paused_payload_rejects_auto_approve_gate_mode(self) -> None:
        """The Paused literal excludes AUTO_APPROVE — a build only pauses when
        human action is required.
        """
        with pytest.raises(ValidationError):
            _make_build_paused(gate_mode="AUTO_APPROVE")

        # Sanity: the three valid literals all work.
        for mode in ("FLAG_FOR_REVIEW", "HARD_STOP", "MANDATORY_HUMAN_APPROVAL"):
            payload = _make_build_paused(gate_mode=mode)
            assert payload.gate_mode == mode

    def test_build_paused_payload_serde_round_trip(self) -> None:
        """model_dump → model_validate returns an equal instance."""
        original = _make_build_paused(
            gate_mode="HARD_STOP", coach_score=None, rationale="Hard-stop gate fired"
        )
        restored = BuildPausedPayload.model_validate(original.model_dump())
        assert restored == original


# ---------------------------------------------------------------------------
# BuildResumedPayload
# ---------------------------------------------------------------------------


class TestBuildResumedPayload:
    """Forge-reconciled BuildResumedPayload tests (TASK-NCFA-003 §6)."""

    def test_build_resumed_payload_validates_required_fields(self) -> None:
        """Omitting a required field raises ValidationError."""
        data = _make_build_resumed_data()
        del data["responder"]
        with pytest.raises(ValidationError):
            BuildResumedPayload(**data)

    def test_build_resumed_payload_rejects_invalid_decision_literal(self) -> None:
        """decision must be one of approve / reject / defer / override."""
        with pytest.raises(ValidationError):
            _make_build_resumed(decision="maybe")
        with pytest.raises(ValidationError):
            _make_build_resumed(decision="APPROVE")  # case-sensitive
        with pytest.raises(ValidationError):
            _make_build_resumed(decision="")

        # Sanity: all four valid values round-trip.
        for decision in ("approve", "reject", "defer", "override"):
            payload = _make_build_resumed(decision=decision)
            assert payload.decision == decision

    def test_build_resumed_payload_serde_round_trip(self) -> None:
        """model_dump → model_validate returns an equal instance."""
        original = _make_build_resumed(decision="override", responder="ops-bot")
        restored = BuildResumedPayload.model_validate(original.model_dump())
        assert restored == original


# ---------------------------------------------------------------------------
# BuildCancelledPayload (net-new)
# ---------------------------------------------------------------------------


class TestBuildCancelledPayload:
    """Net-new BuildCancelledPayload tests (TASK-NCFA-003 §6)."""

    def test_build_cancelled_payload_validates_required_fields(self) -> None:
        """Omitting a required field raises ValidationError."""
        data = _make_build_cancelled_data()
        del data["reason"]
        with pytest.raises(ValidationError):
            BuildCancelledPayload(**data)

    def test_build_cancelled_payload_serde_round_trip(self) -> None:
        """model_dump → model_validate returns an equal instance."""
        original = _make_build_cancelled(
            reason="Build superseded by new feature plan",
            cancelled_by="forge-orchestrator",
        )
        restored = BuildCancelledPayload.model_validate(original.model_dump())
        assert restored == original


# ---------------------------------------------------------------------------
# Forward-compatibility smoke across all four payloads
# ---------------------------------------------------------------------------


class TestForwardCompat:
    """Forward-compat smoke for TASK-NCFA-003 payloads (ConfigDict(extra='allow'))."""

    def test_all_four_payloads_accept_extra_fields(self) -> None:
        """ConfigDict(extra='allow') preserves unknown fields on each payload."""
        cases: list[tuple[type[BaseModel], dict[str, Any]]] = [
            (StageCompletePayload, _make_stage_complete_data()),
            (BuildPausedPayload, _make_build_paused_data()),
            (BuildResumedPayload, _make_build_resumed_data()),
            (BuildCancelledPayload, _make_build_cancelled_data()),
        ]
        for cls, data in cases:
            data_with_extra = {**data, "future_field": "forge-v3-sentinel"}
            instance = cls(**data_with_extra)
            # extra='allow' preserves the value on the instance.
            assert instance.future_field == "forge-v3-sentinel", (  # type: ignore[attr-defined]
                f"{cls.__name__} dropped an unknown field despite extra='allow'"
            )
