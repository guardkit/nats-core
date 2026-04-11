---
id: TASK-A500
title: Implement NATSConfig core connection fields
status: completed
task_type: declarative
parent_review: TASK-F7AE
feature_id: FEAT-NC
wave: 2
implementation_mode: task-work
complexity: 3
dependencies:
- TASK-A3EB
priority: high
tags:
- nats-configuration
- pydantic-settings
- fields
autobuild_state:
  current_turn: 1
  max_turns: 30
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/nats-core/.guardkit/worktrees/FEAT-DD0E
  base_branch: main
  started_at: '2026-04-08T21:16:59.916905'
  last_updated: '2026-04-08T21:21:25.378974'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-04-08T21:16:59.916905'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
completed: '2026-04-11T00:00:00+00:00'
completed_location: tasks/completed/nats-configuration/
---

# Task: Implement NATSConfig core connection fields

## Description

Add the five core connection fields to `NATSConfig` with their default values,
`Field(description=...)` metadata, and numeric bound constraints. Implement the
URL scheme validator (`nats://` or `tls://` only). Cover BDD scenarios: default
config, URL env-var override, constructor override, zero-value boundary cases,
negative-value rejection, invalid/empty URL rejection, and empty client name rejection.

## Acceptance Criteria

- [ ] `url: str` — default `"nats://localhost:4222"`, bound to `NATS_URL`
- [ ] `connect_timeout: float` — default `5.0`, `ge=0.0`, bound to `NATS_CONNECT_TIMEOUT`
- [ ] `reconnect_time_wait: float` — default `2.0`, `ge=0.0`, bound to `NATS_RECONNECT_TIME_WAIT`
- [ ] `max_reconnect_attempts: int` — default `60`, `ge=0`, bound to `NATS_MAX_RECONNECT_ATTEMPTS`
- [ ] `name: str` — default `"nats-core-client"`, `min_length=1`, bound to `NATS_NAME`
- [ ] `@field_validator("url")` rejects scheme other than `nats://` or `tls://`
- [ ] `@field_validator("url")` rejects empty string
- [ ] `@field_validator("name")` rejects blank/empty string
- [ ] All fields carry `Field(description=...)` per project model pattern
- [ ] All modified files pass project-configured lint/format checks with zero errors

## BDD Scenarios Covered

From `features/nats-configuration/nats-configuration.feature`:
- `Scenario: Default configuration connects to localhost` (@smoke)
- `Scenario: Environment variable overrides the default URL` (@smoke)
- `Scenario: Constructor arguments override defaults`
- `Scenario: Connect timeout at zero is accepted`
- `Scenario: Negative connect timeout is rejected`
- `Scenario: Reconnect time wait at zero is accepted`
- `Scenario: Negative reconnect time wait is rejected`
- `Scenario: Max reconnect attempts at zero means no retries`
- `Scenario: Negative max reconnect attempts is rejected`
- `Scenario: Invalid URL scheme is rejected`
- `Scenario: Empty URL is rejected`
- `Scenario: Empty client name is rejected`

## Implementation Notes

- Use `pydantic.field_validator` with `@classmethod`; raise `ValueError` with descriptive message
- URL scheme check: `parsed = urllib.parse.urlparse(v); assert parsed.scheme in ("nats", "tls")`
- `ge=0.0` / `ge=0` are Pydantic Field constraints — do not use `@field_validator` for these
- All fields must be compatible with mypy strict mode
