---
id: TASK-A3EB
title: Scaffold NATSConfig module and add pydantic-settings dependency
status: in_review
task_type: scaffolding
parent_review: TASK-F7AE
feature_id: FEAT-NC
wave: 1
implementation_mode: direct
complexity: 2
dependencies: []
priority: high
tags:
- nats-configuration
- scaffolding
- pydantic-settings
autobuild_state:
  current_turn: 1
  max_turns: 30
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/nats-core/.guardkit/worktrees/FEAT-DD0E
  base_branch: main
  started_at: '2026-04-08T21:13:17.914365'
  last_updated: '2026-04-08T21:16:56.431239'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-04-08T21:13:17.914365'
    player_summary: Scaffolded NATSConfig module with pydantic-settings BaseSettings.
      Added pydantic-settings>=2.0 to pyproject.toml dependencies. Created src/nats_core/config.py
      with NATSConfig class inheriting BaseSettings, configured with env_prefix='NATS_'
      and env_file='.env'. Updated __init__.py to import and re-export NATSConfig
      in __all__. Wrote 8 tests covering inheritance, instantiation, model_config,
      public export, import from package, __all__ membership, future annotations,
      and module docstring.
    player_success: true
    coach_success: true
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
