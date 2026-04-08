# Feature: Topic Registry

**Feature ID**: FEAT-TR
**Status**: Planned
**Complexity**: 4/10
**Estimated Effort**: ~2.5 hours
**Depends on**: Feature 2 (Event Type Schemas) — EventType enum must exist

---

## Overview

The Topic Registry is the single source of truth for all NATS subject strings used by fleet services. It provides typed string constants for five namespaces, template resolution, multi-tenancy project scoping, and identifier validation. No magic strings — all topic usage goes through `Topics`.

Target module: `src/nats_core/topics.py`

---

## Tasks

| Task | Title | Type | Wave | Status |
|------|-------|------|------|--------|
| [TASK-TR01](TASK-TR01-implement-topics-module.md) | Implement topics.py | declarative | 1 | pending |
| [TASK-TR02](TASK-TR02-test-suite-topics.md) | Test suite (32 BDD scenarios) | testing | 2 | pending |

---

## Execution Order

```
Wave 1: TASK-TR01 (implement topics.py)
Wave 2: TASK-TR02 (test suite — imports from TR01)
```

---

## Key API

```python
from nats_core.topics import Topics

# Constant access (no instantiation needed)
Topics.Pipeline.BUILD_STARTED     # "pipeline.build-started.{feature_id}"
Topics.Fleet.REGISTER             # "fleet.register"
Topics.Pipeline.ALL               # "pipeline.>"

# Resolution
Topics.resolve(Topics.Pipeline.BUILD_STARTED, feature_id="FEAT-001")
# -> "pipeline.build-started.FEAT-001"

# Multi-tenancy
Topics.for_project("finproxy", "pipeline.build-started.FEAT-001")
# -> "finproxy.pipeline.build-started.FEAT-001"

# All non-wildcard templates (for JetStream setup)
Topics.ALL_TOPICS  # list[str]
```

---

## BDD Spec

`features/topic-registry/topic-registry.feature` — 32 scenarios:
- 8 key examples (smoke)
- 6 boundary conditions
- 5 negative cases
- 13 edge cases

All 5 assumptions confirmed (3 high, 2 medium confidence). No deferred items.

---

## References

- API contract: `docs/design/contracts/API-topic-registry.md`
- BDD spec: `features/topic-registry/topic-registry.feature`
- Implementation guide: [IMPLEMENTATION-GUIDE.md](IMPLEMENTATION-GUIDE.md)
- Review task: `tasks/backlog/TASK-TR00-plan-topic-registry.md`
