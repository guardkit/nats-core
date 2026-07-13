"""Tests for the WS2 B7 deploy/QA/live-gate wire payloads.

Covers, per WS2 build-plan §B7 + its 2026-07-08 named-consumer note, the
backward-edge episode schema contract 2026-07-07 §4.3/§4.4/§7, and the fleet
dashboard wire-consumer-requirements asks A-1/A-3/A-4/A-6:

  * DeployQueued/Started/Complete/Failed lifecycle payloads (F7 vocabulary,
    keyed on correlation_id, timestamp on every one — A-1).
  * QAVerdictPayload / LiveGateResultPayload mirror the results envelope: the
    four-for-four verdict enum, per-assertion disposition, evidence refs (A-3).
  * The A-4 usage/loop_stats rollup block on StageComplete/BuildComplete AND the
    deploy/verdict payloads.
  * The deploy-domain Topics namespace + registry wiring + envelope round-trip.
  * The deploy-runner/live-gate-driver/qa-verifier capability taxonomy.
  * A-6: Topics.for_project() tenant prefixing.

validate_default note: the Session-I originating_adapter fix (e60d41d) is
already on the queued payloads; the deploy payloads carry no adapter/trigger
field, so there is no validate_default surface here to guard (reviewed, N/A).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from nats_core.envelope import EventType, MessageEnvelope, payload_class_for_event_type
from nats_core.events import (
    FLEET_CAPABILITY_KINDS,
    AssertionResult,
    BuildCompletePayload,
    DeployCompletePayload,
    DeployFailedPayload,
    DeployQueuedPayload,
    DeployRevertedPayload,
    DeployStartedPayload,
    LiveGateResultPayload,
    LoopStats,
    QAVerdictPayload,
    StageCompletePayload,
    UsageRollup,
)
from nats_core.topics import Topics

pytestmark = pytest.mark.unit

_NOW = datetime(2026, 7, 8, 12, 0, 0, tzinfo=UTC)
_CID = "build-FEAT-DEP001-20260708120000"


def _assertion(**overrides: object) -> AssertionResult:
    defaults: dict[str, object] = {
        "id": "a1",
        "gate_id": "gate_phase1_login",
        "status": "pass",
    }
    defaults.update(overrides)
    return AssertionResult(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Deploy lifecycle payloads
# ---------------------------------------------------------------------------


class TestDeployQueued:
    def test_minimal_valid(self) -> None:
        p = DeployQueuedPayload(
            correlation_id=_CID, env_id="lpa-poc-dev", deploy_run_id="run-1", queued_at=_NOW
        )
        assert p.feat_id is None
        assert p.hosts is None

    def test_feat_id_and_task_id_validated(self) -> None:
        with pytest.raises(ValidationError, match="feat_id"):
            DeployQueuedPayload(
                correlation_id=_CID,
                env_id="e",
                deploy_run_id="r",
                queued_at=_NOW,
                feat_id="nope",
            )
        with pytest.raises(ValidationError, match="task_id"):
            DeployQueuedPayload(
                correlation_id=_CID,
                env_id="e",
                deploy_run_id="r",
                queued_at=_NOW,
                task_id="nope",
            )
        ok = DeployQueuedPayload(
            correlation_id=_CID,
            env_id="e",
            deploy_run_id="r",
            queued_at=_NOW,
            feat_id="FEAT-DEP001",
            task_id="TASK-FIX01",
            target_repo="guardkit/lpa-platform",
        )
        assert ok.feat_id == "FEAT-DEP001"


class TestDeployComplete:
    def test_mirrors_f7_vocabulary(self) -> None:
        """backward-edge §7 item 8: env_id, artifact_digest, image_digests,
        deploy_record_ref, correlation_id — verbatim names."""
        p = DeployCompletePayload(
            correlation_id=_CID,
            env_id="study-tutor-gb10",
            deploy_run_id="run-9",
            artifact_digest="sha256:abc",
            image_digests={"backend": "sha256:def", "db": "sha256:ghi"},
            deploy_record_ref="docs/poc/evidence/deploy-record-9.md",
            hosts=["nas", "gb10", "mac"],
            reservation_resource="gb10-gpu",
            duration_seconds=42,
            completed_at=_NOW,
        )
        assert p.status == "complete"
        assert p.image_digests == {"backend": "sha256:def", "db": "sha256:ghi"}

    def test_deploy_record_ref_required(self) -> None:
        with pytest.raises(ValidationError, match="deploy_record_ref"):
            DeployCompletePayload(
                correlation_id=_CID, env_id="e", deploy_run_id="r", completed_at=_NOW
            )


class TestDeployFailed:
    def test_failed_step_required(self) -> None:
        """backward-edge §7 item 8: the failing step type on Failed."""
        with pytest.raises(ValidationError, match="failed_step"):
            DeployFailedPayload(
                correlation_id=_CID,
                env_id="e",
                deploy_run_id="r",
                failure_reason="boom",
                failed_at=_NOW,
            )

    def test_valid_with_failed_step(self) -> None:
        p = DeployFailedPayload(
            correlation_id=_CID,
            env_id="e",
            deploy_run_id="r",
            failed_step="health_check",
            failure_reason="backend never healthy",
            failed_at=_NOW,
        )
        assert p.status == "failed"
        assert p.recoverable is False
        assert p.deploy_record_ref is None


class TestDeployStarted:
    def test_minimal_valid(self) -> None:
        p = DeployStartedPayload(
            correlation_id=_CID, env_id="e", deploy_run_id="r", started_at=_NOW
        )
        assert p.runbook_ref is None


class TestDeployPayloadsCarryTimestampAndCorrelation:
    """Dashboard ask A-1: every deploy payload carries its own event timestamp
    and correlation_id."""

    def test_a1_timestamp_and_correlation(self) -> None:
        cases = [
            DeployQueuedPayload(
                correlation_id=_CID, env_id="e", deploy_run_id="r", queued_at=_NOW
            ),
            DeployStartedPayload(
                correlation_id=_CID, env_id="e", deploy_run_id="r", started_at=_NOW
            ),
            DeployCompletePayload(
                correlation_id=_CID,
                env_id="e",
                deploy_run_id="r",
                deploy_record_ref="ref",
                completed_at=_NOW,
            ),
            DeployFailedPayload(
                correlation_id=_CID,
                env_id="e",
                deploy_run_id="r",
                failed_step="s",
                failure_reason="x",
                failed_at=_NOW,
            ),
        ]
        for p in cases:
            data = p.model_dump()
            assert data["correlation_id"] == _CID
            ts_keys = {"queued_at", "started_at", "completed_at", "failed_at"} & set(data)
            assert ts_keys, f"{type(p).__name__} has no timestamp field"


# ---------------------------------------------------------------------------
# Verdict payloads — A-3 (verdict mirror + evidence refs)
# ---------------------------------------------------------------------------


class TestVerdictEnumFourForFour:
    @pytest.mark.parametrize(
        "verdict", ["pass", "fail", "instrument_fail", "environment_fail"]
    )
    def test_all_four_accepted(self, verdict: str) -> None:
        p = QAVerdictPayload(
            correlation_id=_CID,
            run_id="run-1",
            env_id="e",
            verdict=verdict,  # type: ignore[arg-type]
            gate_ids=["g1"],
            evidence_index_ref="qa/gates/history/run-1/index.json",
            attempt=1,
            decided_at=_NOW,
        )
        assert p.verdict == verdict

    def test_unknown_verdict_rejected(self) -> None:
        with pytest.raises(ValidationError):
            QAVerdictPayload(
                correlation_id=_CID,
                run_id="run-1",
                env_id="e",
                verdict="green",  # type: ignore[arg-type]
                gate_ids=["g1"],
                evidence_index_ref="ref",
                attempt=1,
                decided_at=_NOW,
            )

    def test_attempt_must_be_ge_1(self) -> None:
        with pytest.raises(ValidationError):
            QAVerdictPayload(
                correlation_id=_CID,
                run_id="run-1",
                env_id="e",
                verdict="pass",
                gate_ids=["g1"],
                evidence_index_ref="ref",
                attempt=0,
                decided_at=_NOW,
            )


class TestAssertionResult:
    def test_disposition_none_on_pass(self) -> None:
        a = _assertion(status="pass")
        assert a.disposition is None

    @pytest.mark.parametrize("disp", ["counts", "instrument", "environment"])
    def test_disposition_vocabulary(self, disp: str) -> None:
        a = _assertion(status="fail", disposition=disp)
        assert a.disposition == disp

    def test_bad_disposition_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _assertion(status="fail", disposition="app")  # app maps to 'counts'

    def test_carries_gate_id_and_evidence_ref(self) -> None:
        a = _assertion(evidence_ref="shots/a1.png", observed="200", expected="200")
        assert a.gate_id == "gate_phase1_login"
        assert a.evidence_ref == "shots/a1.png"


class TestQAVerdictEvidenceRefs:
    def test_a3_evidence_and_assertions(self) -> None:
        p = QAVerdictPayload(
            correlation_id=_CID,
            run_id="run-1",
            env_id="lpa-poc-dev",
            verdict="fail",
            gate_ids=["gate_phase1_login", "gate_phase6_sweep"],
            assertions=[
                _assertion(status="pass"),
                _assertion(id="a2", status="fail", disposition="counts", evidence_ref="s/a2.png"),
            ],
            evidence_index_ref="qa/gates/history/run-1/index.json",
            dispositions_ref="qa/gates/history/run-1/dispositions.yaml",
            attempts_ledger_ref="qa/gates/history/run-1/attempts.yaml",
            app_url="https://lpa.local",
            attempt=2,
            leak_sweep_findings=0,
            decided_at=_NOW,
        )
        assert p.assertions[1].disposition == "counts"
        assert p.leak_sweep_findings == 0


class TestLiveGateResult:
    def test_scenario_and_screenshot_refs(self) -> None:
        p = LiveGateResultPayload(
            correlation_id=_CID,
            run_id="run-1",
            env_id="study-tutor-gb10",
            verdict="pass",
            gate_ids=["walk_checkpoint_1"],
            assertions=[_assertion()],
            evidence_index_ref="index.json",
            attempt=1,
            app_url="http://100.1.2.3:8080",
            screenshot_refs=["shots/1.png", "shots/2.png"],
            trace_refs=["traces/run.har"],
            finished_at=_NOW,
        )
        assert p.screenshot_refs == ["shots/1.png", "shots/2.png"]
        assert p.trace_refs == ["traces/run.har"]


# ---------------------------------------------------------------------------
# A-4 usage / loop_stats rollup block
# ---------------------------------------------------------------------------


class TestUsageRollupBlock:
    def _rollup(self) -> list[UsageRollup]:
        return [
            UsageRollup(
                lane="frontier",
                provider="anthropic",
                model="claude-opus-4-8",
                calls=12,
                input_tokens=1000,
                output_tokens=500,
                cost_gbp=0.42,
            ),
            UsageRollup(
                lane="local",
                provider="ollama",
                model="gemma4:26b",
                calls=3,
                input_tokens=200,
                output_tokens=80,
            ),
        ]

    def test_local_lane_cost_gbp_nullable(self) -> None:
        assert self._rollup()[1].cost_gbp is None

    def test_usage_optional_on_stage_complete(self) -> None:
        p = StageCompletePayload(
            feature_id="FEAT-DEP001",
            build_id="b1",
            stage_label="LIVE_GATE",
            target_kind="fleet_capability",
            target_identifier="live-gate-driver",
            status="PASSED",
            gate_mode=None,
            coach_score=None,
            duration_secs=1.5,
            completed_at="2026-07-08T12:00:00Z",
            correlation_id=_CID,
            usage=self._rollup(),
            loop_stats=LoopStats(turns=4, sdk_ceiling_hits=0),
        )
        assert p.usage is not None
        assert p.usage[0].lane == "frontier"
        assert p.loop_stats is not None
        assert p.loop_stats.turns == 4

    def test_usage_optional_on_build_complete(self) -> None:
        p = BuildCompletePayload(
            feature_id="FEAT-DEP001",
            build_id="b1",
            tasks_completed=3,
            tasks_failed=0,
            tasks_total=3,
            duration_seconds=100,
            summary="ok",
            usage=self._rollup(),
        )
        assert p.usage is not None
        # default None keeps old publishers valid
        p2 = BuildCompletePayload(
            feature_id="FEAT-DEP001",
            build_id="b1",
            tasks_completed=1,
            tasks_failed=0,
            tasks_total=1,
            duration_seconds=1,
            summary="ok",
        )
        assert p2.usage is None and p2.loop_stats is None

    def test_usage_optional_on_verdict(self) -> None:
        p = QAVerdictPayload(
            correlation_id=_CID,
            run_id="run-1",
            env_id="e",
            verdict="pass",
            gate_ids=["g1"],
            evidence_index_ref="ref",
            attempt=1,
            decided_at=_NOW,
            usage=self._rollup(),
        )
        assert p.usage is not None


# ---------------------------------------------------------------------------
# Topic registry + envelope round-trip
# ---------------------------------------------------------------------------


class TestDeployRevertedPayload:
    """O-32 revert-on-gate-fail receipt (nats-core 0.7.1)."""

    def _reverted(self, **overrides: object) -> DeployRevertedPayload:
        defaults: dict[str, object] = {
            "correlation_id": _CID,
            "env_id": "gb10-prod",
            "deploy_run_id": "deployrun-1",
            "reverted_to_image_ref": "study-tutor:rollback-20260713",
            "failing_verdict": "fail",
            "reverted_at": _NOW,
        }
        defaults.update(overrides)
        return DeployRevertedPayload(**defaults)  # type: ignore[arg-type]

    def test_minimal_fields_and_status_default(self) -> None:
        p = self._reverted()
        assert p.status == "reverted"
        assert p.reverted_to_image_ref == "study-tutor:rollback-20260713"
        assert p.failing_verdict == "fail"

    def test_failing_verdict_must_be_in_enum(self) -> None:
        with pytest.raises(ValidationError):
            self._reverted(failing_verdict="borked")

    def test_bad_feat_id_rejected(self) -> None:
        with pytest.raises(ValidationError):
            self._reverted(feat_id="not a feat id")

    def test_envelope_round_trip(self) -> None:
        payload = self._reverted(
            feat_id="FEAT-9A21",
            failing_verdict_ref="ev/idx.json",
            revert_runbook_ref="revert-deployrun-1",
            deploy_record_ref="deploys/dr.md",
        )
        env = MessageEnvelope(
            source_id="forge",
            event_type=EventType.DEPLOY_REVERTED,
            correlation_id=_CID,
            payload=payload.model_dump(mode="json"),
        )
        raw = env.model_dump_json()
        restored_env = MessageEnvelope.model_validate_json(raw)
        cls = payload_class_for_event_type(restored_env.event_type)
        restored = cls.model_validate(restored_env.payload)
        assert isinstance(restored, DeployRevertedPayload)
        assert restored.reverted_to_image_ref == "study-tutor:rollback-20260713"
        assert restored.failing_verdict == "fail"
        assert restored.feat_id == "FEAT-9A21"


class TestDeployTopics:
    @pytest.mark.parametrize(
        "template",
        [
            Topics.Deploy.DEPLOY_QUEUED,
            Topics.Deploy.DEPLOY_STARTED,
            Topics.Deploy.DEPLOY_COMPLETE,
            Topics.Deploy.DEPLOY_FAILED,
            Topics.Deploy.DEPLOY_REVERTED,
            Topics.Deploy.QA_VERDICT,
            Topics.Deploy.LIVE_GATE_RESULT,
        ],
    )
    def test_keyed_on_correlation_id_and_registered(self, template: str) -> None:
        resolved = Topics.resolve(template, correlation_id="abc-123")
        assert resolved.endswith("abc-123")
        assert resolved.startswith("deploy.")
        assert template in Topics.ALL_TOPICS

    def test_wildcard_excluded_from_all_topics(self) -> None:
        assert Topics.Deploy.ALL == "deploy.>"
        assert Topics.Deploy.ALL not in Topics.ALL_TOPICS

    def test_for_project_tenant_prefix_a6(self) -> None:
        resolved = Topics.resolve(Topics.Deploy.QA_VERDICT, correlation_id="c1")
        scoped = Topics.for_project("finproxy", resolved)
        assert scoped == "finproxy.deploy.qa-verdict.c1"


class TestRegistryWiring:
    @pytest.mark.parametrize(
        ("event_type", "payload_cls"),
        [
            (EventType.DEPLOY_QUEUED, DeployQueuedPayload),
            (EventType.DEPLOY_STARTED, DeployStartedPayload),
            (EventType.DEPLOY_COMPLETE, DeployCompletePayload),
            (EventType.DEPLOY_FAILED, DeployFailedPayload),
            (EventType.DEPLOY_REVERTED, DeployRevertedPayload),
            (EventType.QA_VERDICT, QAVerdictPayload),
            (EventType.LIVE_GATE_RESULT, LiveGateResultPayload),
        ],
    )
    def test_registry(self, event_type: EventType, payload_cls: type) -> None:
        assert payload_class_for_event_type(event_type) is payload_cls

    def test_envelope_round_trip(self) -> None:
        payload = DeployCompletePayload(
            correlation_id=_CID,
            env_id="e",
            deploy_run_id="r",
            artifact_digest="sha256:abc",
            image_digests={"backend": "sha256:x"},
            deploy_record_ref="ref",
            completed_at=_NOW,
        )
        env = MessageEnvelope(
            source_id="forge",
            event_type=EventType.DEPLOY_COMPLETE,
            correlation_id=_CID,
            payload=payload.model_dump(mode="json"),
        )
        raw = env.model_dump_json()
        restored_env = MessageEnvelope.model_validate_json(raw)
        cls = payload_class_for_event_type(restored_env.event_type)
        restored = cls.model_validate(restored_env.payload)
        assert isinstance(restored, DeployCompletePayload)
        assert restored.deploy_record_ref == "ref"
        assert restored.image_digests == {"backend": "sha256:x"}

    def test_verdict_round_trip_preserves_dispositions(self) -> None:
        payload = QAVerdictPayload(
            correlation_id=_CID,
            run_id="run-1",
            env_id="e",
            verdict="fail",
            gate_ids=["g1"],
            assertions=[_assertion(status="fail", disposition="environment")],
            evidence_index_ref="ref",
            attempt=3,
            decided_at=_NOW,
        )
        restored = QAVerdictPayload.model_validate_json(payload.model_dump_json())
        assert restored.assertions[0].disposition == "environment"
        assert restored.attempt == 3


# ---------------------------------------------------------------------------
# Capability taxonomy
# ---------------------------------------------------------------------------


class TestCapabilityTaxonomy:
    def test_three_kinds(self) -> None:
        assert FLEET_CAPABILITY_KINDS == {
            "deploy-runner",
            "live-gate-driver",
            "qa-verifier",
        }


# ---------------------------------------------------------------------------
# feat_id / task_id validator branches across EVERY payload
# ---------------------------------------------------------------------------


def _minimal_kwargs(cls: type) -> dict[str, object]:
    """Minimal valid kwargs (minus feat_id/task_id) for each payload class."""
    common = {"correlation_id": _CID}
    if cls is DeployQueuedPayload:
        return {**common, "env_id": "e", "deploy_run_id": "r", "queued_at": _NOW}
    if cls is DeployStartedPayload:
        return {**common, "env_id": "e", "deploy_run_id": "r", "started_at": _NOW}
    if cls is DeployCompletePayload:
        return {
            **common,
            "env_id": "e",
            "deploy_run_id": "r",
            "deploy_record_ref": "ref",
            "completed_at": _NOW,
        }
    if cls is DeployFailedPayload:
        return {
            **common,
            "env_id": "e",
            "deploy_run_id": "r",
            "failed_step": "s",
            "failure_reason": "x",
            "failed_at": _NOW,
        }
    if cls is QAVerdictPayload:
        return {
            **common,
            "run_id": "run-1",
            "env_id": "e",
            "verdict": "pass",
            "gate_ids": ["g1"],
            "evidence_index_ref": "ref",
            "attempt": 1,
            "decided_at": _NOW,
        }
    if cls is LiveGateResultPayload:
        return {
            **common,
            "run_id": "run-1",
            "env_id": "e",
            "verdict": "pass",
            "gate_ids": ["g1"],
            "evidence_index_ref": "ref",
            "attempt": 1,
            "finished_at": _NOW,
        }
    raise AssertionError(cls)


_ALL_PAYLOADS = [
    DeployQueuedPayload,
    DeployStartedPayload,
    DeployCompletePayload,
    DeployFailedPayload,
    QAVerdictPayload,
    LiveGateResultPayload,
]


class TestIdentifierValidatorsEveryPayload:
    @pytest.mark.parametrize("cls", _ALL_PAYLOADS)
    def test_bad_feat_id_rejected(self, cls: type) -> None:
        with pytest.raises(ValidationError, match="feat_id"):
            cls(**_minimal_kwargs(cls), feat_id="not-a-feat")

    @pytest.mark.parametrize("cls", _ALL_PAYLOADS)
    def test_bad_task_id_rejected(self, cls: type) -> None:
        with pytest.raises(ValidationError, match="task_id"):
            cls(**_minimal_kwargs(cls), task_id="not-a-task")

    @pytest.mark.parametrize("cls", _ALL_PAYLOADS)
    def test_valid_ids_and_none_accepted(self, cls: type) -> None:
        ok = cls(**_minimal_kwargs(cls), feat_id="FEAT-DEP001", task_id="TASK-FIX01")
        assert ok.feat_id == "FEAT-DEP001"
        assert ok.task_id == "TASK-FIX01"
        # omitted -> None (no validate_default surface to trip; e60d41d discipline N/A)
        default = cls(**_minimal_kwargs(cls))
        assert default.feat_id is None
        assert default.task_id is None

    def test_deploy_queued_bad_target_repo_rejected(self) -> None:
        with pytest.raises(ValidationError, match="target_repo"):
            DeployQueuedPayload(**_minimal_kwargs(DeployQueuedPayload), target_repo="bare")
