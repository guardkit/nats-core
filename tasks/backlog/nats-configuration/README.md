# Feature: NATS Configuration (FEAT-NC)

**Module:** `src/nats_core/config.py`
**Tests:** `tests/test_config.py`
**Spec:** `features/nats-configuration/nats-configuration.feature` (23 scenarios)
**Review task:** TASK-F7AE
**Build order:** Feature 4 — independent, no dependencies

## Summary

Implements `NATSConfig`, a pydantic-settings `BaseSettings` subclass that manages
NATS connection parameters with environment variable overrides, field validation,
secret masking, and nats-py kwargs output.

## Tasks

| Task | Title | Type | Complexity |
|------|-------|------|-----------|
| [TASK-A3EB](TASK-A3EB-scaffold-natsconfig.md) | Scaffold NATSConfig module | scaffolding | 2 |
| [TASK-A500](TASK-A500-core-fields.md) | Core connection fields | declarative | 3 |
| [TASK-83F5](TASK-83F5-auth-validators.md) | Auth fields + validators | feature | 4 |
| [TASK-B725](TASK-B725-kwargs-and-masking.md) | kwargs output + masking | feature | 3 |
| [TASK-132C](TASK-132C-test-suite.md) | Test suite (23 scenarios) | testing | 3 |

## Quick Start

```bash
/task-work TASK-A3EB   # Scaffold
/task-work TASK-A500   # Core fields
/task-work TASK-83F5   # Auth validators
/task-work TASK-B725   # kwargs + masking
/task-work TASK-132C   # Tests
```

## Key Behaviours

- `NATS_URL`, `NATS_USER`, `NATS_PASSWORD`, `NATS_CREDS_FILE` env vars auto-bound
- `.env` file loaded by default (pydantic-settings)
- `password` field is `SecretStr` — masked in repr and `model_dump`
- user+password must be provided together; mutually exclusive with creds_file
- `to_connect_kwargs()` → nats-py `Client.connect(**kwargs)` compatible
