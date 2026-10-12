"""Tests for ReviewEvidence / ReviewOutcome (web-readiness W7).

The merge offer's preview and test evidence travels on ``BuildPausedPayload``
as an optional ``review_evidence`` field. Covers:
  - valid ``ready`` and ``failed`` records
  - git object id format, https-only URLs, state-dependent required fields
  - unknown outcome counts stay ``None`` (never 0)
  - old payloads without the field still validate; unknown fields are ignored
  - JSON round-trip through the payload
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from pydantic import ValidationError

from nats_core.events import BuildPausedPayload, ReviewEvidence, ReviewOutcome
from nats_core.events.pipeline import ReviewEvidence as PipelineReviewEvidence

pytestmark = pytest.mark.unit

_NOW = datetime(2026, 10, 12, 14, 0, 0, tzinfo=UTC)
_SHA = "a" * 40
_TREE = "b" * 40
_PREVIEW_TREE = "c" * 40
_BASE = "https://preview.example.test"


def _ready(**overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "state": "ready",
        "app_url": f"{_BASE}:8950/?preview=tok123",
        "report_url": f"{_BASE}/evidence/run-1/report/index.html",
        "media_urls": [f"{_BASE}/evidence/run-1/journey.webm"],
        "candidate_sha": _SHA,
        "candidate_tree": _TREE,
        "preview_tree": _PREVIEW_TREE,
        "run_id": "run-1",
        "created_at": _NOW.isoformat(),
        "app_expires_at": (_NOW + timedelta(hours=24)).isoformat(),
        "evidence_expires_at": (_NOW + timedelta(days=14)).isoformat(),
        "outcome": {"passed": 3, "failed": 0, "skipped": 1, "flaky": None},
    }
    data.update(overrides)
    return data


def _failed(**overrides: Any) -> dict[str, Any]:
    data = _ready(
        state="failed",
        app_url=None,
        report_url=None,
        media_urls=[],
        diagnostics_url=f"{_BASE}/evidence/run-1/trace.zip",
        failure_reason="the preview does not enforce its link",
        outcome={},
    )
    data.update(overrides)
    return data


def _paused(**overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "feature_id": "FEAT-ABC123",
        "build_id": "build-FEAT-ABC123-20261012140000",
        "stage_label": "merge",
        "gate_mode": "MANDATORY_HUMAN_APPROVAL",
        "coach_score": None,
        "rationale": "Ready to merge",
        "approval_subject": "agents.approval.forge.FEAT-ABC123",
        "paused_at": _NOW.isoformat(),
        "correlation_id": "corr-1",
    }
    data.update(overrides)
    return data


class TestReviewEvidence:
    def test_valid_ready(self) -> None:
        ev = ReviewEvidence.model_validate(_ready())
        assert ev.state == "ready"
        assert ev.outcome.passed == 3
        assert ev.outcome.flaky is None
        assert ev.app_expires_at.tzinfo is not None

    def test_valid_failed(self) -> None:
        ev = ReviewEvidence.model_validate(_failed())
        assert ev.state == "failed"
        assert ev.app_url is None
        assert ev.failure_reason == "the preview does not enforce its link"

    def test_unknown_counts_stay_none_not_zero(self) -> None:
        ev = ReviewEvidence.model_validate(_failed())
        assert ev.outcome == ReviewOutcome(passed=None, failed=None, skipped=None, flaky=None)

    def test_reexported_from_pipeline_module(self) -> None:
        assert PipelineReviewEvidence is ReviewEvidence

    @pytest.mark.parametrize("field", ["candidate_sha", "candidate_tree", "preview_tree"])
    @pytest.mark.parametrize("bad", ["abc123", "A" * 40, "g" * 40, "a" * 41, ""])
    def test_invalid_object_id_rejected(self, field: str, bad: str) -> None:
        with pytest.raises(ValidationError):
            ReviewEvidence.model_validate(_ready(**{field: bad}))

    @pytest.mark.parametrize("missing", ["app_url", "report_url"])
    def test_ready_without_app_or_report_url_rejected(self, missing: str) -> None:
        with pytest.raises(ValidationError, match="requires app_url and report_url"):
            ReviewEvidence.model_validate(_ready(**{missing: None}))

    @pytest.mark.parametrize("reason", [None, "", "   "])
    def test_failed_without_reason_rejected(self, reason: str | None) -> None:
        with pytest.raises(ValidationError, match="requires failure_reason"):
            ReviewEvidence.model_validate(_failed(failure_reason=reason))

    @pytest.mark.parametrize("field", ["app_url", "report_url", "diagnostics_url", "media_urls"])
    @pytest.mark.parametrize(
        "bad", ["http://preview.example.test/x", "ftp://preview.example.test/x", "https:///x"]
    )
    def test_non_https_url_rejected(self, field: str, bad: str) -> None:
        value: Any = [bad] if field == "media_urls" else bad
        with pytest.raises(ValidationError, match="https"):
            ReviewEvidence.model_validate(_ready(**{field: value}))

    def test_naive_datetime_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ReviewEvidence.model_validate(_ready(app_expires_at="2026-10-13T14:00:00"))

    def test_negative_count_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ReviewEvidence.model_validate(_ready(outcome={"passed": -1}))

    def test_extra_unknown_fields_ignored(self) -> None:
        ev = ReviewEvidence.model_validate(
            _ready(future_field="x", outcome={"passed": 1, "retried": 2})
        )
        assert not hasattr(ev, "future_field")
        assert "future_field" not in ev.model_dump()
        assert "retried" not in ev.outcome.model_dump()

    def test_frozen(self) -> None:
        ev = ReviewEvidence.model_validate(_ready())
        with pytest.raises(ValidationError):
            ev.state = "failed"  # type: ignore[misc]


class TestBuildPausedReviewEvidence:
    def test_old_payload_without_field_validates(self) -> None:
        payload = BuildPausedPayload.model_validate(_paused())
        assert payload.review_evidence is None

    def test_payload_carries_typed_evidence(self) -> None:
        payload = BuildPausedPayload.model_validate(_paused(review_evidence=_ready()))
        assert isinstance(payload.review_evidence, ReviewEvidence)
        assert payload.review_evidence.preview_tree == _PREVIEW_TREE

    def test_payload_rejects_invalid_evidence(self) -> None:
        with pytest.raises(ValidationError):
            BuildPausedPayload.model_validate(_paused(review_evidence=_ready(app_url=None)))

    @pytest.mark.parametrize("make", [_ready, _failed])
    def test_json_round_trip(self, make: Any) -> None:
        original = BuildPausedPayload.model_validate(_paused(review_evidence=make()))
        restored = BuildPausedPayload.model_validate_json(original.model_dump_json())
        assert restored == original
        assert restored.review_evidence is not None
        assert restored.review_evidence.app_expires_at == original.review_evidence.app_expires_at

    def test_evidence_json_dump_round_trips_as_offer_details(self) -> None:
        # Forge puts model_dump(mode="json") under the offer's details dict.
        ev = ReviewEvidence.model_validate(_ready())
        as_details = ev.model_dump(mode="json")
        assert ReviewEvidence.model_validate(as_details) == ev
