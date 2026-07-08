"""Deploy / QA-verdict / live-gate wire payloads (WS2 B7, the last-mile stage).

The factory's output definition graduates to **merged + QA-verified + deployed
+ live-gated** (WS2 scope-design §4, §5). These payloads carry the deploy stage
and the live-gate runner's verdicts onto the bus so jarvis (the phone loop) and
the fleet dashboard can observe "deployed / live-verified" for the first time.

Vocabulary discipline (WS2 B7 guardrail + backward-edge episode schema contract
2026-07-07 §4.3/§4.4/§7): field names **mirror the F7 deploy-record and the
scope-design §3 results-envelope vocabulary VERBATIM — one vocabulary, no
translation layer**. The two deliberate naming exceptions pinned in the contract
(§7) are ``feat_id`` (⇐ envelope ``feature_id``, the 008-006 cross-workstream
join key) and ``env_id`` (⇐ envelope ``target_env`` / F7 header ``env``, the
deploy profile is the source of truth). These payloads are **notifications** —
forge's authoritative live-gate input stays the seam stdout envelope (§4.6);
they never trigger forge.

State discipline (ADR-ARCH-004): no session state anywhere — state lives in NATS
payloads + forge SQLite + the committed F7 deploy record. These payloads are
pointers onto that record, not the record.

``validate_default`` note: the Session-I ``originating_adapter`` defect
(nats-core 0.6.0, ``e60d41d``) is already fixed on the queued payloads. The
deploy payloads carry no adapter/trigger-conditional field, so there is no
``validate_default`` surface to guard here — the discipline was reviewed and is
not applicable, not skipped.

All models use ``ConfigDict(extra="allow")`` for forward compatibility with
future producers (the A-4 ``usage`` block is additive on top of this).

This is a private module; public names are re-exported from
``nats_core.events.__init__``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from nats_core.events._pipeline import (
    FEATURE_ID_PATTERN,
    REPO_PATTERN,
    TASK_ID_PATTERN,
    LoopStats,
    UsageRollup,
)

# ---------------------------------------------------------------------------
# Shared vocabulary
# ---------------------------------------------------------------------------

# The verdict enum, four-for-four (scope-design §3 results envelope; DF-017;
# backward-edge §4.4). ``instrument_fail`` and ``environment_fail`` are
# first-class: they never indict the system under test and are NEVER counted
# against the feature (ST-11 attribution discipline).
Verdict = Literal["pass", "fail", "instrument_fail", "environment_fail"]

# Per-assertion failure attribution (backward-edge §4.4). ``None`` on a passing
# assertion, so a green run legitimately carries no dispositions. The B4
# attribution mapping (§7 item 7): counts ⇐ {app, backend, contract_gap};
# instrument ⇐ instrument; environment ⇐ environment.
AssertionDisposition = Literal["counts", "instrument", "environment"]

# Deploy terminal status — the DeployComplete/Failed discriminator (§4.3).
DeployStatus = Literal["complete", "failed"]


# ---------------------------------------------------------------------------
# Capability taxonomy (WS2 scope-design §4)
# ---------------------------------------------------------------------------
#
# The three last-mile fleet capabilities. ``StageCompletePayload.target_kind``
# already anticipates ``fleet_capability`` targets; this taxonomy pins the
# controlled vocabulary for ``target_identifier`` (and for AgentManifest
# ``agent_id`` / registrations) when a stage runs one of these capabilities, so
# consumers can classify deploy/QA/live-gate work without string-guessing.
FleetCapabilityKind = Literal["deploy-runner", "live-gate-driver", "qa-verifier"]
FLEET_CAPABILITY_KINDS: frozenset[str] = frozenset(
    ("deploy-runner", "live-gate-driver", "qa-verifier")
)


# ---------------------------------------------------------------------------
# Nested models
# ---------------------------------------------------------------------------


class AssertionResult(BaseModel):
    """One assertion outcome within a gate run (results-envelope field names verbatim).

    Mirrors the scope-design §3 results-envelope assertion shape and the
    backward-edge §4.4 ``AssertionResult`` VERBATIM: ``id`` / ``gate_id`` /
    ``status`` / ``disposition`` / ``evidence_ref`` (assertion ids are unique
    only per gate script, hence ``gate_id``). ``observed``/``expected`` are the
    envelope's optional human-facing detail.

    Attributes:
        id: Assertion id (unique only within its gate script).
        gate_id: The gate script this assertion belongs to (F4 vocabulary).
        status: The envelope's assertion status (free-form; B4 owns the set).
        disposition: Failure attribution, or None on a passing assertion.
        evidence_ref: Reference to the evidence for this assertion, or None.
        observed: Observed value (envelope detail), or None.
        expected: Expected value (envelope detail), or None.
    """

    model_config = ConfigDict(extra="allow")

    id: str = Field(description="Assertion id (unique only within its gate script)")
    gate_id: str = Field(description="The gate script this assertion belongs to (F4 gate_id)")
    status: str = Field(description="The envelope's assertion status (B4 owns the set)")
    disposition: AssertionDisposition | None = Field(
        default=None,
        description="Failure attribution (counts|instrument|environment); None when passing",
    )
    evidence_ref: str | None = Field(
        default=None, description="Reference to the evidence for this assertion, or None"
    )
    observed: str | None = Field(default=None, description="Observed value (envelope detail)")
    expected: str | None = Field(default=None, description="Expected value (envelope detail)")


# ---------------------------------------------------------------------------
# Deploy lifecycle payloads
# ---------------------------------------------------------------------------
#
# DeployQueued -> DeployStarted -> DeployComplete | DeployFailed, keyed by
# ``correlation_id`` (the build/feature spine — a deploy has no identity of its
# own beyond its forge run id). Every payload carries its own event timestamp
# and ``correlation_id`` (dashboard ask A-1). Field names mirror the F7
# deploy-record vocabulary (§4.3).


class DeployQueuedPayload(BaseModel):
    """Emitted on deploy.queued.{correlation_id} when a DEPLOY stage is enqueued.

    Attributes:
        correlation_id: Build/feature correlation back to planning.
        env_id: Deploy profile env_id (⇐ target_env; the deploy profile owns the name).
        deploy_run_id: Raw forge run id for this DEPLOY stage execution.
        feat_id: Mode-P/008-006 feature id, or None (work-item linkage).
        task_id: Fix-task id (TASK-XXX) for Mode C deploys, or None.
        target_repo: GitHub org/repo being deployed, or None.
        deploy_profile_ref: The deploy/profile.yaml ref to be consumed, or None.
        hosts: Host set from the profile (hosts[].host), or None.
        reservation_resource: Reservation to be taken (e.g. 'gb10-gpu'), or None.
        queued_at: When the DEPLOY stage was enqueued.
    """

    model_config = ConfigDict(extra="allow")

    correlation_id: str = Field(description="Build/feature correlation back to planning")
    env_id: str = Field(description="Deploy profile env_id (⇐ target_env)")
    deploy_run_id: str = Field(description="Raw forge run id for this DEPLOY stage execution")
    feat_id: str | None = Field(default=None, description="Feature id (008-006), or None")
    task_id: str | None = Field(default=None, description="Fix-task id (Mode C), or None")
    target_repo: str | None = Field(
        default=None, description="GitHub org/repo being deployed, or None"
    )
    deploy_profile_ref: str | None = Field(
        default=None, description="The deploy/profile.yaml ref to be consumed, or None"
    )
    hosts: list[str] | None = Field(
        default=None, description="Host set from the profile (hosts[].host), or None"
    )
    reservation_resource: str | None = Field(
        default=None, description="Reservation to be taken (e.g. 'gb10-gpu'), or None"
    )
    queued_at: datetime = Field(description="When the DEPLOY stage was enqueued")

    @field_validator("feat_id")
    @classmethod
    def _validate_feat_id(cls, v: str | None) -> str | None:
        if v is not None and not FEATURE_ID_PATTERN.match(v):
            msg = f"feat_id must match {FEATURE_ID_PATTERN.pattern}, got {v!r}"
            raise ValueError(msg)
        return v

    @field_validator("task_id")
    @classmethod
    def _validate_task_id(cls, v: str | None) -> str | None:
        if v is not None and not TASK_ID_PATTERN.match(v):
            msg = f"task_id must match {TASK_ID_PATTERN.pattern}, got {v!r}"
            raise ValueError(msg)
        return v

    @field_validator("target_repo")
    @classmethod
    def _validate_target_repo(cls, v: str | None) -> str | None:
        if v is not None and not REPO_PATTERN.match(v):
            msg = f"target_repo must be 'org/name' format, got {v!r}"
            raise ValueError(msg)
        return v


class DeployStartedPayload(BaseModel):
    """Emitted on deploy.started.{correlation_id} when the DEPLOY stage begins.

    Attributes:
        correlation_id: Build/feature correlation back to planning.
        env_id: Deploy profile env_id.
        deploy_run_id: Raw forge run id for this DEPLOY stage execution.
        feat_id: Feature id (008-006), or None.
        task_id: Fix-task id (Mode C), or None.
        deploy_profile_ref: The deploy/profile.yaml ref consumed, or None.
        runbook_ref: The rendered typed runbook being executed, or None.
        hosts: Host set from the profile, or None.
        reservation_resource: Reservation taken (e.g. 'gb10-gpu'), or None.
        started_at: When the DEPLOY stage began executing.
    """

    model_config = ConfigDict(extra="allow")

    correlation_id: str = Field(description="Build/feature correlation back to planning")
    env_id: str = Field(description="Deploy profile env_id (⇐ target_env)")
    deploy_run_id: str = Field(description="Raw forge run id for this DEPLOY stage execution")
    feat_id: str | None = Field(default=None, description="Feature id (008-006), or None")
    task_id: str | None = Field(default=None, description="Fix-task id (Mode C), or None")
    deploy_profile_ref: str | None = Field(
        default=None, description="The deploy/profile.yaml ref consumed, or None"
    )
    runbook_ref: str | None = Field(
        default=None, description="The rendered typed runbook being executed, or None"
    )
    hosts: list[str] | None = Field(
        default=None, description="Host set from the profile, or None"
    )
    reservation_resource: str | None = Field(
        default=None, description="Reservation taken (e.g. 'gb10-gpu'), or None"
    )
    started_at: datetime = Field(description="When the DEPLOY stage began executing")

    @field_validator("feat_id")
    @classmethod
    def _validate_feat_id(cls, v: str | None) -> str | None:
        if v is not None and not FEATURE_ID_PATTERN.match(v):
            msg = f"feat_id must match {FEATURE_ID_PATTERN.pattern}, got {v!r}"
            raise ValueError(msg)
        return v

    @field_validator("task_id")
    @classmethod
    def _validate_task_id(cls, v: str | None) -> str | None:
        if v is not None and not TASK_ID_PATTERN.match(v):
            msg = f"task_id must match {TASK_ID_PATTERN.pattern}, got {v!r}"
            raise ValueError(msg)
        return v


class DeployCompletePayload(BaseModel):
    """Emitted on deploy.complete.{correlation_id} when a DEPLOY stage succeeds.

    Backward-edge §7 item 8 obligation: carries ``env_id``, ``artifact_digest``,
    ``image_digests``, ``deploy_record_ref``, ``correlation_id`` — the
    ``deploy_record`` episode (§4.3) mirrors these names verbatim.

    Attributes:
        correlation_id: Build/feature correlation back to planning.
        env_id: Deploy profile env_id.
        deploy_run_id: Raw forge run id for this DEPLOY stage execution.
        status: Always 'complete' — the DeployComplete/Failed discriminator.
        feat_id: Feature id (008-006), or None.
        task_id: Fix-task id (Mode C), or None.
        artifact_digest: Merged-artifact digest (sha), or None.
        image_digests: service -> image digest map, or None.
        deploy_record_ref: Path/ref of the committed F7 deploy record (the evidence authority).
        deploy_profile_ref: The deploy/profile.yaml ref consumed, or None.
        runbook_ref: The rendered typed runbook executed, or None.
        hosts: Host set from the profile, or None.
        reservation_resource: Reservation taken (e.g. 'gb10-gpu'), or None.
        duration_seconds: Stage wall time in seconds, or None.
        completed_at: When the DEPLOY stage completed.
        usage: Optional per-lane LLM usage rollups (A-4) if models ran, or None.
        loop_stats: Optional outer-loop counters (A-4), or None.
    """

    model_config = ConfigDict(extra="allow")

    correlation_id: str = Field(description="Build/feature correlation back to planning")
    env_id: str = Field(description="Deploy profile env_id (⇐ target_env)")
    deploy_run_id: str = Field(description="Raw forge run id for this DEPLOY stage execution")
    status: Literal["complete"] = Field(
        default="complete", description="Always 'complete' — the terminal discriminator"
    )
    feat_id: str | None = Field(default=None, description="Feature id (008-006), or None")
    task_id: str | None = Field(default=None, description="Fix-task id (Mode C), or None")
    artifact_digest: str | None = Field(
        default=None, description="Merged-artifact digest (sha), or None"
    )
    image_digests: dict[str, str] | None = Field(
        default=None, description="service -> image digest map, or None"
    )
    deploy_record_ref: str = Field(
        description="Path/ref of the committed F7 deploy record (the evidence authority)"
    )
    deploy_profile_ref: str | None = Field(
        default=None, description="The deploy/profile.yaml ref consumed, or None"
    )
    runbook_ref: str | None = Field(
        default=None, description="The rendered typed runbook executed, or None"
    )
    hosts: list[str] | None = Field(
        default=None, description="Host set from the profile, or None"
    )
    reservation_resource: str | None = Field(
        default=None, description="Reservation taken (e.g. 'gb10-gpu'), or None"
    )
    duration_seconds: int | None = Field(
        default=None, ge=0, description="Stage wall time in seconds, or None"
    )
    completed_at: datetime = Field(description="When the DEPLOY stage completed")
    usage: list[UsageRollup] | None = Field(
        default=None, description="Optional per-lane LLM usage rollups (A-4), or None"
    )
    loop_stats: LoopStats | None = Field(
        default=None, description="Optional outer-loop counters (A-4), or None"
    )

    @field_validator("feat_id")
    @classmethod
    def _validate_feat_id(cls, v: str | None) -> str | None:
        if v is not None and not FEATURE_ID_PATTERN.match(v):
            msg = f"feat_id must match {FEATURE_ID_PATTERN.pattern}, got {v!r}"
            raise ValueError(msg)
        return v

    @field_validator("task_id")
    @classmethod
    def _validate_task_id(cls, v: str | None) -> str | None:
        if v is not None and not TASK_ID_PATTERN.match(v):
            msg = f"task_id must match {TASK_ID_PATTERN.pattern}, got {v!r}"
            raise ValueError(msg)
        return v


class DeployFailedPayload(BaseModel):
    """Emitted on deploy.failed.{correlation_id} when a DEPLOY stage fails.

    Backward-edge §7 item 8 obligation: carries the failing step type
    (``failed_step``) — a genuine addition to B7's current work list — plus the
    same F7 vocabulary as DeployComplete for the ``deploy_record`` episode
    (§4.3). ``deploy_record_ref`` is optional here: a failed run may leave a
    record addendum, or may fail before the record is written.

    Attributes:
        correlation_id: Build/feature correlation back to planning.
        env_id: Deploy profile env_id.
        deploy_run_id: Raw forge run id for this DEPLOY stage execution.
        status: Always 'failed' — the DeployComplete/Failed discriminator.
        failed_step: Step type at failure ('import_realm', 'health_check', ...).
        failure_reason: Human-readable description of the failure cause.
        recoverable: Whether the deploy can be retried.
        feat_id: Feature id (008-006), or None.
        task_id: Fix-task id (Mode C), or None.
        artifact_digest: Merged-artifact digest (sha), or None.
        image_digests: service -> image digest map, or None.
        deploy_record_ref: Path/ref of the F7 record addendum, or None.
        deploy_profile_ref: The deploy/profile.yaml ref consumed, or None.
        runbook_ref: The rendered typed runbook executed, or None.
        hosts: Host set from the profile, or None.
        reservation_resource: Reservation taken (e.g. 'gb10-gpu'), or None.
        duration_seconds: Stage wall time in seconds, or None.
        failed_at: When the DEPLOY stage failed.
    """

    model_config = ConfigDict(extra="allow")

    correlation_id: str = Field(description="Build/feature correlation back to planning")
    env_id: str = Field(description="Deploy profile env_id (⇐ target_env)")
    deploy_run_id: str = Field(description="Raw forge run id for this DEPLOY stage execution")
    status: Literal["failed"] = Field(
        default="failed", description="Always 'failed' — the terminal discriminator"
    )
    failed_step: str = Field(
        description="Step type at failure ('import_realm', 'health_check', ...)"
    )
    failure_reason: str = Field(description="Human-readable description of the failure cause")
    recoverable: bool = Field(default=False, description="Whether the deploy can be retried")
    feat_id: str | None = Field(default=None, description="Feature id (008-006), or None")
    task_id: str | None = Field(default=None, description="Fix-task id (Mode C), or None")
    artifact_digest: str | None = Field(
        default=None, description="Merged-artifact digest (sha), or None"
    )
    image_digests: dict[str, str] | None = Field(
        default=None, description="service -> image digest map, or None"
    )
    deploy_record_ref: str | None = Field(
        default=None, description="Path/ref of the F7 record addendum, or None"
    )
    deploy_profile_ref: str | None = Field(
        default=None, description="The deploy/profile.yaml ref consumed, or None"
    )
    runbook_ref: str | None = Field(
        default=None, description="The rendered typed runbook executed, or None"
    )
    hosts: list[str] | None = Field(
        default=None, description="Host set from the profile, or None"
    )
    reservation_resource: str | None = Field(
        default=None, description="Reservation taken (e.g. 'gb10-gpu'), or None"
    )
    duration_seconds: int | None = Field(
        default=None, ge=0, description="Stage wall time in seconds, or None"
    )
    failed_at: datetime = Field(description="When the DEPLOY stage failed")

    @field_validator("feat_id")
    @classmethod
    def _validate_feat_id(cls, v: str | None) -> str | None:
        if v is not None and not FEATURE_ID_PATTERN.match(v):
            msg = f"feat_id must match {FEATURE_ID_PATTERN.pattern}, got {v!r}"
            raise ValueError(msg)
        return v

    @field_validator("task_id")
    @classmethod
    def _validate_task_id(cls, v: str | None) -> str | None:
        if v is not None and not TASK_ID_PATTERN.match(v):
            msg = f"task_id must match {TASK_ID_PATTERN.pattern}, got {v!r}"
            raise ValueError(msg)
        return v


# ---------------------------------------------------------------------------
# QA / live-gate verdict payloads
# ---------------------------------------------------------------------------
#
# Both mirror the (B4-extended) results envelope (backward-edge §7 item 9,
# §4.4): verdict enum four-for-four; per-assertion results carry disposition;
# evidence_index_ref, app_url, run_id, attempt, correlation_id. They are
# NOTIFICATIONS — forge's authoritative live-gate input stays the seam stdout
# envelope (§4.6), never these bus payloads.


class QAVerdictPayload(BaseModel):
    """Emitted on deploy.qa-verdict.{correlation_id} — the overall QA verdict.

    The results-envelope verdict aggregated over all gates, published so a
    feature can be marked "QA verified live" (distinct from "coach passed") for
    the first time (scope-design §3/§4). Field names mirror the results envelope
    verbatim.

    Attributes:
        correlation_id: Correlation back to the build.
        run_id: The results envelope's run id (raw).
        env_id: Deploy profile env_id the run targeted (⇐ target_env).
        verdict: Four-for-four verdict (pass|fail|instrument_fail|environment_fail).
        gate_ids: Gate scripts executed (F4 vocabulary).
        assertions: Per-assertion outcomes with disposition.
        evidence_index_ref: The envelope's evidence index (F5 convention).
        attempt: 1-based, forge-side monotonic per correlation_id across campaigns.
        feat_id: Feature id (008-006), or None.
        task_id: Fix-task id (Mode C), or None.
        app_url: Live instance driven, or None.
        dispositions_ref: Ref to the F8 dispositions record, or None.
        attempts_ledger_ref: Ref to the F9 attempts ledger, or None.
        leak_sweep_findings: Count of leak-sweep findings (detail in evidence), or None.
        decided_at: When the verdict was rendered.
        usage: Optional per-lane LLM usage rollups (A-4) if models ran, or None.
        loop_stats: Optional outer-loop counters (A-4), or None.
    """

    model_config = ConfigDict(extra="allow")

    correlation_id: str = Field(description="Correlation back to the build")
    run_id: str = Field(description="The results envelope's run id (raw)")
    env_id: str = Field(description="Deploy profile env_id the run targeted (⇐ target_env)")
    verdict: Verdict = Field(
        description="Four-for-four verdict (pass|fail|instrument_fail|environment_fail)"
    )
    gate_ids: list[str] = Field(description="Gate scripts executed (F4 vocabulary)")
    assertions: list[AssertionResult] = Field(
        default_factory=list, description="Per-assertion outcomes with disposition"
    )
    evidence_index_ref: str = Field(description="The envelope's evidence index (F5 convention)")
    attempt: int = Field(
        ge=1,
        description="1-based, forge-side monotonic per correlation_id across campaigns",
    )
    feat_id: str | None = Field(default=None, description="Feature id (008-006), or None")
    task_id: str | None = Field(default=None, description="Fix-task id (Mode C), or None")
    app_url: str | None = Field(default=None, description="Live instance driven, or None")
    dispositions_ref: str | None = Field(
        default=None, description="Ref to the F8 dispositions record, or None"
    )
    attempts_ledger_ref: str | None = Field(
        default=None, description="Ref to the F9 attempts ledger, or None"
    )
    leak_sweep_findings: int | None = Field(
        default=None, ge=0, description="Count of leak-sweep findings, or None"
    )
    decided_at: datetime = Field(description="When the verdict was rendered")
    usage: list[UsageRollup] | None = Field(
        default=None, description="Optional per-lane LLM usage rollups (A-4), or None"
    )
    loop_stats: LoopStats | None = Field(
        default=None, description="Optional outer-loop counters (A-4), or None"
    )

    @field_validator("feat_id")
    @classmethod
    def _validate_feat_id(cls, v: str | None) -> str | None:
        if v is not None and not FEATURE_ID_PATTERN.match(v):
            msg = f"feat_id must match {FEATURE_ID_PATTERN.pattern}, got {v!r}"
            raise ValueError(msg)
        return v

    @field_validator("task_id")
    @classmethod
    def _validate_task_id(cls, v: str | None) -> str | None:
        if v is not None and not TASK_ID_PATTERN.match(v):
            msg = f"task_id must match {TASK_ID_PATTERN.pattern}, got {v!r}"
            raise ValueError(msg)
        return v


class LiveGateResultPayload(BaseModel):
    """Emitted on deploy.live-gate-result.{correlation_id} — the live-gate run detail.

    The per-run scenario detail behind a :class:`QAVerdictPayload`: scenario
    (assertion) results plus the screenshot/trace refs and the live app URL
    (scope-design §4). Mirrors the results envelope (backward-edge §4.4)
    verbatim.

    Attributes:
        correlation_id: Correlation back to the build.
        run_id: The results envelope's run id (raw).
        env_id: Deploy profile env_id the run targeted (⇐ target_env).
        verdict: Four-for-four verdict (pass|fail|instrument_fail|environment_fail).
        gate_ids: Gate scripts executed (F4 vocabulary).
        assertions: Per-scenario (assertion) outcomes with disposition.
        evidence_index_ref: The envelope's evidence index (F5 convention).
        attempt: 1-based, forge-side monotonic per correlation_id across campaigns.
        feat_id: Feature id (008-006), or None.
        task_id: Fix-task id (Mode C), or None.
        app_url: Live instance driven, or None.
        screenshot_refs: Ordered screenshot evidence refs, or empty.
        trace_refs: Trace/HAR/log evidence refs, or empty.
        leak_sweep_findings: Count of leak-sweep findings (detail in evidence), or None.
        finished_at: When the live-gate run finished.
        usage: Optional per-lane LLM usage rollups (A-4) if models ran, or None.
        loop_stats: Optional outer-loop counters (A-4), or None.
    """

    model_config = ConfigDict(extra="allow")

    correlation_id: str = Field(description="Correlation back to the build")
    run_id: str = Field(description="The results envelope's run id (raw)")
    env_id: str = Field(description="Deploy profile env_id the run targeted (⇐ target_env)")
    verdict: Verdict = Field(
        description="Four-for-four verdict (pass|fail|instrument_fail|environment_fail)"
    )
    gate_ids: list[str] = Field(description="Gate scripts executed (F4 vocabulary)")
    assertions: list[AssertionResult] = Field(
        default_factory=list, description="Per-scenario (assertion) outcomes with disposition"
    )
    evidence_index_ref: str = Field(description="The envelope's evidence index (F5 convention)")
    attempt: int = Field(
        ge=1,
        description="1-based, forge-side monotonic per correlation_id across campaigns",
    )
    feat_id: str | None = Field(default=None, description="Feature id (008-006), or None")
    task_id: str | None = Field(default=None, description="Fix-task id (Mode C), or None")
    app_url: str | None = Field(default=None, description="Live instance driven, or None")
    screenshot_refs: list[str] = Field(
        default_factory=list, description="Ordered screenshot evidence refs, or empty"
    )
    trace_refs: list[str] = Field(
        default_factory=list, description="Trace/HAR/log evidence refs, or empty"
    )
    leak_sweep_findings: int | None = Field(
        default=None, ge=0, description="Count of leak-sweep findings, or None"
    )
    finished_at: datetime = Field(description="When the live-gate run finished")
    usage: list[UsageRollup] | None = Field(
        default=None, description="Optional per-lane LLM usage rollups (A-4), or None"
    )
    loop_stats: LoopStats | None = Field(
        default=None, description="Optional outer-loop counters (A-4), or None"
    )

    @field_validator("feat_id")
    @classmethod
    def _validate_feat_id(cls, v: str | None) -> str | None:
        if v is not None and not FEATURE_ID_PATTERN.match(v):
            msg = f"feat_id must match {FEATURE_ID_PATTERN.pattern}, got {v!r}"
            raise ValueError(msg)
        return v

    @field_validator("task_id")
    @classmethod
    def _validate_task_id(cls, v: str | None) -> str | None:
        if v is not None and not TASK_ID_PATTERN.match(v):
            msg = f"task_id must match {TASK_ID_PATTERN.pattern}, got {v!r}"
            raise ValueError(msg)
        return v
