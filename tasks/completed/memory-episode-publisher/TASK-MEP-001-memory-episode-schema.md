---
id: TASK-MEP-001
title: MemoryEpisodeV1 canonical schema + MAX_EPISODE_BODY_BYTES
status: completed
completed: '2026-06-24T00:00:00+00:00'
created: 2026-06-24 00:00:00+00:00
updated: '2026-06-24T00:00:00+00:00'
priority: high
task_type: declarative
tags:
- memory-publisher
- pydantic
- schema
- cross-repo-contract
complexity: 4
wave: 1
implementation_mode: task-work
parent_review: TASK-REV-MEP1
feature_id: FEAT-MEP1
dependencies: []
---

# Task: MemoryEpisodeV1 canonical schema + MAX_EPISODE_BODY_BYTES

## Description

Add the **canonical, framework-neutral** `MemoryEpisodeV1` Pydantic model — the
cross-repo contract that the `fleet-memory` relay imports/mirrors at P3. It
reconciles the two existing definitions (the 2026-06-12 scope-doc and
`fleet-memory/src/fleet_memory/relay/schema.py`) into the single authoritative
shape from v2 §5. Also define the shared `MAX_EPISODE_BODY_BYTES` size constant.

The model lives in a **private** module `src/nats_core/events/_memory.py` and is
re-exported, following the established `_fleet.py` → `events/__init__.py` →
top-level `__init__.py` convention (there is **no** public `events/memory.py`
sibling — the public `fleet.py` is a 4-line stub and re-export happens in the
`__init__` modules).

## Scope

### `src/nats_core/events/_memory.py`

```python
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# 900 KB, binary (matches the 64KB == 65536 convention in manifest.py).
# Sits ~148KB below the NATS default 1MB max_payload, leaving headroom for the
# subject + Nats-Msg-Id header. Guard is enforced by publish_episode (TASK-MEP-003).
MAX_EPISODE_BODY_BYTES = 900 * 1024  # 921600


class MemoryEpisodeV1(BaseModel):
    """Canonical framework-neutral memory episode (the cross-repo write contract)."""

    model_config = ConfigDict(extra="ignore")  # forward-compat: unknown keys survive
    # ... fields below
```

### Field set (v2 §5 canonical)

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `episode_id` | `str` (`min_length=1`) | ✅ | == `Nats-Msg-Id` header (dedupe key) |
| `project_id` | `str` (`min_length=1`) | ✅ | subject partition key (renamed from relay's `project`) |
| `episode_type` | `str` (`min_length=1`, NATS-safe identifier) | ✅ | coarse source category; the `{episode_type}` subject segment |
| `content_format` | `str` | ✅ | raw `json`/`markdown`/`text` — **NOT** an enum (relay declares `content_format: str`) |
| `body` | `str` | ✅ | the episode content |
| `payload_type` | `str \| None = None` | optional | typed-payload-registry key for the json path |
| `source_ref` | `str \| None = None` | optional | |
| `name` | `str \| None = None` | optional | |
| `source` | `str \| None = None` | optional | |
| `occurred_at` | `datetime \| None = None` | optional | |
| `published_at` | `datetime \| None = None` | optional | |
| `ingest_hints` | `dict[str, Any] \| None = None` | optional | |

- **DROP** `group_id` (FalkorDB-specific; fleet-memory partitions by namespace tuple).
- Constrain `episode_type` to a NATS-safe identifier **at the model** (e.g.
  `Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9\-_]*$", min_length=1)` — same shape as
  `topics._IDENTIFIER_RE`). This makes a bad `episode_type` fail at model
  construction instead of deep inside `Topics.resolve` at publish time.
  `underscore` values (`feature_outcome`, `structured_json`) must pass; values
  with dots/spaces/`>`/`*` must be rejected.
- Every field carries `Field(description=...)`.

### Re-exports

- `src/nats_core/events/__init__.py`: re-export `MemoryEpisodeV1`, `MAX_EPISODE_BODY_BYTES`.
- `src/nats_core/__init__.py`: add both to the imports and `__all__`.

## Acceptance Criteria

- [ ] `MemoryEpisodeV1` exists in `src/nats_core/events/_memory.py`, starts with
      `from __future__ import annotations`, sets `model_config = ConfigDict(extra="ignore")`,
      and defines exactly the v2 §5 field set above with `Field(description=...)` on every field.
- [ ] `episode_type` is constrained to a NATS-safe identifier: `MemoryEpisodeV1(... episode_type="evil.>")`
      (or any dot/space/wildcard) raises `ValidationError` at construction;
      `feature_outcome` and `structured_json` construct successfully.
- [ ] `group_id` is **not** a field; `content_format` is typed `str` (not an enum).
- [ ] `MAX_EPISODE_BODY_BYTES == 900 * 1024 == 921600` is a module-level `int` in `_memory.py`.
- [ ] `MemoryEpisodeV1` and `MAX_EPISODE_BODY_BYTES` import cleanly as
      `from nats_core.events import MemoryEpisodeV1, MAX_EPISODE_BODY_BYTES` **and**
      `from nats_core import MemoryEpisodeV1` (top-level re-export); no public `events/memory.py` is created.
- [ ] `model_validate_json` of a payload with an unknown extra key drops it (forward-compat).
- [ ] All modified files pass project-configured lint/format checks (ruff `E,F,W,I,N,UP`,
      line-length 100) and mypy strict with zero errors.

## Implementation Notes

- `datetime | None` precedent: `events/_fleet.py::AgentHeartbeatPayload.last_task_completed_at`.
- Keep the module pure data — no I/O. The size constant lives here so both the
  helper (TASK-MEP-003) and tests (TASK-MEP-004) import one source of truth.
- **Cross-repo caveat (do not "fix" here):** the *built* relay still declares a
  required `project` field. We emit `project_id` and drop `project` deliberately —
  the relay renames `project → project_id` at P3. Do **not** add a `project`
  compat alias to this canonical model; that pollutes the contract.

## Coach Validation Commands

```bash
python -c "from nats_core import MemoryEpisodeV1; from nats_core.events import MAX_EPISODE_BODY_BYTES; print(MAX_EPISODE_BODY_BYTES, sorted(MemoryEpisodeV1.model_fields))"
python -c "from nats_core import MemoryEpisodeV1; MemoryEpisodeV1(episode_id='e1', project_id='finproxy', episode_type='feature_outcome', content_format='markdown', body='x')"
python -c "from nats_core import MemoryEpisodeV1; from pydantic import ValidationError
try:
    MemoryEpisodeV1(episode_id='e1', project_id='p', episode_type='evil.>', content_format='text', body='x')
    raise SystemExit('FAIL: bad episode_type accepted')
except ValidationError:
    print('OK: bad episode_type rejected')"
ruff check src/nats_core/events/_memory.py
mypy src/nats_core/events/_memory.py
```


---

> **Tracker reconcile 2026-07-11 (WS3-S8 sweep).** FEAT-MEP1 shipped and merged at nats-core `d1f421e` (Merge FEAT-MEP1: Memory Episode Publisher, 2026-06-24); code landed in `src/nats_core/events/_memory.py` + `topics.py`. Status flipped `->` completed and file relocated to `tasks/completed/memory-episode-publisher/` to match the completed feature YAML rollup (`.guardkit/features/FEAT-MEP1.yaml` status=completed, this task status=completed). No content change.
