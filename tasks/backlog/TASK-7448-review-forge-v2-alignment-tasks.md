---
id: TASK-7448
title: Review forge-v2-alignment tasks for correctness and regression safety
status: review_complete
task_type: review
review_mode: architectural
review_depth: standard
created: 2026-04-16T00:00:00Z
updated: 2026-04-16T00:00:00Z
priority: high
tags: [review, forge-v2.2, nats-core, payloads, topics, regression-safety, anchor]
complexity: 5
decision_required: true
review_results:
  score: 78
  findings_count: 9
  recommendations_count: 7
  decision: proceed_with_modifications
  completed_at: 2026-04-16
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Review forge-v2-alignment tasks for correctness and regression safety

## Context

The alignment review (`forge/docs/research/forge-build-plan-alignment-review.md`) audited the forge anchor v2.2 against four sibling repos and produced a comprehensive correction list. From that review, two implementation tasks were created in `tasks/backlog/forge-v2-alignment/`:

- **TASK-NCFA-001** — Add five new pipeline payloads (`BuildQueued`, `BuildPaused`, `BuildResumed`, `StageComplete`, `StageGated`), six new topic constants, and deprecate `FeaturePlannedPayload`
- **TASK-NCFA-002** — Integration tests for the new payloads against live NATS on GB10

These tasks are derived from §2.1 of the alignment review (corrections 26–30) and the `IMPLEMENTATION-GUIDE.md` in the same directory.

## Purpose

Before implementation begins, independently verify that:

1. The proposed changes are **the correct approach** given the current state of `nats-core`
2. The changes **won't cause regressions** in the existing 98% test-covered codebase
3. The tasks represent **the correct way forward** for Forge v2.2 alignment

## Review scope

### 1. Payload design correctness

- [ ] Verify `BuildQueuedPayload` (Appendix C of alignment review) is compatible with existing `_pipeline.py` patterns (`BuildStartedPayload`, `BuildProgressPayload`, `BuildCompletePayload`, `BuildFailedPayload`)
- [ ] Verify the four sketch payloads in `IMPLEMENTATION-GUIDE.md` (`BuildPaused`, `BuildResumed`, `StageComplete`, `StageGated`) follow the same Pydantic conventions as existing payloads
- [ ] Check that `correlation_id: str` as a required field is consistent with existing payload patterns (existing payloads use `correlation_id` via `MessageEnvelope`, not as a direct payload field — assess whether this is a design divergence or intentional)
- [ ] Validate that `ConfigDict(extra='allow')` on `BuildQueuedPayload` is compatible with how `MessageEnvelope` wraps payloads today
- [ ] Assess whether `TriggerSource` and `OriginatingAdapter` Literal types belong in `_pipeline.py` or should be in a shared types module

### 2. Topic naming and registry

- [ ] Verify the six new topic constants (`BUILD_QUEUED`, `BUILD_PAUSED`, `BUILD_RESUMED`, `STAGE_COMPLETE`, `STAGE_GATED`, `COMMAND_BROADCAST`) follow the existing naming pattern in `topics.py`
- [ ] Confirm the `pipeline.build-queued.{feature_id}` subject pattern is compatible with the existing `PIPELINE` JetStream stream's subject filter
- [ ] Check that `agents.command.broadcast` doesn't conflict with wildcard subscriptions on `agents.command.>`

### 3. Deprecation strategy

- [ ] Verify the `FeaturePlannedPayload` deprecation approach (warning on use, docstring update, no deletion) is safe for existing consumers
- [ ] Check whether any code in `nats-core` itself imports or references `FeaturePlannedPayload` beyond the definition
- [ ] Confirm the topic `pipeline.feature-planned.{feature_id}` deprecation won't break existing subscribers (specialist-agent reference noted in the review)

### 4. Regression risk assessment

- [ ] Review the existing test suite structure to confirm new tests can be added without disrupting existing test discovery or fixtures
- [ ] Check that adding new exports to `__init__.py` won't cause circular import issues
- [ ] Verify that any payload registry or type mapping (if it exists) can accommodate the new entries without breaking existing lookups
- [ ] Assess whether the `FeaturePlannedPayload` deprecation warning will cause any existing tests to fail (e.g., tests that import it without `pytest.warns`)

### 5. Integration test feasibility (TASK-NCFA-002)

- [ ] Confirm the existing integration test infrastructure supports the proposed test patterns (live NATS fixtures, `@pytest.mark.integration`)
- [ ] Verify the proposed AckWait redelivery test is feasible with the current `nats-infrastructure` stream configuration
- [ ] Check that the wildcard subscription test (`pipeline.build-*.>`) is compatible with the PIPELINE stream's subject filter

### 6. Alignment with anchor v2.2

- [ ] Cross-reference the task scope against corrections 26–30 in the alignment review to confirm nothing was missed or mis-transcribed
- [ ] Verify the out-of-scope items are genuinely out of scope (particularly the `FeatureReadyForBuildPayload` deferral to TASK-FVD3)
- [ ] Confirm the singular topic convention (ADR-SP-016) is correctly applied throughout

## Decision points

After the review, decide on each:

1. **Proceed as-is** — Tasks are correct, no changes needed
2. **Proceed with modifications** — Tasks are mostly correct but need specific adjustments (list them)
3. **Revise significantly** — Tasks have fundamental issues that need reworking before implementation
4. **Block** — Tasks should not proceed until upstream decisions are made

## Source documents

- Alignment review: `forge/docs/research/forge-build-plan-alignment-review.md`
- Task README: `tasks/backlog/forge-v2-alignment/README.md`
- TASK-NCFA-001: `tasks/backlog/forge-v2-alignment/TASK-NCFA-001-add-pipeline-payloads.md`
- TASK-NCFA-002: `tasks/backlog/forge-v2-alignment/TASK-NCFA-002-integration-tests-new-payloads.md`
- Implementation guide: `tasks/backlog/forge-v2-alignment/IMPLEMENTATION-GUIDE.md`
- Current pipeline events: `src/nats_core/events/_pipeline.py`
- Current topics: `src/nats_core/topics.py`
- Current public API: `src/nats_core/__init__.py`

## Acceptance criteria

- [ ] All six review sections above completed with findings documented
- [ ] Each decision point has a clear recommendation with justification
- [ ] Any regression risks identified with specific mitigation steps
- [ ] Any missing scope or incorrect assumptions flagged

## Implementation Notes — Review Findings (2026-04-16)

### Verdict: PROCEED WITH MODIFICATIONS (78/100)

Tasks are architecturally sound. Three modifications applied to task files before implementation:

**MUST fixes (applied):**
1. **EventType/registry gap** — TASK-NCFA-001 now includes scope item for `EventType` enum additions and `_EVENT_TYPE_REGISTRY` updates in `envelope.py`. Out-of-scope clarified to distinguish schema changes from registry additions.
2. **Deprecation mechanism** — TASK-NCFA-001 and IMPLEMENTATION-GUIDE.md corrected to use `model_post_init` instead of `__init_subclass__` or module-level import. Existing test update scope added.
3. **`extra='allow'` consistency** — All five new payloads now specified with `ConfigDict(extra="allow")` for forward compatibility. IMPLEMENTATION-GUIDE.md sketches updated with `model_config`, `Field(description=...)`, and `float | None` style.

**SHOULD fixes (applied):**
4. **Test deprecation noise** — TASK-NCFA-001 scope now includes updating existing tests with `pytest.warns(DeprecationWarning)`.
5. **Live NATS fixtures** — TASK-NCFA-002 updated to note that live fixtures must be created from scratch (existing integration tests use AsyncMock).

**COULD items (not applied, left as notes):**
6. Dual-level `correlation_id` documentation — implementer should add code comment
7. `ALL_STAGES` wildcard constant — consider adding for stage event subscriptions

### Key observations
- 114 existing pipeline/event tests pass (0.08s)
- No `agents.commands.` (plural) references in codebase
- No `filterwarnings` configured in pyproject.toml
- `Topics.Pipeline.ALL_BUILDS` wildcard correctly excludes stage events
- `agents.command.broadcast` compatible with existing wildcard subscriptions

## Test Execution Log

```
$ pytest tests/test_pipeline_payloads.py tests/test_event_type_schemas.py -v --tb=short -q
114 passed in 0.08s (baseline verified 2026-04-16)
```
