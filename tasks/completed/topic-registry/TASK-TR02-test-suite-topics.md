---
id: TASK-TR02
title: "Test suite \u2014 Topic Registry (32 BDD scenarios)"
status: completed
task_type: testing
parent_review: TASK-TR00
feature_id: FEAT-TR
wave: 2
implementation_mode: task-work
complexity: 4
dependencies:
- TASK-TR01
priority: high
tags:
- topic-registry
- testing
- bdd
consumer_context:
- task: TASK-TR01
  consumes: nats_core.topics
  framework: pytest with asyncio_mode=auto
  driver: pytest
  format_note: Module must be importable as `from nats_core.topics import Topics`
    after `pip install -e '.[dev]'`; Topics class must expose Pipeline, Agents, Fleet,
    Jarvis, System as inner classes with string constants
autobuild_state:
  current_turn: 1
  max_turns: 30
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/nats-core/.guardkit/worktrees/FEAT-DCBD
  base_branch: main
  started_at: '2026-04-08T20:51:35.475069'
  last_updated: '2026-04-08T20:58:51.290124'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-04-08T20:51:35.475069'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
completed: '2026-04-11T00:00:00+00:00'
completed_location: tasks/completed/topic-registry/
---

# Task: Test suite — Topic Registry (32 BDD scenarios)

## Description

Implement `tests/test_topics.py` covering all 32 BDD scenarios from `features/topic-registry/topic-registry.feature`. Uses the factory function pattern from `tests/conftest.py`. Depends on TASK-TR01 (`topics.py` must exist and be importable).

## Acceptance Criteria

- [ ] `tests/test_topics.py` created with `from __future__ import annotations`
- [ ] All 32 BDD scenarios covered (see spec for full list):
  - **@key-example (8)**: Core resolution scenarios for Pipeline, Agents, Fleet, Jarvis; project scoping; wildcards; tool invocation; approval topics
  - **@boundary (6)**: Minimal-length IDs, hyphens/numbers in IDs, wildcard suffix correctness (Scenario Outline ×6 examples)
  - **@negative (5)**: Empty ID, dots in ID, spaces in ID, missing template var, extra template var, empty project name, dots in project name, wildcards in ID
  - **@edge-case (13)**: EventType sync (pipeline + agents), no hardcoded strings outside registry, resolve+scope composition, wildcard project scoping, valid NATS subject chars (Scenario Outline ×11 examples), no instantiation required, approval response extends request, control chars rejected, shell metacharacters rejected, immutability, all 5 namespaces present, idempotency
- [ ] `@smoke` marker applied to the 8 smoke scenarios (matches `@smoke` tags in .feature file)
- [ ] `@seam` marker applied to the integration contract seam test (see Seam Tests section)
- [ ] Factory functions added/extended in `tests/conftest.py` as needed
- [ ] All tests pass: `pytest tests/test_topics.py -v`
- [ ] Smoke gate passes: `pytest tests/test_topics.py -m smoke -v` (8 tests)
- [ ] Coverage on `topics.py` >= 95%: `pytest --cov=nats_core.topics --cov-report=term-missing`

## Seam Tests

The following seam test validates the integration contract with TASK-TR01. Implement this test to verify the boundary before integration.

```python
"""Seam test: verify nats_core.topics contract from TASK-TR01."""
import pytest


@pytest.mark.seam
@pytest.mark.integration_contract("nats_core.topics")
def test_nats_core_topics_importable():
    """Verify nats_core.topics module matches the expected interface.

    Contract: Module must be importable as `from nats_core.topics import Topics`
    after `pip install -e '.[dev]'`; Topics class must expose Pipeline, Agents,
    Fleet, Jarvis, System as inner classes with string constants.
    Producer: TASK-TR01
    """
    from nats_core.topics import Topics  # noqa: PLC0415

    # Module is importable
    assert Topics is not None, "Topics class must be importable"

    # All 5 namespaces present
    for ns in ("Pipeline", "Agents", "Fleet", "Jarvis", "System"):
        assert hasattr(Topics, ns), f"Topics must have {ns} namespace"

    # Constants are strings (not None, not instances)
    assert isinstance(Topics.Pipeline.BUILD_STARTED, str)
    assert isinstance(Topics.Fleet.REGISTER, str)
```

## Implementation Notes

### Factory Functions (conftest.py)

Add helpers for creating test inputs:

```python
# conftest.py additions for topic-registry tests
def make_valid_feature_id(**overrides: str) -> str:
    return overrides.get("feature_id", "FEAT-001")

def make_valid_agent_id(**overrides: str) -> str:
    return overrides.get("agent_id", "guardkit-factory")
```

### Test Structure

Group tests by BDD category using markers or classes:

```python
class TestKeyExamples:
    """@key-example @smoke scenarios."""

    @pytest.mark.smoke
    def test_resolve_pipeline_build_started_with_feature_id(self): ...

    @pytest.mark.smoke
    def test_resolve_agent_status_with_agent_id(self): ...
    ...

class TestBoundaryConditions:
    """@boundary scenarios."""
    ...

class TestNegativeCases:
    """@negative scenarios."""
    ...

class TestEdgeCases:
    """@edge-case scenarios."""
    ...
```

### EventType Sync Test

```python
def test_pipeline_topics_correspond_to_event_types():
    """Every non-wildcard Pipeline topic template has a matching EventType."""
    from nats_core.envelope import EventType  # or wherever EventType lives

    pipeline_templates = [
        v for k, v in vars(Topics.Pipeline).items()
        if not k.startswith("_") and isinstance(v, str) and ">" not in v and "*" not in v
    ]
    event_type_values = {e.value for e in EventType}
    for template in pipeline_templates:
        # Extract the base subject (first segment after "pipeline.")
        # Match to EventType value e.g. "pipeline.build-started.{feature_id}" → "build-started"
        ...
```

### Hardcoded String Test

```python
def test_no_hardcoded_topic_strings_outside_registry():
    """No file outside topics.py should contain hardcoded topic strings."""
    import subprocess
    result = subprocess.run(
        ["grep", "-r", "pipeline.build-", "src/", "--include=*.py",
         "--exclude=topics.py"],
        capture_output=True, text=True
    )
    assert result.stdout == "", f"Hardcoded topic strings found:\n{result.stdout}"
```

## Coach Validation Commands

```bash
pytest tests/test_topics.py -v
pytest tests/test_topics.py -m smoke -v
pytest tests/test_topics.py --cov=nats_core.topics --cov-report=term-missing
ruff check tests/test_topics.py
mypy tests/test_topics.py
```
