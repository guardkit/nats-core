"""Pipeline event payload schemas for the feature build lifecycle.

Covers the full lifecycle of a feature build:
planned → ready → queued → started → progress → complete/failed,
plus per-stage lifecycle events (stage-complete, stage-gated)
and build pause/resume flow.

Existing models (v1) use ``ConfigDict(extra="ignore")`` per ADR-002.
New v2.2 models use ``ConfigDict(extra="allow")`` for forward compatibility
with future publishers (deliberate divergence — see TASK-7448 review).

All models use ``Field(description=...)`` on every field.

This is a private module; public names are re-exported from
``nats_core.events.__init__``.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# Regex patterns for BuildQueuedPayload validators.
FEATURE_ID_PATTERN = re.compile(r"^FEAT-[A-Z0-9]{3,12}$")
REPO_PATTERN = re.compile(r"^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$")

# Literal types for BuildQueuedPayload provenance fields.
TriggerSource = Literal["cli", "jarvis", "forge-internal", "notification-adapter"]
OriginatingAdapter = Literal[
    "terminal",
    "voice-reachy",
    "telegram",
    "slack",
    "dashboard",
    "cli-wrapper",
]


class WaveSummary(BaseModel):
    """Summary of a single wave within a feature plan.

    Attributes:
        wave_number: 1-based index of this wave.
        task_count: Number of tasks in this wave.
        task_ids: Identifiers of each task in the wave.
    """

    model_config = ConfigDict(extra="ignore")

    wave_number: int = Field(ge=1, description="1-based index of this wave")
    task_count: int = Field(ge=0, description="Number of tasks in this wave")
    task_ids: list[str] = Field(description="Identifiers of each task in the wave")


class TaskProgress(BaseModel):
    """Progress status for a single task within a build.

    Attributes:
        task_id: Unique identifier for the task.
        status: Current execution status.
        duration_seconds: Elapsed time in seconds, or None if not yet timed.
    """

    model_config = ConfigDict(extra="ignore")

    task_id: str = Field(description="Unique identifier for the task")
    status: Literal["pending", "running", "complete", "failed"] = Field(
        description="Current execution status"
    )
    duration_seconds: int | None = Field(
        default=None, description="Elapsed time in seconds, or None if not yet timed"
    )


class FeaturePlannedPayload(BaseModel):
    """DEPRECATED: Use BuildQueuedPayload.

    Retained for backward compatibility, to be removed in nats-core v2.x.

    Payload emitted when a feature has been planned and decomposed into waves.

    Attributes:
        feature_id: Unique identifier for the feature.
        wave_count: Total number of waves in the plan.
        task_count: Total number of tasks across all waves.
        waves: Ordered list of wave summaries.
    """

    model_config = ConfigDict(extra="ignore")

    feature_id: str = Field(description="Unique identifier for the feature")
    wave_count: int = Field(ge=1, description="Total number of waves in the plan")
    task_count: int = Field(ge=1, description="Total number of tasks across all waves")
    waves: list[WaveSummary] = Field(description="Ordered list of wave summaries")

    def model_post_init(self, __context: Any) -> None:
        import warnings

        warnings.warn(
            "FeaturePlannedPayload is deprecated; use BuildQueuedPayload",
            DeprecationWarning,
            stacklevel=2,
        )

    @model_validator(mode="after")
    def _waves_length_matches_wave_count(self) -> FeaturePlannedPayload:
        if len(self.waves) != self.wave_count:
            msg = (
                f"len(waves) is {len(self.waves)} but wave_count is {self.wave_count}; "
                "they must be equal"
            )
            raise ValueError(msg)
        return self


class FeatureReadyForBuildPayload(BaseModel):
    """Payload emitted when a feature is ready to begin building.

    Attributes:
        feature_id: Unique identifier for the feature.
        spec_path: Path to the feature specification YAML.
        plan_path: Path to the feature plan document.
        pipeline_type: Whether this is a greenfield or existing codebase build.
        source_commands: GuardKit commands that produced the spec.
    """

    model_config = ConfigDict(extra="ignore")

    feature_id: str = Field(description="Unique identifier for the feature")
    spec_path: str = Field(description="Path to the feature specification YAML")
    plan_path: str = Field(description="Path to the feature plan document")
    pipeline_type: Literal["greenfield", "existing"] = Field(
        description="Whether this is a greenfield or existing codebase build"
    )
    source_commands: list[str] = Field(
        default_factory=list,
        description="GuardKit commands that produced the spec",
    )


class BuildStartedPayload(BaseModel):
    """Payload emitted when a feature build begins execution.

    Attributes:
        feature_id: Unique identifier for the feature.
        build_id: Build identifier in format ``build-{feature_id}-{YYYYMMDDHHMMSS}``.
        wave_total: Total number of waves to execute.
    """

    model_config = ConfigDict(extra="ignore")

    feature_id: str = Field(description="Unique identifier for the feature")
    build_id: str = Field(
        description="Build identifier in format build-{feature_id}-{YYYYMMDDHHMMSS}"
    )
    wave_total: int = Field(ge=1, description="Total number of waves to execute")


class BuildProgressPayload(BaseModel):
    """Payload emitted periodically during a feature build to report progress.

    Attributes:
        feature_id: Unique identifier for the feature.
        build_id: Build identifier.
        wave: Current wave number (1-based).
        wave_total: Total number of waves.
        overall_progress_pct: Overall build progress as a percentage (0.0–100.0).
        elapsed_seconds: Total elapsed time in seconds.
    """

    model_config = ConfigDict(extra="ignore")

    feature_id: str = Field(description="Unique identifier for the feature")
    build_id: str = Field(description="Build identifier")
    wave: int = Field(ge=1, description="Current wave number (1-based)")
    wave_total: int = Field(ge=1, description="Total number of waves")
    overall_progress_pct: float = Field(
        ge=0.0, le=100.0, description="Overall build progress as a percentage (0.0-100.0)"
    )
    elapsed_seconds: int = Field(ge=0, description="Total elapsed time in seconds")

    @model_validator(mode="after")
    def _wave_must_not_exceed_wave_total(self) -> BuildProgressPayload:
        if self.wave > self.wave_total:
            msg = (
                f"wave is {self.wave} but wave_total is {self.wave_total}; "
                "wave must be <= wave_total"
            )
            raise ValueError(msg)
        return self


class BuildCompletePayload(BaseModel):
    """Payload emitted when a feature build finishes (success or partial failure).

    Attributes:
        feature_id: Unique identifier for the feature.
        build_id: Build identifier.
        repo: Repository name for the build.
        branch: Branch name for the build.
        tasks_completed: Number of tasks that completed successfully.
        tasks_failed: Number of tasks that failed.
        tasks_total: Total number of tasks (must equal completed + failed).
        pr_url: URL of the created pull request, or None.
        duration_seconds: Total build duration in seconds.
        summary: Human-readable summary of the build outcome.
    """

    model_config = ConfigDict(extra="ignore")

    feature_id: str = Field(description="Unique identifier for the feature")
    build_id: str = Field(description="Build identifier")
    repo: str | None = Field(default=None, description="Repository name for the build")
    branch: str | None = Field(default=None, description="Branch name for the build")
    tasks_completed: int = Field(ge=0, description="Number of tasks that completed successfully")
    tasks_failed: int = Field(ge=0, description="Number of tasks that failed")
    tasks_total: int = Field(ge=1, description="Total number of tasks")
    pr_url: str | None = Field(default=None, description="URL of the created pull request, or None")
    duration_seconds: int = Field(ge=0, description="Total build duration in seconds")
    summary: str = Field(description="Human-readable summary of the build outcome")

    @model_validator(mode="after")
    def _tasks_sum_must_equal_total(self) -> BuildCompletePayload:
        actual_sum = self.tasks_completed + self.tasks_failed
        if actual_sum != self.tasks_total:
            msg = (
                f"tasks_completed ({self.tasks_completed}) + tasks_failed ({self.tasks_failed}) "
                f"= {actual_sum}, but tasks_total is {self.tasks_total}; they must be equal"
            )
            raise ValueError(msg)
        return self


class BuildFailedPayload(BaseModel):
    """Payload emitted when a feature build fails fatally.

    Attributes:
        feature_id: Unique identifier for the feature.
        build_id: Build identifier.
        failure_reason: Human-readable description of the failure cause.
        recoverable: Whether the build can be retried.
        failed_task_id: Identifier of the task that caused the failure, or None.
    """

    model_config = ConfigDict(extra="ignore")

    feature_id: str = Field(description="Unique identifier for the feature")
    build_id: str = Field(description="Build identifier")
    failure_reason: str = Field(description="Human-readable description of the failure cause")
    recoverable: bool = Field(description="Whether the build can be retried")
    failed_task_id: str | None = Field(
        default=None,
        description="Identifier of the task that caused the failure, or None",
    )


# ---------------------------------------------------------------------------
# v2.2 pipeline payloads (ConfigDict(extra="allow") for forward compat)
# ---------------------------------------------------------------------------


class BuildQueuedPayload(BaseModel):
    """Published to pipeline.build-queued.{feature_id} to trigger a Forge build.

    Any trigger source (CLI, Jarvis, future adapters) publishes this payload to
    the same JetStream topic. Forge consumes without distinguishing sources at
    the consumer level; the triggered_by / originating_adapter fields are for
    history, diagnostics, and routing progress events back to the originator.

    Attributes:
        feature_id: FEAT-XXX identifier.
        repo: GitHub org/repo, e.g. guardkit/lpa-platform.
        branch: Base branch to branch from.
        feature_yaml_path: Path to feature YAML spec, relative to repo root.
        max_turns: Max AutoBuild Player-Coach turns per task before escalation.
        sdk_timeout_seconds: Max seconds per GuardKit autobuild subprocess invocation.
        wave_gating: If true, Forge pauses between waves for explicit approval.
        config_overrides: Narrow per-build overrides of forge.yaml thresholds.
        triggered_by: Which layer originated this build-queued message.
        originating_adapter: Which Jarvis adapter the human interacted with.
        originating_user: User identifier (e.g. 'rich').
        correlation_id: Stable ID for tracing this build across stages and streams.
        parent_request_id: For Jarvis-triggered builds, the dispatch message ID.
        retry_count: Incremented by Forge on crash-recovery redelivery.
        requested_at: When the request was made at the originating layer.
        queued_at: When the message was published to JetStream.
    """

    model_config = ConfigDict(extra="allow")

    # --- identity ---
    feature_id: str = Field(description="FEAT-XXX identifier")
    repo: str = Field(description="GitHub org/repo, e.g. guardkit/lpa-platform")
    branch: str = Field(default="main", description="Base branch to branch from")
    feature_yaml_path: str = Field(
        description="Path to feature YAML spec, relative to repo root"
    )

    # --- build config (narrow overrides only) ---
    max_turns: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Max AutoBuild Player-Coach turns per task before escalation",
    )
    sdk_timeout_seconds: int = Field(
        default=1800,
        ge=60,
        le=7200,
        description="Max seconds per GuardKit autobuild subprocess invocation",
    )
    wave_gating: bool = Field(
        default=False,
        description="If true, Forge pauses between waves for explicit approval",
    )
    config_overrides: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Narrow per-build overrides of forge.yaml thresholds. "
            "Keys must match forge.yaml top-level keys. Use sparingly."
        ),
    )

    # --- provenance ---
    triggered_by: TriggerSource = Field(
        description="Which layer originated this build-queued message"
    )
    originating_adapter: OriginatingAdapter | None = Field(
        default=None,
        description=(
            "Which Jarvis adapter the human interacted with. "
            "Required when triggered_by == 'jarvis'. None for CLI."
        ),
    )
    originating_user: str | None = Field(
        default=None,
        description="User identifier (e.g. 'rich'). Free-form for now.",
    )

    # --- correlation & tracing ---
    correlation_id: str = Field(
        description="Stable ID for tracing this build across stages and streams"
    )
    parent_request_id: str | None = Field(
        default=None,
        description=(
            "For Jarvis-triggered builds, the ID of the jarvis.dispatch.* message "
            "that spawned this build. Lets Jarvis correlate progress events back "
            "to the originating conversation/session."
        ),
    )

    # --- retry semantics ---
    retry_count: int = Field(
        default=0,
        ge=0,
        description=(
            "Incremented by Forge on crash-recovery redelivery. Publishers "
            "should leave this at 0."
        ),
    )

    # --- timing ---
    requested_at: datetime = Field(
        description="When the request was made at the originating layer"
    )
    queued_at: datetime = Field(
        description="When the message was published to JetStream"
    )

    # --- validators ---
    @field_validator("feature_id")
    @classmethod
    def _validate_feature_id(cls, v: str) -> str:
        if not FEATURE_ID_PATTERN.match(v):
            msg = f"feature_id must match {FEATURE_ID_PATTERN.pattern}, got {v!r}"
            raise ValueError(msg)
        return v

    @field_validator("repo")
    @classmethod
    def _validate_repo(cls, v: str) -> str:
        if not REPO_PATTERN.match(v):
            msg = f"repo must be 'org/name' format, got {v!r}"
            raise ValueError(msg)
        return v

    @field_validator("originating_adapter")
    @classmethod
    def _adapter_required_for_jarvis(
        cls, v: OriginatingAdapter | None, info: Any
    ) -> OriginatingAdapter | None:
        triggered_by = info.data.get("triggered_by")
        if triggered_by == "jarvis" and v is None:
            msg = "originating_adapter is required when triggered_by == 'jarvis'"
            raise ValueError(msg)
        if triggered_by == "cli" and v not in (None, "terminal", "cli-wrapper"):
            msg = (
                "CLI trigger must use originating_adapter 'terminal', "
                "'cli-wrapper', or None"
            )
            raise ValueError(msg)
        return v


class BuildPausedPayload(BaseModel):
    """Payload emitted when a build is paused at a quality gate.

    Attributes:
        feature_id: Unique identifier for the feature.
        build_id: Build identifier.
        stage: Pipeline stage that triggered the pause.
        coach_score: Coach quality score that triggered the gate.
        threshold: Minimum score threshold for this gate.
        gate_mode: Gate enforcement mode.
        details: Human-readable explanation of why the build was paused.
        correlation_id: Correlates this event with other build lifecycle events.
        paused_at: UTC timestamp when the build was paused.
    """

    model_config = ConfigDict(extra="allow")

    feature_id: str = Field(description="Unique identifier for the feature")
    build_id: str = Field(description="Build identifier")
    stage: str = Field(description="Pipeline stage that triggered the pause")
    coach_score: float = Field(description="Coach quality score that triggered the gate")
    threshold: float = Field(description="Minimum score threshold for this gate")
    gate_mode: Literal["flag_for_review", "hard_stop"] = Field(
        description="Gate enforcement mode"
    )
    details: str = Field(
        description="Human-readable explanation of why the build was paused"
    )
    correlation_id: str = Field(
        description="Correlates this event with other build lifecycle events"
    )
    paused_at: datetime = Field(
        description="UTC timestamp when the build was paused"
    )


class BuildResumedPayload(BaseModel):
    """Payload emitted when a paused build is resumed after approval.

    Attributes:
        feature_id: Unique identifier for the feature.
        build_id: Build identifier.
        stage: Pipeline stage being resumed.
        resumed_by: Identifier of the approver (e.g. 'rich').
        decision: Approval decision.
        correlation_id: Correlates this event with other build lifecycle events.
        resumed_at: UTC timestamp when the build was resumed.
    """

    model_config = ConfigDict(extra="allow")

    feature_id: str = Field(description="Unique identifier for the feature")
    build_id: str = Field(description="Build identifier")
    stage: str = Field(description="Pipeline stage being resumed")
    resumed_by: str = Field(description="Identifier of the approver (e.g. 'rich')")
    decision: Literal["approve", "reject"] = Field(description="Approval decision")
    correlation_id: str = Field(
        description="Correlates this event with other build lifecycle events"
    )
    resumed_at: datetime = Field(
        description="UTC timestamp when the build was resumed"
    )


class StageCompletePayload(BaseModel):
    """Payload emitted when a pipeline stage finishes.

    Attributes:
        feature_id: Unique identifier for the feature.
        build_id: Build identifier.
        stage: Pipeline stage that completed.
        status: Stage outcome.
        coach_score: Coach quality score, if applicable.
        duration_secs: Stage duration in seconds.
        correlation_id: Correlates this event with other build lifecycle events.
        completed_at: UTC timestamp when the stage completed.
    """

    model_config = ConfigDict(extra="allow")

    feature_id: str = Field(description="Unique identifier for the feature")
    build_id: str = Field(description="Build identifier")
    stage: str = Field(description="Pipeline stage that completed")
    status: Literal["passed", "failed", "gated", "skipped"] = Field(
        description="Stage outcome"
    )
    coach_score: float | None = Field(
        default=None, description="Coach quality score, if applicable"
    )
    duration_secs: float = Field(description="Stage duration in seconds")
    correlation_id: str = Field(
        description="Correlates this event with other build lifecycle events"
    )
    completed_at: datetime = Field(
        description="UTC timestamp when the stage completed"
    )


class StageGatedPayload(BaseModel):
    """Payload emitted when a pipeline stage is gated by a quality check.

    Attributes:
        feature_id: Unique identifier for the feature.
        build_id: Build identifier.
        stage: Pipeline stage that was gated.
        gate_mode: Gate enforcement mode.
        coach_score: Coach quality score that triggered the gate.
        threshold: Minimum score threshold for this gate.
        details: Human-readable explanation of the gating decision.
        correlation_id: Correlates this event with other build lifecycle events.
        gated_at: UTC timestamp when the stage was gated.
    """

    model_config = ConfigDict(extra="allow")

    feature_id: str = Field(description="Unique identifier for the feature")
    build_id: str = Field(description="Build identifier")
    stage: str = Field(description="Pipeline stage that was gated")
    gate_mode: Literal["flag_for_review", "hard_stop"] = Field(
        description="Gate enforcement mode"
    )
    coach_score: float = Field(
        description="Coach quality score that triggered the gate"
    )
    threshold: float = Field(description="Minimum score threshold for this gate")
    details: str = Field(
        description="Human-readable explanation of the gating decision"
    )
    correlation_id: str = Field(
        description="Correlates this event with other build lifecycle events"
    )
    gated_at: datetime = Field(
        description="UTC timestamp when the stage was gated"
    )
