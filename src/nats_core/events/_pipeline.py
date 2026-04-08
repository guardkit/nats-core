"""Pipeline event payload schemas for the feature build lifecycle.

Covers the full lifecycle of a feature build:
planned → ready → started → progress → complete/failed.

All models use ``ConfigDict(extra="ignore")`` for forward compatibility
(ADR-002) and ``Field(description=...)`` on every field.

This is a private module; public names are re-exported from
``nats_core.events.__init__``.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


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
    """Payload emitted when a feature has been planned and decomposed into waves.

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
