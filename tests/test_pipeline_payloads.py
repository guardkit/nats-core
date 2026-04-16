"""Tests for pipeline event payload schemas.

Validates all 8 Pydantic models in nats_core.events._pipeline:
  - WaveSummary, TaskProgress (nested models)
  - FeaturePlannedPayload, FeatureReadyForBuildPayload
  - BuildStartedPayload, BuildProgressPayload
  - BuildCompletePayload, BuildFailedPayload
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from nats_core.events import (
    BuildCompletePayload,
    BuildFailedPayload,
    BuildProgressPayload,
    BuildStartedPayload,
    FeaturePlannedPayload,
    FeatureReadyForBuildPayload,
    TaskProgress,
    WaveSummary,
)

# ---------------------------------------------------------------------------
# WaveSummary
# ---------------------------------------------------------------------------


class TestWaveSummary:
    """WaveSummary nested model validation."""

    def test_valid_wave_summary(self) -> None:
        ws = WaveSummary(wave_number=1, task_count=2, task_ids=["T1", "T2"])
        assert ws.wave_number == 1
        assert ws.task_count == 2
        assert ws.task_ids == ["T1", "T2"]

    def test_wave_number_ge_1(self) -> None:
        with pytest.raises(ValidationError):
            WaveSummary(wave_number=0, task_count=0, task_ids=[])

    def test_task_count_ge_0(self) -> None:
        with pytest.raises(ValidationError):
            WaveSummary(wave_number=1, task_count=-1, task_ids=[])

    def test_extra_fields_ignored(self) -> None:
        ws = WaveSummary(wave_number=1, task_count=0, task_ids=[], unknown_field="x")
        assert not hasattr(ws, "unknown_field")


# ---------------------------------------------------------------------------
# TaskProgress
# ---------------------------------------------------------------------------


class TestTaskProgress:
    """TaskProgress nested model validation."""

    def test_valid_task_progress(self) -> None:
        tp = TaskProgress(task_id="T1", status="running")
        assert tp.task_id == "T1"
        assert tp.status == "running"
        assert tp.duration_seconds is None

    def test_valid_statuses(self) -> None:
        for status in ("pending", "running", "complete", "failed"):
            tp = TaskProgress(task_id="T1", status=status)
            assert tp.status == status

    def test_invalid_status_rejected(self) -> None:
        with pytest.raises(ValidationError):
            TaskProgress(task_id="T1", status="unknown")

    def test_duration_seconds_optional(self) -> None:
        tp = TaskProgress(task_id="T1", status="complete", duration_seconds=42)
        assert tp.duration_seconds == 42

    def test_extra_fields_ignored(self) -> None:
        tp = TaskProgress(task_id="T1", status="pending", extra="ignored")
        assert not hasattr(tp, "extra")


# ---------------------------------------------------------------------------
# FeaturePlannedPayload
# ---------------------------------------------------------------------------


class TestFeaturePlannedPayload:
    """FeaturePlannedPayload validation including cross-field validator."""

    def test_valid_feature_planned(self) -> None:
        waves = [WaveSummary(wave_number=1, task_count=2, task_ids=["T1", "T2"])]
        with pytest.warns(DeprecationWarning, match="deprecated"):
            fp = FeaturePlannedPayload(
                feature_id="FEAT-001",
                wave_count=1,
                task_count=2,
                waves=waves,
            )
        assert fp.feature_id == "FEAT-001"
        assert fp.wave_count == 1
        assert fp.task_count == 2
        assert len(fp.waves) == 1

    def test_wave_count_ge_1(self) -> None:
        # ValidationError fires during field validation, before model_post_init,
        # so no DeprecationWarning is emitted.
        with pytest.raises(ValidationError):
            FeaturePlannedPayload(
                feature_id="FEAT-001",
                wave_count=0,
                task_count=1,
                waves=[],
            )

    def test_task_count_ge_1(self) -> None:
        with pytest.raises(ValidationError):
            FeaturePlannedPayload(
                feature_id="FEAT-001",
                wave_count=1,
                task_count=0,
                waves=[WaveSummary(wave_number=1, task_count=0, task_ids=[])],
            )

    def test_cross_field_len_waves_eq_wave_count(self) -> None:
        """len(waves) must equal wave_count."""
        waves = [WaveSummary(wave_number=1, task_count=1, task_ids=["T1"])]
        with pytest.raises(ValidationError, match="wave_count"):
            FeaturePlannedPayload(
                feature_id="FEAT-001",
                wave_count=2,
                task_count=1,
                waves=waves,
            )

    def test_extra_fields_ignored(self) -> None:
        waves = [WaveSummary(wave_number=1, task_count=1, task_ids=["T1"])]
        with pytest.warns(DeprecationWarning, match="deprecated"):
            fp = FeaturePlannedPayload(
                feature_id="FEAT-001",
                wave_count=1,
                task_count=1,
                waves=waves,
                unknown="x",
            )
        assert not hasattr(fp, "unknown")


# ---------------------------------------------------------------------------
# FeatureReadyForBuildPayload
# ---------------------------------------------------------------------------


class TestFeatureReadyForBuildPayload:
    """FeatureReadyForBuildPayload validation."""

    def test_valid_ready_for_build(self) -> None:
        fr = FeatureReadyForBuildPayload(
            feature_id="FEAT-001",
            spec_path="/specs/FEAT-001.yaml",
            plan_path="/plans/FEAT-001.md",
            pipeline_type="greenfield",
        )
        assert fr.feature_id == "FEAT-001"
        assert fr.spec_path == "/specs/FEAT-001.yaml"
        assert fr.plan_path == "/plans/FEAT-001.md"
        assert fr.pipeline_type == "greenfield"
        assert fr.source_commands == []

    def test_pipeline_type_literal(self) -> None:
        with pytest.raises(ValidationError):
            FeatureReadyForBuildPayload(
                feature_id="FEAT-001",
                spec_path="/specs/x.yaml",
                plan_path="/plans/x.md",
                pipeline_type="invalid",
            )

    def test_source_commands_custom(self) -> None:
        fr = FeatureReadyForBuildPayload(
            feature_id="FEAT-001",
            spec_path="/specs/x.yaml",
            plan_path="/plans/x.md",
            pipeline_type="existing",
            source_commands=["cmd1", "cmd2"],
        )
        assert fr.source_commands == ["cmd1", "cmd2"]

    def test_extra_fields_ignored(self) -> None:
        fr = FeatureReadyForBuildPayload(
            feature_id="FEAT-001",
            spec_path="/specs/x.yaml",
            plan_path="/plans/x.md",
            pipeline_type="greenfield",
            extra="ignored",
        )
        assert not hasattr(fr, "extra")


# ---------------------------------------------------------------------------
# BuildStartedPayload
# ---------------------------------------------------------------------------


class TestBuildStartedPayload:
    """BuildStartedPayload validation."""

    def test_valid_build_started(self) -> None:
        bs = BuildStartedPayload(
            feature_id="FEAT-001",
            build_id="build-FEAT-001-20260408120000",
            wave_total=3,
        )
        assert bs.feature_id == "FEAT-001"
        assert bs.build_id == "build-FEAT-001-20260408120000"
        assert bs.wave_total == 3

    def test_wave_total_ge_1(self) -> None:
        with pytest.raises(ValidationError):
            BuildStartedPayload(
                feature_id="FEAT-001",
                build_id="build-FEAT-001-20260408120000",
                wave_total=0,
            )

    def test_extra_fields_ignored(self) -> None:
        bs = BuildStartedPayload(
            feature_id="FEAT-001",
            build_id="build-FEAT-001-20260408120000",
            wave_total=1,
            extra="ignored",
        )
        assert not hasattr(bs, "extra")


# ---------------------------------------------------------------------------
# BuildProgressPayload
# ---------------------------------------------------------------------------


class TestBuildProgressPayload:
    """BuildProgressPayload validation including cross-field validator."""

    def test_valid_build_progress(self) -> None:
        bp = BuildProgressPayload(
            feature_id="FEAT-001",
            build_id="build-FEAT-001-20260408120000",
            wave=2,
            wave_total=3,
            overall_progress_pct=66.7,
            elapsed_seconds=120,
        )
        assert bp.wave == 2
        assert bp.wave_total == 3
        assert bp.overall_progress_pct == 66.7
        assert bp.elapsed_seconds == 120

    def test_wave_ge_1(self) -> None:
        with pytest.raises(ValidationError):
            BuildProgressPayload(
                feature_id="FEAT-001",
                build_id="build-x-20260408120000",
                wave=0,
                wave_total=1,
                overall_progress_pct=0.0,
                elapsed_seconds=0,
            )

    def test_wave_total_ge_1(self) -> None:
        with pytest.raises(ValidationError):
            BuildProgressPayload(
                feature_id="FEAT-001",
                build_id="build-x-20260408120000",
                wave=1,
                wave_total=0,
                overall_progress_pct=0.0,
                elapsed_seconds=0,
            )

    def test_cross_field_wave_le_wave_total(self) -> None:
        """wave must be <= wave_total."""
        with pytest.raises(ValidationError, match="wave"):
            BuildProgressPayload(
                feature_id="FEAT-001",
                build_id="build-x-20260408120000",
                wave=4,
                wave_total=3,
                overall_progress_pct=50.0,
                elapsed_seconds=60,
            )

    def test_progress_pct_lower_bound(self) -> None:
        with pytest.raises(ValidationError):
            BuildProgressPayload(
                feature_id="FEAT-001",
                build_id="build-x-20260408120000",
                wave=1,
                wave_total=1,
                overall_progress_pct=-1.0,
                elapsed_seconds=0,
            )

    def test_progress_pct_upper_bound(self) -> None:
        with pytest.raises(ValidationError):
            BuildProgressPayload(
                feature_id="FEAT-001",
                build_id="build-x-20260408120000",
                wave=1,
                wave_total=1,
                overall_progress_pct=100.1,
                elapsed_seconds=0,
            )

    def test_elapsed_seconds_ge_0(self) -> None:
        with pytest.raises(ValidationError):
            BuildProgressPayload(
                feature_id="FEAT-001",
                build_id="build-x-20260408120000",
                wave=1,
                wave_total=1,
                overall_progress_pct=0.0,
                elapsed_seconds=-1,
            )

    def test_extra_fields_ignored(self) -> None:
        bp = BuildProgressPayload(
            feature_id="FEAT-001",
            build_id="build-x-20260408120000",
            wave=1,
            wave_total=1,
            overall_progress_pct=0.0,
            elapsed_seconds=0,
            extra="ignored",
        )
        assert not hasattr(bp, "extra")


# ---------------------------------------------------------------------------
# BuildCompletePayload
# ---------------------------------------------------------------------------


class TestBuildCompletePayload:
    """BuildCompletePayload validation including cross-field validator."""

    def test_valid_build_complete(self) -> None:
        bc = BuildCompletePayload(
            feature_id="FEAT-001",
            build_id="build-FEAT-001-20260408120000",
            tasks_completed=5,
            tasks_failed=0,
            tasks_total=5,
            duration_seconds=300,
            summary="All tasks completed successfully",
        )
        assert bc.tasks_completed == 5
        assert bc.tasks_failed == 0
        assert bc.tasks_total == 5
        assert bc.pr_url is None
        assert bc.duration_seconds == 300
        assert bc.summary == "All tasks completed successfully"

    def test_pr_url_optional(self) -> None:
        bc = BuildCompletePayload(
            feature_id="FEAT-001",
            build_id="build-FEAT-001-20260408120000",
            tasks_completed=3,
            tasks_failed=2,
            tasks_total=5,
            pr_url="https://github.com/org/repo/pull/42",
            duration_seconds=600,
            summary="Build complete with failures",
        )
        assert bc.pr_url == "https://github.com/org/repo/pull/42"

    def test_cross_field_tasks_sum_eq_total(self) -> None:
        """tasks_completed + tasks_failed must equal tasks_total."""
        with pytest.raises(ValidationError, match="tasks_total"):
            BuildCompletePayload(
                feature_id="FEAT-001",
                build_id="build-FEAT-001-20260408120000",
                tasks_completed=3,
                tasks_failed=1,
                tasks_total=5,
                duration_seconds=300,
                summary="Mismatch",
            )

    def test_tasks_total_ge_1(self) -> None:
        with pytest.raises(ValidationError):
            BuildCompletePayload(
                feature_id="FEAT-001",
                build_id="build-FEAT-001-20260408120000",
                tasks_completed=0,
                tasks_failed=0,
                tasks_total=0,
                duration_seconds=0,
                summary="Zero total",
            )

    def test_tasks_completed_ge_0(self) -> None:
        with pytest.raises(ValidationError):
            BuildCompletePayload(
                feature_id="FEAT-001",
                build_id="build-FEAT-001-20260408120000",
                tasks_completed=-1,
                tasks_failed=1,
                tasks_total=0,
                duration_seconds=0,
                summary="Negative completed",
            )

    def test_duration_seconds_ge_0(self) -> None:
        with pytest.raises(ValidationError):
            BuildCompletePayload(
                feature_id="FEAT-001",
                build_id="build-FEAT-001-20260408120000",
                tasks_completed=1,
                tasks_failed=0,
                tasks_total=1,
                duration_seconds=-1,
                summary="Negative duration",
            )

    def test_extra_fields_ignored(self) -> None:
        bc = BuildCompletePayload(
            feature_id="FEAT-001",
            build_id="build-FEAT-001-20260408120000",
            tasks_completed=1,
            tasks_failed=0,
            tasks_total=1,
            duration_seconds=10,
            summary="Done",
            extra="ignored",
        )
        assert not hasattr(bc, "extra")


# ---------------------------------------------------------------------------
# BuildFailedPayload
# ---------------------------------------------------------------------------


class TestBuildFailedPayload:
    """BuildFailedPayload validation."""

    def test_valid_build_failed(self) -> None:
        bf = BuildFailedPayload(
            feature_id="FEAT-001",
            build_id="build-FEAT-001-20260408120000",
            failure_reason="Timeout exceeded",
            recoverable=True,
        )
        assert bf.feature_id == "FEAT-001"
        assert bf.failure_reason == "Timeout exceeded"
        assert bf.recoverable is True
        assert bf.failed_task_id is None

    def test_failed_task_id_optional(self) -> None:
        bf = BuildFailedPayload(
            feature_id="FEAT-001",
            build_id="build-FEAT-001-20260408120000",
            failure_reason="Task crashed",
            recoverable=False,
            failed_task_id="TASK-007",
        )
        assert bf.failed_task_id == "TASK-007"

    def test_extra_fields_ignored(self) -> None:
        bf = BuildFailedPayload(
            feature_id="FEAT-001",
            build_id="build-FEAT-001-20260408120000",
            failure_reason="Error",
            recoverable=False,
            extra="ignored",
        )
        assert not hasattr(bf, "extra")
