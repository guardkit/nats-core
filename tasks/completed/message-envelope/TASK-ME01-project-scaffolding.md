---
id: TASK-ME01
title: Create nats-core project scaffolding
status: completed
task_type: scaffolding
parent_review: TASK-40B8
feature_id: FEAT-ME
wave: 1
implementation_mode: direct
complexity: 3
dependencies: []
priority: high
tags:
- scaffolding
- project-setup
autobuild_state:
  current_turn: 1
  max_turns: 30
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/nats-core/.guardkit/worktrees/FEAT-2637
  base_branch: main
  started_at: '2026-04-08T19:25:28.669247'
  last_updated: '2026-04-08T19:30:30.925943'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-04-08T19:25:28.669247'
    player_summary: Created complete nats-core project scaffolding from scratch. Includes
      pyproject.toml with hatchling build system, all required tool configurations
      (ruff, mypy, pytest), src layout with nats_core package including version and
      docstring, PEP 561 py.typed marker, events sub-package, and test infrastructure
      with conftest.py factory function pattern. Virtual environment created with
      Python 3.12 and all dev dependencies installed. ruff check passes with zero
      errors, mypy src/ passes with zero errors i
    player_success: true
    coach_success: true
completed: '2026-04-11T00:00:00+00:00'
completed_location: tasks/completed/message-envelope/
---

# Task: Create nats-core project scaffolding

## Description

Set up the Python library project structure for nats-core using hatchling build system,
src layout, and all required tooling configuration. This is a greenfield project — no
existing files to migrate.

## Acceptance Criteria

- [ ] `pyproject.toml` created with hatchling build, project metadata, and dev dependencies
  - Python >= 3.10
  - Dependencies: pydantic >= 2.0
  - Dev dependencies: pytest, pytest-asyncio, ruff, mypy, build
  - ruff config: select = ["E", "F", "W", "I", "N", "UP"], line-length = 100
  - mypy config: strict = true
  - pytest config: asyncio_mode = "auto"
- [ ] `src/nats_core/__init__.py` created with module docstring and version
- [ ] `src/nats_core/py.typed` created (empty, PEP 561 marker)
- [ ] `src/nats_core/events/__init__.py` created (empty sub-package)
- [ ] `tests/__init__.py` created
- [ ] `tests/conftest.py` created with factory function pattern skeleton
- [ ] Project installs successfully with `pip install -e ".[dev]"`
- [ ] `ruff check .` passes with zero errors
- [ ] `mypy src/` passes with zero errors

## Implementation Notes

- Follow src layout: `src/nats_core/`
- Package name: `nats-core` (hyphenated), import name: `nats_core` (underscored)
- Include `from __future__ import annotations` in all .py files
- Use Google-style docstrings on public modules
- Do NOT implement any models or business logic — that is TASK-ME02
