---
id: TASK-TR01
title: "Implement topics.py — Topic Registry"
status: pending
task_type: declarative
parent_review: TASK-TR00
feature_id: FEAT-TR
wave: 1
implementation_mode: task-work
complexity: 4
dependencies: []
priority: high
tags: [topic-registry, nats-subjects, declarative]
---

# Task: Implement topics.py — Topic Registry

## Description

Implement `src/nats_core/topics.py` — the single source of truth for all NATS subject strings in the fleet. This module provides typed string constants for five namespaces (Pipeline, Agents, Fleet, Jarvis, System), template resolution via `Topics.resolve()`, multi-tenancy project scoping via `Topics.for_project()`, and identifier validation.

No I/O, no async, no external dependencies beyond Python stdlib. Pure declarative module.

## Acceptance Criteria

- [ ] `src/nats_core/topics.py` created with `from __future__ import annotations`
- [ ] `Topics` outer class with five inner namespace classes: `Pipeline`, `Agents`, `Fleet`, `Jarvis`, `System`
- [ ] All topic constants defined per API contract (`docs/design/contracts/API-topic-registry.md`):
  - **Pipeline**: `FEATURE_PLANNED`, `FEATURE_READY_FOR_BUILD`, `BUILD_STARTED`, `BUILD_PROGRESS`, `BUILD_COMPLETE`, `BUILD_FAILED`, `ALL`, `ALL_BUILDS`
  - **Agents**: `STATUS`, `STATUS_ALL`, `APPROVAL_REQUEST`, `APPROVAL_RESPONSE`, `COMMAND`, `RESULT`, `TOOLS`, `TOOLS_ALL`
  - **Fleet**: `REGISTER`, `DEREGISTER`, `HEARTBEAT`, `HEARTBEAT_ALL`, `ALL`
  - **Jarvis**: `COMMAND`, `INTENT_CLASSIFIED`, `DISPATCH`, `NOTIFICATION`
  - **System**: `HEALTH`
- [ ] `Topics.resolve(template: str, **kwargs: str) -> str` implemented:
  - Substitutes `{placeholder}` tokens in template with provided kwargs
  - Raises `ValueError` if a required placeholder is missing
  - Raises `ValueError` if unexpected kwargs are provided
  - Raises `ValueError` if any kwarg value is empty, contains dots, spaces, `*`, `>`, or control characters
- [ ] `Topics.for_project(project: str, topic: str) -> str` implemented:
  - Returns `f"{project}.{topic}"`
  - Raises `ValueError` if `project` is empty, contains dots, spaces, `*`, `>`, or control characters
- [ ] `Topics.ALL_TOPICS: list[str]` — all non-wildcard template strings (for JetStream stream setup)
- [ ] Topic constants are accessible as class attributes without instantiation
- [ ] `Topics` re-exported from `src/nats_core/__init__.py`
- [ ] All modified files pass project-configured lint/format checks with zero errors
- [ ] `mypy src/` passes with zero errors in strict mode

## Implementation Notes

### Identifier Validation

Identifiers (values passed to `resolve()` kwargs and `for_project()` project name) must match:
- Non-empty
- No dots (NATS subject delimiter)
- No spaces
- No `*` or `>` (NATS wildcard tokens)
- No control characters (e.g. `\n`, `\r`, `\0`)
- No shell metacharacters (e.g. `;`, `|`, `` ` ``)

Suggested regex: `r'^[a-zA-Z0-9][a-zA-Z0-9\-_]*$'` — or a blocklist approach checking for forbidden chars. Use whichever is cleanest for the BDD scenarios.

### resolve() Template Mechanics

Templates use Python `str.format_map` style: `{feature_id}`, `{agent_id}`, etc.

```python
import re
import string

_PLACEHOLDER_RE = re.compile(r"\{(\w+)\}")

@staticmethod
def resolve(template: str, **kwargs: str) -> str:
    # Extract expected placeholders from template
    expected = set(_PLACEHOLDER_RE.findall(template))
    provided = set(kwargs)
    # Check for missing and unexpected kwargs...
    # Validate each value...
    # Return template.format(**kwargs)
```

Note: Wildcard tokens (`*`, `>`) in template strings are NOT placeholders — `pipeline.build-*.>` has no `{...}` patterns, so `resolve()` would return it unchanged (it cannot be resolved with kwargs). Document this if needed.

### ALL_TOPICS

Enumerate all templates from inner classes, excluding wildcards:

```python
ALL_TOPICS: list[str] = [
    v for cls in (Pipeline, Agents, Fleet, Jarvis, System)
    for v in vars(cls).values()
    if isinstance(v, str) and ">" not in v and "*" not in v
]
```

### Immutability (Optional)

The BDD spec includes a scenario testing that `Topics.Pipeline.BUILD_STARTED` cannot be reassigned. Options:
1. Do nothing — Python class attributes can technically be reassigned; test verifies "original value unchanged" after attempted assignment (which Python does allow on nested classes)
2. Override `__setattr__` on inner classes to raise `AttributeError`

Implement option 2 if it does not complicate mypy strict compliance; otherwise use option 1 with a note.

### EventType Sync

The `EventType` enum is defined in `src/nats_core/envelope.py` (Feature 1/2). The sync between topic templates and EventType values is verified by tests, not enforced at runtime. No import of EventType needed in `topics.py`.

## Coach Validation Commands

```bash
ruff check src/nats_core/topics.py
mypy src/nats_core/topics.py
python -c "from nats_core.topics import Topics; print(Topics.Pipeline.BUILD_STARTED)"
```
