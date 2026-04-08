---
complexity: 3
dependencies:
- TASK-B725
feature_id: FEAT-NC
id: TASK-132C
implementation_mode: task-work
parent_review: TASK-F7AE
priority: high
status: design_approved
tags:
- nats-configuration
- testing
- pytest
task_type: testing
title: Create NATSConfig test suite
wave: 5
---

# Task: Create NATSConfig test suite

## Description

Create `tests/test_config.py` covering all 23 BDD scenarios from
`features/nats-configuration/nats-configuration.feature`. Use the factory function
pattern from `tests/conftest.py` and `monkeypatch.setenv` / `tmp_path` for
environment and .env file scenarios. Mark smoke scenarios with `@pytest.mark.smoke`.

## Acceptance Criteria

- [ ] `tests/test_config.py` created
- [ ] `make_nats_config(**overrides)` factory function in `tests/conftest.py`
- [ ] All 23 BDD scenarios covered with individual test functions
- [ ] 2 smoke scenarios marked `@pytest.mark.smoke` matching `.feature` @smoke tags
- [ ] `@pytest.mark.integration` on the nats-py connect acceptance test
- [ ] `pytest tests/test_config.py -v` passes with all tests green (excluding integration)
- [ ] `pytest tests/test_config.py -m smoke -v` passes (CI gate)
- [ ] `mypy tests/test_config.py` passes in strict mode
- [ ] `ruff check tests/test_config.py` passes with zero errors

## BDD Scenario → Test Function Mapping

| BDD Scenario | Test Function |
|---|---|
| Default configuration connects to localhost | `test_default_url` |
| Environment variable overrides default URL | `test_env_url_override` |
| Configuring user and password from environment | `test_env_user_password` |
| Configuring NKey credentials file | `test_env_creds_file` |
| Constructor arguments override defaults | `test_constructor_override` |
| Connect timeout at zero is accepted | `test_connect_timeout_zero` |
| Negative connect timeout is rejected | `test_connect_timeout_negative` |
| Reconnect time wait at zero is accepted | `test_reconnect_time_wait_zero` |
| Negative reconnect time wait is rejected | `test_reconnect_time_wait_negative` |
| Max reconnect attempts at zero | `test_max_reconnect_attempts_zero` |
| Negative max reconnect attempts is rejected | `test_max_reconnect_attempts_negative` |
| Invalid URL scheme is rejected | `test_invalid_url_scheme` |
| Empty URL is rejected | `test_empty_url` |
| Empty client name is rejected | `test_empty_name` |
| User without password is rejected | `test_user_without_password` |
| Environment variable precedence over defaults | `test_env_precedence` |
| Multiple NATSConfig instances are independent | `test_instances_independent` |
| Configuration loads from dotenv file | `test_dotenv_loading` |
| Sensitive fields masked in string representation | `test_password_masked_repr` |
| Password not exposed when serialised to dict | `test_password_masked_model_dump` |
| Creds file with path traversal is rejected | `test_creds_file_path_traversal` |
| Config produces valid nats-py connection kwargs | `test_to_connect_kwargs` *(integration)* |
| Providing both password auth and creds file is rejected | `test_password_and_creds_mutually_exclusive` |

## Implementation Notes

- Use `monkeypatch.setenv("NATS_URL", ...)` for env-var tests — never set `os.environ` directly
- For `.env` file test: write `NATS_URL=nats://dotenv-server:4222` to `tmp_path / ".env"`, then pass `_env_file=tmp_path / ".env"` to `NATSConfig()`
- `pydantic-settings` v2: constructor accepts `_env_file` kwarg to override dotenv path
- For `test_instances_independent`: pydantic BaseSettings instances are independent by construction — verify by creating two instances and checking `id()` or field identity
- Factory: `def make_nats_config(**overrides: Any) -> NATSConfig` — use `NATSConfig.model_validate(overrides)` or construct directly
- `from __future__ import annotations` at top of test file