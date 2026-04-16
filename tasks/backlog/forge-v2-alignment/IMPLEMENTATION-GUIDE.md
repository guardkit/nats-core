# Implementation Guide — nats-core Forge v2.2 Alignment

## Authoritative spec

The full Pydantic model for `BuildQueuedPayload` — the most important new payload — is specified in **Appendix C** of the alignment review:

`forge/docs/research/forge-build-plan-alignment-review.md` → Appendix C "BuildQueuedPayload full design (Jarvis-aware)"

That appendix contains the exact field list, validators, literal types, example payloads for CLI and Jarvis voice triggers, and the list of tests to add. Copy it across. Do not re-derive.

The other four payloads (`BuildPausedPayload`, `BuildResumedPayload`, `StageCompletePayload`, `StageGatedPayload`) are sketched in anchor v2.2 §7. Model them in the same Pydantic style, mirroring the existing `BuildStartedPayload` / `BuildProgressPayload` / `BuildCompletePayload` / `BuildFailedPayload` patterns in `src/nats_core/events/_pipeline.py`.

**Forward-compatibility decision (TASK-7448 review):** All five new payloads use `ConfigDict(extra="allow")` for forward compatibility with future publishers. This is a deliberate v2.2 divergence from the existing `extra="ignore"` convention (ADR-002). Each sketch below should include `model_config = ConfigDict(extra="allow")`.

## Suggested payload fields (for the four sketch-only ones)

```python
class BuildPausedPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    feature_id: str = Field(description="Unique identifier for the feature")
    build_id: str = Field(description="Build identifier")
    stage: str = Field(description="Pipeline stage that triggered the pause")
    coach_score: float = Field(description="Coach quality score that triggered the gate")
    threshold: float = Field(description="Minimum score threshold for this gate")
    gate_mode: Literal["flag_for_review", "hard_stop"] = Field(description="Gate enforcement mode")
    details: str = Field(description="Human-readable explanation of why the build was paused")
    correlation_id: str = Field(description="Correlates this event with other build lifecycle events")
    paused_at: datetime = Field(description="UTC timestamp when the build was paused")

class BuildResumedPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    feature_id: str = Field(description="Unique identifier for the feature")
    build_id: str = Field(description="Build identifier")
    stage: str = Field(description="Pipeline stage being resumed")
    resumed_by: str = Field(description="Identifier of the approver (e.g. 'rich')")
    decision: Literal["approve", "reject"] = Field(description="Approval decision")
    correlation_id: str = Field(description="Correlates this event with other build lifecycle events")
    resumed_at: datetime = Field(description="UTC timestamp when the build was resumed")

class StageCompletePayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    feature_id: str = Field(description="Unique identifier for the feature")
    build_id: str = Field(description="Build identifier")
    stage: str = Field(description="Pipeline stage that completed")
    status: Literal["passed", "failed", "gated", "skipped"] = Field(description="Stage outcome")
    coach_score: float | None = Field(default=None, description="Coach quality score, if applicable")
    duration_secs: float = Field(description="Stage duration in seconds")
    correlation_id: str = Field(description="Correlates this event with other build lifecycle events")
    completed_at: datetime = Field(description="UTC timestamp when the stage completed")

class StageGatedPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    feature_id: str = Field(description="Unique identifier for the feature")
    build_id: str = Field(description="Build identifier")
    stage: str = Field(description="Pipeline stage that was gated")
    gate_mode: Literal["flag_for_review", "hard_stop"] = Field(description="Gate enforcement mode")
    coach_score: float = Field(description="Coach quality score that triggered the gate")
    threshold: float = Field(description="Minimum score threshold for this gate")
    details: str = Field(description="Human-readable explanation of the gating decision")
    correlation_id: str = Field(description="Correlates this event with other build lifecycle events")
    gated_at: datetime = Field(description="UTC timestamp when the stage was gated")
```

Rationale for `correlation_id` on every event: threads a build's events together across stages and streams, enabling Jarvis to filter `pipeline.build-*.{feature_id}` by `correlation_id` and stream progress back to the originating adapter (ADR-SP-014).

## Test coverage target

Maintain ≥98% — current baseline per the alignment review.

## Deprecation of `FeaturePlannedPayload`

1. Add deprecation warning on **instantiation** using Pydantic's `model_post_init`:
   ```python
   def model_post_init(self, __context: Any) -> None:
       import warnings
       warnings.warn(
           "FeaturePlannedPayload is deprecated; use BuildQueuedPayload",
           DeprecationWarning,
           stacklevel=2,
       )
   ```
   Do NOT use `__init_subclass__` (fires on subclassing, not instantiation) or module-level `warnings.warn` (fires on every `import nats_core` since `envelope.py` imports it at the top level).
2. Do **not** delete in this task — removal is a semver-minor breaking change. File a follow-up to remove in `nats-core` v2.x.
3. Update `FeaturePlannedPayload`'s docstring to point at `BuildQueuedPayload`.
4. Leave `pipeline.feature-planned.{feature_id}` topic in place for now (it still has subscribers in `specialist-agent` per the audit); mark as deprecated in the docstring.

Coordinate with TASK-FVD3 in forge repo: if that task decides to fully retire `FeatureReadyForBuildPayload` as well, add a follow-up here.

## Graphiti seeding after completion

After TASK-NCFA-001 and TASK-NCFA-002 land, add a Graphiti episode to the `nats-core` project's `architecture_decisions` group noting:

> "nats-core v2.x adds BuildQueued/BuildPaused/BuildResumed/StageComplete/StageGated payloads and topics per forge anchor v2.2 ADR-SP-014/015/016/017. FeaturePlannedPayload deprecated. Singular agents.command.* convention is now fleet-wide canonical."
