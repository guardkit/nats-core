---
id: TASK-83F5
title: Implement auth fields and mutual-exclusivity validators
status: in_review
task_type: feature
parent_review: TASK-F7AE
feature_id: FEAT-NC
wave: 3
implementation_mode: task-work
complexity: 4
dependencies:
- TASK-A500
priority: high
tags:
- nats-configuration
- auth
- validators
autobuild_state:
  current_turn: 1
  max_turns: 30
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/nats-core/.guardkit/worktrees/FEAT-DD0E
  base_branch: main
  started_at: '2026-04-08T21:21:25.397354'
  last_updated: '2026-04-08T21:26:51.525539'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-04-08T21:21:25.397354'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
---

# Task: Implement auth fields and mutual-exclusivity validators

## Description

Add authentication fields (`user`, `password`, `creds_file`) to `NATSConfig` and
implement the three auth validation rules: (1) user and password must be provided
together, (2) password auth and creds_file are mutually exclusive, (3) creds_file
path must not contain directory traversal (`..`). Uses `@model_validator(mode="after")`
for cross-field rules.

## Acceptance Criteria

- [ ] `user: str | None` — default `None`, bound to `NATS_USER`
- [ ] `password: pydantic.SecretStr | None` — default `None`, bound to `NATS_PASSWORD`
- [ ] `creds_file: str | None` — default `None`, bound to `NATS_CREDS_FILE`
- [ ] `@model_validator(mode="after")` raises `ValueError` when `user` is set without `password` (or vice versa)
- [ ] `@model_validator(mode="after")` raises `ValueError` when both `password` and `creds_file` are set
- [ ] `@field_validator("creds_file")` raises `ValueError` when path contains `..`
- [ ] All auth fields carry `Field(description=...)` metadata
- [ ] All modified files pass project-configured lint/format checks with zero errors

## BDD Scenarios Covered

From `features/nats-configuration/nats-configuration.feature`:
- `Scenario: Configuring user and password authentication from environment` (@key-example)
- `Scenario: Configuring NKey credentials file from environment` (@key-example)
- `Scenario: User without password is rejected` (@negative)
- `Scenario: Providing both password auth and creds file is rejected` (@edge-case @negative)
- `Scenario: Creds file with path traversal is rejected` (@edge-case @negative)

## Implementation Notes

- `pydantic.SecretStr` automatically masks `password` in `__repr__` and `model_dump` — no manual masking needed here
- `@model_validator(mode="after")` receives the fully-constructed model instance; access fields as `self.user`, `self.password`, etc.
- For `password` check in cross-field validator: `self.password is not None` (SecretStr is truthy even with empty secret — use `is not None`)
- creds_file path traversal: `".." in pathlib.PurePosixPath(v).parts`
- mypy strict: return type of `@model_validator(mode="after")` is `Self`
