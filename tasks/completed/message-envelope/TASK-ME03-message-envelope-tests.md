---
id: TASK-ME03
title: Implement MessageEnvelope test suite from BDD scenarios
status: completed
task_type: testing
parent_review: TASK-40B8
feature_id: FEAT-ME
wave: 2
implementation_mode: task-work
complexity: 4
dependencies:
- TASK-ME01
priority: high
tags:
- testing
- bdd
- envelope
autobuild_state:
  current_turn: 1
  max_turns: 30
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/nats-core/.guardkit/worktrees/FEAT-2637
  base_branch: main
  started_at: '2026-04-08T19:30:33.521111'
  last_updated: '2026-04-08T19:37:51.151280'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-04-08T19:30:33.521111'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
completed: '2026-04-11T00:00:00+00:00'
completed_location: tasks/completed/message-envelope/
---

# Task: Implement MessageEnvelope test suite from BDD scenarios

## Description

Implement the pytest test suite for MessageEnvelope and EventType based on the 23 BDD
scenarios defined in `features/message-envelope/message-envelope.feature`. Use the
conftest.py factory function pattern as specified in the project rules.

## Acceptance Criteria

- [ ] `tests/conftest.py` includes factory functions for creating test MessageEnvelope instances
  - `make_envelope(**overrides) -> MessageEnvelope` with sensible defaults
  - `make_envelope_json(**overrides) -> str` for JSON deserialisation tests
- [ ] `tests/test_envelope.py` implements all 23 BDD scenarios:
  - 4 smoke tests (@smoke): defaults, serialise, deserialise, unknown fields
  - 5 key-example tests (@key-example): defaults, serialise, deserialise, correlation, project scope
  - 6 boundary tests (@boundary): version, empty source_id, invalid event_type, optional None fields, empty payload, unique message_ids
  - 4 negative tests (@negative): unknown fields, missing source_id, missing event_type, missing payload
  - 8 edge-case tests (@edge-case): large payload, explicit overrides, future version, correlation chain, non-ASCII, concurrent creation, datetime payload, cross-version
- [ ] Tests use pytest markers matching BDD tags: `@pytest.mark.smoke`, `@pytest.mark.boundary`, `@pytest.mark.negative`, `@pytest.mark.edge_case`
- [ ] pytest marker configuration added to `pyproject.toml`
- [ ] All tests pass with `pytest tests/ -v`
- [ ] Test coverage for `envelope.py` >= 95%

## Implementation Notes

- Reference: `features/message-envelope/message-envelope.feature` for exact scenario definitions
- Reference: `features/message-envelope/message-envelope_assumptions.yaml` for confirmed assumptions
- Use factory function pattern (conftest.py), NOT fixtures with mutable state
- Use `@dataclass` for MockEnvelope if needed as test data holder
- For concurrent test (1000 envelopes): use `asyncio.gather` or `concurrent.futures`
- For the "within 1 second of now" assertion: compare with tolerance, not exact match
- Map BDD `@edge-case` tag to pytest `@pytest.mark.edge_case` (underscore, not hyphen)
