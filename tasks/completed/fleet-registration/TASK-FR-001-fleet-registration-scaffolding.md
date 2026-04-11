---
id: TASK-FR-001
title: Fleet Registration scaffolding
status: completed
task_type: scaffolding
priority: high
created: 2026-04-08 00:00:00+00:00
updated: '2026-04-11T00:00:00+00:00'
complexity: 2
parent_review: TASK-B5F3
feature_id: FEAT-FR01
wave: 1
implementation_mode: direct
dependencies: []
autobuild_state:
  current_turn: 1
  max_turns: 30
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/nats-core/.guardkit/worktrees/FEAT-BEA5
  base_branch: main
  started_at: '2026-04-08T23:19:19.804228'
  last_updated: '2026-04-08T23:21:59.300201'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-04-08T23:19:19.804228'
    player_summary: Created two new stub files (_routing.py and events/fleet.py) with
      only docstrings and 'from __future__ import annotations'. The manifest.py and
      py.typed files already existed in the codebase. Wrote 25 comprehensive tests
      covering file existence, future annotations presence and ordering, valid Python
      syntax, stub-only enforcement (no class/function definitions), importability,
      and subprocess import verification.
    player_success: true
    coach_success: true
completed: '2026-04-11T00:00:00+00:00'
completed_location: tasks/completed/fleet-registration/
---

# TASK-FR-001: Fleet Registration scaffolding

## Description

Set up the package structure for the Fleet Registration feature within nats-core.
This is the foundation wave — all subsequent Fleet Registration tasks depend on these
modules existing.

## Deliverables

Create the following files (empty stubs — content implemented in subsequent tasks):

```
src/
└── nats_core/
    ├── __init__.py        # Package init (if not already present)
    ├── py.typed           # PEP 561 marker (if not already present)
    ├── manifest.py        # AgentManifest, IntentCapability, ToolCapability,
    │                      # ManifestRegistry ABC, InMemoryManifestRegistry
    ├── _routing.py        # Private: routing logic (confidence + queue-depth tiebreak)
    └── events/
        ├── __init__.py    # Events sub-package init (if not already present)
        └── fleet.py       # AgentHeartbeatPayload, AgentDeregistrationPayload
```

## Acceptance Criteria

- [ ] `src/nats_core/manifest.py` exists (stub with `from __future__ import annotations`)
- [ ] `src/nats_core/_routing.py` exists (stub with `from __future__ import annotations`)
- [ ] `src/nats_core/events/fleet.py` exists (stub with `from __future__ import annotations`)
- [ ] `src/nats_core/py.typed` exists (empty file — PEP 561 compliance)
- [ ] `python -c "import nats_core"` succeeds without error
- [ ] All stub files include `from __future__ import annotations` as first import
- [ ] No logic implemented in this task — stubs only

## Implementation Notes

Each stub file should contain only:
```python
from __future__ import annotations
```

If `src/nats_core/__init__.py` already exists (from Message Envelope scaffolding),
do NOT overwrite it. Only add missing files.

If `src/nats_core/events/__init__.py` already exists, do NOT overwrite it.
