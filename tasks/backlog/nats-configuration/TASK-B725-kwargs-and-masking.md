---
id: TASK-B725
title: "Implement to_connect_kwargs() and serialisation masking"
status: pending
task_type: feature
parent_review: TASK-F7AE
feature_id: FEAT-NC
wave: 4
implementation_mode: task-work
complexity: 3
dependencies: [TASK-83F5]
priority: high
tags: [nats-configuration, kwargs, masking]
---

# Task: Implement to_connect_kwargs() and serialisation masking

## Description

Implement `to_connect_kwargs() -> dict[str, Any]` which maps `NATSConfig` fields
to the keyword arguments accepted by nats-py's `Client.connect()`. Verify that
`password` (as `SecretStr`) is correctly excluded or masked when the config is
serialised to a dict (`model_dump`) — relying on pydantic's built-in `SecretStr`
serialisation behaviour. Ensure repr output does not expose raw secrets.

## Acceptance Criteria

- [ ] `to_connect_kwargs() -> dict[str, Any]` method added to `NATSConfig`
  - Returns `{"servers": [self.url], "connect_timeout": self.connect_timeout, "reconnect_time_wait": self.reconnect_time_wait, "max_reconnect_attempts": self.max_reconnect_attempts, "name": self.name}`
  - Includes `"user": self.user, "password": self.password.get_secret_value()` when both are set
  - Includes `"credentials": self.creds_file` when creds_file is set
- [ ] `model_dump()` does not expose raw password string — `SecretStr` serialises as `"**********"` by default in pydantic v2
- [ ] `repr(config)` / `str(config)` does not expose raw password value
- [ ] `to_connect_kwargs()` output is accepted by nats-py `Client.connect(**kwargs)` (verified in integration test)
- [ ] All modified files pass project-configured lint/format checks with zero errors

## BDD Scenarios Covered

From `features/nats-configuration/nats-configuration.feature`:
- `Scenario: Sensitive fields are masked in string representation` (@edge-case)
- `Scenario: Password is not exposed when config is serialised to dict` (@edge-case)
- `Scenario: Config produces valid nats-py connection kwargs` (@edge-case)

## Implementation Notes

- `pydantic.SecretStr` in pydantic v2 serialises as `SecretStr('**********')` in repr and `"**********"` in `model_dump(mode="python")`
- To get raw value for nats-py: `self.password.get_secret_value()` — only call this inside `to_connect_kwargs()`
- The `servers` field must be a list (nats-py accepts a single URL or list)
- Type annotation: `from typing import Any` required in config.py
- Integration test for nats-py acceptance is `@pytest.mark.integration` — mark it to be skipped in unit test suite
