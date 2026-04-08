---
id: TASK-FR-001
title: Fleet Registration scaffolding
status: backlog
task_type: scaffolding
priority: high
created: 2026-04-08T00:00:00Z
updated: 2026-04-08T00:00:00Z
complexity: 2
parent_review: TASK-B5F3
feature_id: FEAT-FR01
wave: 1
implementation_mode: direct
dependencies: []
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
