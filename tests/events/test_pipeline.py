"""Tests for v2.2 pipeline event payloads (TASK-NCFA-001).

Validates the five new payload classes added for forge v2.2 alignment:
  - BuildQueuedPayload (with field validators)
  - BuildPausedPayload
  - BuildResumedPayload
  - StageCompletePayload
  - StageGatedPayload

Also verifies the FeaturePlannedPayload deprecation warning.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest
from pydantic import ValidationError

from nats_core.events import (
    BuildPausedPayload,
    BuildQueuedPayload,
    BuildResumedPayload,
    FeaturePlannedPayload,
    StageCompletePayload,
    StageGatedPayload,
    WaveSummary,
)

# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------

_NOW = datetime(2026, 4, 15, 16, 30, 12, tzinfo=timezone.utc)


def _make_build_queued(**overrides: Any) -> BuildQueuedPayload:
    defaults: dict[str, Any] = {
        "feature_id": "FEAT-LPA042",
        "repo": "guardkit/lpa-platform",
        "branch": "main",
        "feature_yaml_path": "specs/FEAT-LPA042.yaml",
        "triggered_by": "cli",
        "originating_adapter": "terminal",
        "correlation_id": "bld-2026-04-15T16-30-12-a7f2",
        "requested_at": _NOW,
        "queued_at": _NOW,
    }
    defaults.update(overrides)
    return BuildQueuedPayload(**defaults)


def _make_build_paused(**overrides: Any) -> BuildPausedPayload:
    defaults: dict[str, Any] = {
        "feature_id": "FEAT-001",
        "build_id": "build-FEAT-001-20260415163012",
        "stage": "autobuild",
        "coach_score": 0.65,
        "threshold": 0.75,
        "gate_mode": "flag_for_review",
        "details": "Coach score below threshold",
        "correlation_id": "bld-001",
        "paused_at": _NOW,
    }
    defaults.update(overrides)
    return BuildPausedPayload(**defaults)


def _make_build_resumed(**overrides: Any) -> BuildResumedPayload:
    defaults: dict[str, Any] = {
        "feature_id": "FEAT-001",
        "build_id": "build-FEAT-001-20260415163012",
        "stage": "autobuild",
        "resumed_by": "rich",
        "decision": "approve",
        "correlation_id": "bld-001",
        "resumed_at": _NOW,
    }
    defaults.update(overrides)
    return BuildResumedPayload(**defaults)


def _make_stage_complete(**overrides: Any) -> StageCompletePayload:
    defaults: dict[str, Any] = {
        "feature_id": "FEAT-001",
        "build_id": "build-FEAT-001-20260415163012",
        "stage": "autobuild",
        "status": "passed",
        "duration_secs": 42.5,
        "correlation_id": "bld-001",
        "completed_at": _NOW,
    }
    defaults.update(overrides)
    return StageCompletePayload(**defaults)


def _make_stage_gated(**overrides: Any) -> StageGatedPayload:
    defaults: dict[str, Any] = {
        "feature_id": "FEAT-001",
        "build_id": "build-FEAT-001-20260415163012",
        "stage": "autobuild",
        "gate_mode": "hard_stop",
        "coach_score": 0.55,
        "threshold": 0.75,
        "details": "Hard stop: score below threshold",
        "correlation_id": "bld-001",
        "gated_at": _NOW,
    }
    defaults.update(overrides)
    return StageGatedPayload(**defaults)


# ---------------------------------------------------------------------------
# BuildQueuedPayload
# ---------------------------------------------------------------------------


class TestBuildQueuedPayload:
    """BuildQueuedPayload validation including field validators."""

    def test_build_queued_payload_validates_feature_id_format(self) -> None:
        """Rejects invalid feature_id, accepts FEAT-XXX."""
        with pytest.raises(ValidationError, match="feature_id"):
            _make_build_queued(feature_id="BAD-ID")

        payload = _make_build_queued(feature_id="FEAT-LPA042")
        assert payload.feature_id == "FEAT-LPA042"

    def test_build_queued_payload_validates_repo_format(self) -> None:
        """Rejects bare repo name, accepts org/name."""
        with pytest.raises(ValidationError, match="repo"):
            _make_build_queued(repo="lpa-platform")

        payload = _make_build_queued(repo="guardkit/lpa-platform")
        assert payload.repo == "guardkit/lpa-platform"

    def test_build_queued_payload_adapter_required_for_jarvis(self) -> None:
        """triggered_by='jarvis' with originating_adapter=None raises."""
        with pytest.raises(ValidationError, match="originating_adapter"):
            _make_build_queued(
                triggered_by="jarvis",
                originating_adapter=None,
            )

    def test_build_queued_payload_cli_rejects_voice_adapter(self) -> None:
        """triggered_by='cli' with originating_adapter='voice-reachy' raises."""
        with pytest.raises(ValidationError, match="CLI trigger"):
            _make_build_queued(
                triggered_by="cli",
                originating_adapter="voice-reachy",
            )

    def test_build_queued_payload_correlation_id_required(self) -> None:
        """Missing correlation_id raises ValidationError."""
        data = {
            "feature_id": "FEAT-LPA042",
            "repo": "guardkit/lpa-platform",
            "feature_yaml_path": "specs/FEAT-LPA042.yaml",
            "triggered_by": "cli",
            "requested_at": _NOW,
            "queued_at": _NOW,
        }
        with pytest.raises(ValidationError):
            BuildQueuedPayload(**data)  # type: ignore[arg-type]

    def test_build_queued_payload_forward_compat_extra_fields(self) -> None:
        """extra='allow': unknown fields are preserved, not discarded."""
        payload = _make_build_queued(future_field="hello")
        assert payload.future_field == "hello"  # type: ignore[attr-defined]

    def test_build_queued_payload_defaults(self) -> None:
        """Verify sensible defaults for optional fields."""
        payload = _make_build_queued()
        assert payload.branch == "main"
        assert payload.max_turns == 5  # noqa: PLR2004
        assert payload.sdk_timeout_seconds == 1800  # noqa: PLR2004
        assert payload.wave_gating is False
        assert payload.config_overrides is None
        assert payload.originating_user is None
        assert payload.parent_request_id is None
        assert payload.retry_count == 0

    def test_build_queued_payload_jarvis_voice_trigger(self) -> None:
        """Full Jarvis voice trigger payload round-trips correctly."""
        payload = _make_build_queued(
            triggered_by="jarvis",
            originating_adapter="voice-reachy",
            originating_user="rich",
            parent_request_id="jarvis-dispatch-001",
            max_turns=10,
        )
        assert payload.triggered_by == "jarvis"
        assert payload.originating_adapter == "voice-reachy"
        assert payload.parent_request_id == "jarvis-dispatch-001"
        assert payload.max_turns == 10  # noqa: PLR2004

    def test_build_queued_payload_json_round_trip(self) -> None:
        """JSON round-trip fidelity."""
        payload = _make_build_queued()
        dumped = payload.model_dump(mode="json")
        restored = BuildQueuedPayload.model_validate(dumped)
        assert restored.feature_id == payload.feature_id
        assert restored.correlation_id == payload.correlation_id
        assert restored.triggered_by == payload.triggered_by


# ---------------------------------------------------------------------------
# BuildPausedPayload
# ---------------------------------------------------------------------------


class TestBuildPausedPayload:
    """BuildPausedPayload validation."""

    def test_build_paused_payload_requires_gate_mode(self) -> None:
        """gate_mode must be 'flag_for_review' or 'hard_stop'."""
        with pytest.raises(ValidationError):
            _make_build_paused(gate_mode="invalid")

        for mode in ("flag_for_review", "hard_stop"):
            payload = _make_build_paused(gate_mode=mode)
            assert payload.gate_mode == mode

    def test_build_paused_payload_forward_compat(self) -> None:
        """extra='allow': unknown fields preserved."""
        payload = _make_build_paused(new_field="value")
        assert payload.new_field == "value"  # type: ignore[attr-defined]

    def test_build_paused_payload_json_round_trip(self) -> None:
        """JSON round-trip fidelity."""
        payload = _make_build_paused()
        dumped = payload.model_dump(mode="json")
        restored = BuildPausedPayload.model_validate(dumped)
        assert restored.stage == payload.stage
        assert restored.gate_mode == payload.gate_mode


# ---------------------------------------------------------------------------
# BuildResumedPayload
# ---------------------------------------------------------------------------


class TestBuildResumedPayload:
    """BuildResumedPayload validation."""

    def test_build_resumed_payload_requires_decision(self) -> None:
        """decision must be 'approve' or 'reject'."""
        with pytest.raises(ValidationError):
            _make_build_resumed(decision="maybe")

        for decision in ("approve", "reject"):
            payload = _make_build_resumed(decision=decision)
            assert payload.decision == decision

    def test_build_resumed_payload_forward_compat(self) -> None:
        """extra='allow': unknown fields preserved."""
        payload = _make_build_resumed(reason="looks good")
        assert payload.reason == "looks good"  # type: ignore[attr-defined]

    def test_build_resumed_payload_json_round_trip(self) -> None:
        """JSON round-trip fidelity."""
        payload = _make_build_resumed()
        dumped = payload.model_dump(mode="json")
        restored = BuildResumedPayload.model_validate(dumped)
        assert restored.decision == payload.decision
        assert restored.resumed_by == payload.resumed_by


# ---------------------------------------------------------------------------
# StageCompletePayload
# ---------------------------------------------------------------------------


class TestStageCompletePayload:
    """StageCompletePayload validation."""

    def test_stage_complete_payload_status_literal(self) -> None:
        """status must be one of: passed, failed, gated, skipped."""
        for status in ("passed", "failed", "gated", "skipped"):
            payload = _make_stage_complete(status=status)
            assert payload.status == status

        with pytest.raises(ValidationError):
            _make_stage_complete(status="unknown")

    def test_stage_complete_payload_coach_score_optional(self) -> None:
        """coach_score defaults to None."""
        payload = _make_stage_complete()
        assert payload.coach_score is None

        payload_with_score = _make_stage_complete(coach_score=0.85)
        assert payload_with_score.coach_score == pytest.approx(0.85)

    def test_stage_complete_payload_forward_compat(self) -> None:
        """extra='allow': unknown fields preserved."""
        payload = _make_stage_complete(extra_metric=42)
        assert payload.extra_metric == 42  # type: ignore[attr-defined]

    def test_stage_complete_payload_json_round_trip(self) -> None:
        """JSON round-trip fidelity."""
        payload = _make_stage_complete(coach_score=0.9)
        dumped = payload.model_dump(mode="json")
        restored = StageCompletePayload.model_validate(dumped)
        assert restored.status == payload.status
        assert restored.coach_score == pytest.approx(0.9)


# ---------------------------------------------------------------------------
# StageGatedPayload
# ---------------------------------------------------------------------------


class TestStageGatedPayload:
    """StageGatedPayload validation."""

    def test_stage_gated_payload_requires_coach_score_and_threshold(self) -> None:
        """coach_score and threshold are required fields."""
        payload = _make_stage_gated(coach_score=0.55, threshold=0.75)
        assert payload.coach_score == pytest.approx(0.55)
        assert payload.threshold == pytest.approx(0.75)

        # Missing coach_score
        data = _make_stage_gated().model_dump()
        del data["coach_score"]
        with pytest.raises(ValidationError):
            StageGatedPayload(**data)

        # Missing threshold
        data = _make_stage_gated().model_dump()
        del data["threshold"]
        with pytest.raises(ValidationError):
            StageGatedPayload(**data)

    def test_stage_gated_payload_gate_mode_literal(self) -> None:
        """gate_mode must be 'flag_for_review' or 'hard_stop'."""
        with pytest.raises(ValidationError):
            _make_stage_gated(gate_mode="auto_approve")

    def test_stage_gated_payload_forward_compat(self) -> None:
        """extra='allow': unknown fields preserved."""
        payload = _make_stage_gated(new_policy="v3")
        assert payload.new_policy == "v3"  # type: ignore[attr-defined]

    def test_stage_gated_payload_json_round_trip(self) -> None:
        """JSON round-trip fidelity."""
        payload = _make_stage_gated()
        dumped = payload.model_dump(mode="json")
        restored = StageGatedPayload.model_validate(dumped)
        assert restored.coach_score == pytest.approx(payload.coach_score)
        assert restored.gate_mode == payload.gate_mode


# ---------------------------------------------------------------------------
# FeaturePlannedPayload deprecation
# ---------------------------------------------------------------------------


class TestFeaturePlannedDeprecation:
    """Verify FeaturePlannedPayload emits DeprecationWarning on instantiation."""

    def test_feature_planned_payload_emits_deprecation_warning(self) -> None:
        """Instantiating FeaturePlannedPayload emits DeprecationWarning."""
        waves = [WaveSummary(wave_number=1, task_count=1, task_ids=["T1"])]
        with pytest.warns(DeprecationWarning, match="deprecated.*BuildQueuedPayload"):
            FeaturePlannedPayload(
                feature_id="FEAT-001",
                wave_count=1,
                task_count=1,
                waves=waves,
            )
