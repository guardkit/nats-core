---
id: TASK-A3EB
title: "Scaffold NATSConfig module and add pydantic-settings dependency"
status: pending
task_type: scaffolding
parent_review: TASK-F7AE
feature_id: FEAT-NC
wave: 1
implementation_mode: direct
complexity: 2
dependencies: []
priority: high
tags: [nats-configuration, scaffolding, pydantic-settings]
---

# Task: Scaffold NATSConfig module and add pydantic-settings dependency

## Description

Add `pydantic-settings` to `pyproject.toml` and create the `src/nats_core/config.py`
skeleton module. This is a greenfield module within the existing project structure
(established by TASK-ME01). No implementation logic yet — skeleton only.

## Acceptance Criteria

- [ ] `pyproject.toml` updated: `pydantic-settings>=2.0` added to `[project.dependencies]`
- [ ] `src/nats_core/config.py` created with:
  - `from __future__ import annotations` at top
  - `NATSConfig` class stub inheriting `BaseSettings` from `pydantic_settings`
  - Google-style module docstring
  - Empty `model_config = SettingsConfigDict(env_prefix="NATS_", env_file=".env")`
- [ ] `src/nats_core/__init__.py` exports `NATSConfig`
- [ ] `pip install -e ".[dev]"` succeeds after adding dependency
- [ ] `ruff check .` passes with zero errors
- [ ] `mypy src/` passes with zero errors on the skeleton

## Implementation Notes

- Use `pydantic_settings.BaseSettings` and `pydantic_settings.SettingsConfigDict`
- Do NOT add any fields or validators — that is TASK-A500 and TASK-83F5
- `env_file=".env"` enables dotenv loading by pydantic-settings default behaviour
- Include `from __future__ import annotations` in all new .py files
- Do not add `py.typed` if it already exists (created by TASK-ME01)
