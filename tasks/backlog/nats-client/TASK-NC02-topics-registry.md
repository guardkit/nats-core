---
id: TASK-NC02
title: "Topics registry"
status: pending
created: 2026-04-08T00:00:00Z
updated: 2026-04-08T00:00:00Z
priority: high
task_type: declarative
tags: [nats-client, topics, registry]
complexity: 3
wave: 1
implementation_mode: direct
parent_review: TASK-1T1W
feature_id: FEAT-1T1W
dependencies: [TASK-ME01]
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Topics registry

## Description

Implement `src/nats_core/topics.py` — the typed topic constants registry providing
`Topics.resolve()`, `Topics.for_project()`, and `Topics.ALL_TOPICS`.

## Scope

### Topic Hierarchy

**Pipeline domain:**
| Constant | Template |
|----------|----------|
| `Topics.Pipeline.FEATURE_PLANNED` | `pipeline.feature-planned.{feature_id}` |
| `Topics.Pipeline.FEATURE_READY_FOR_BUILD` | `pipeline.feature-ready-for-build.{feature_id}` |
| `Topics.Pipeline.BUILD_STARTED` | `pipeline.build-started.{feature_id}` |
| `Topics.Pipeline.BUILD_PROGRESS` | `pipeline.build-progress.{feature_id}` |
| `Topics.Pipeline.BUILD_COMPLETE` | `pipeline.build-complete.{feature_id}` |
| `Topics.Pipeline.BUILD_FAILED` | `pipeline.build-failed.{feature_id}` |
| `Topics.Pipeline.ALL` | `pipeline.>` |
| `Topics.Pipeline.ALL_BUILDS` | `pipeline.build-*.>` |

**Agents domain:**
| Constant | Template |
|----------|----------|
| `Topics.Agents.STATUS` | `agents.status.{agent_id}` |
| `Topics.Agents.STATUS_ALL` | `agents.status.>` |
| `Topics.Agents.APPROVAL_REQUEST` | `agents.approval.{agent_id}.{task_id}` |
| `Topics.Agents.APPROVAL_RESPONSE` | `agents.approval.{agent_id}.{task_id}.response` |
| `Topics.Agents.COMMAND` | `agents.command.{agent_id}` |
| `Topics.Agents.RESULT` | `agents.result.{agent_id}` |
| `Topics.Agents.TOOLS` | `agents.{agent_id}.tools.{tool_name}` |
| `Topics.Agents.TOOLS_ALL` | `agents.{agent_id}.tools.>` |

**Fleet domain:**
| Constant | Template |
|----------|----------|
| `Topics.Fleet.REGISTER` | `fleet.register` |
| `Topics.Fleet.DEREGISTER` | `fleet.deregister` |
| `Topics.Fleet.HEARTBEAT` | `fleet.heartbeat.{agent_id}` |
| `Topics.Fleet.HEARTBEAT_ALL` | `fleet.heartbeat.>` |
| `Topics.Fleet.ALL` | `fleet.>` |

**Jarvis domain:**
| Constant | Template |
|----------|----------|
| `Topics.Jarvis.COMMAND` | `jarvis.command.{adapter}` |
| `Topics.Jarvis.INTENT_CLASSIFIED` | `jarvis.intent.classified` |
| `Topics.Jarvis.DISPATCH` | `jarvis.dispatch.{agent}` |
| `Topics.Jarvis.NOTIFICATION` | `jarvis.notification.{adapter}` |

**System domain:**
| Constant | Template |
|----------|----------|
| `Topics.System.HEALTH` | `system.health.{component}` |

### Resolution Methods

```python
@staticmethod
def resolve(template: str, **kwargs: str) -> str:
    """Substitute {placeholders} in template. Raises KeyError on missing kwargs."""

@staticmethod
def for_project(project: str, topic: str) -> str:
    """Prepend '{project}.' to topic for multi-tenancy scoping."""
```

### ALL_TOPICS

```python
Topics.ALL_TOPICS: list[str]  # All template strings
```

### Topic segment validation

`resolve()` must reject wildcard characters (`>`, `*`) in substituted values.
Raises `ValueError` with a clear message if found.

## Acceptance Criteria

- [ ] All constants from all 5 domains are present
- [ ] `Topics.resolve(Topics.Pipeline.BUILD_COMPLETE, feature_id="FEAT-001")` → `"pipeline.build-complete.FEAT-001"`
- [ ] `Topics.for_project("finproxy", "pipeline.build-complete.FEAT-001")` → `"finproxy.pipeline.build-complete.FEAT-001"`
- [ ] `Topics.resolve(template)` raises `KeyError` when a required placeholder is missing
- [ ] `Topics.resolve(Topics.Agents.APPROVAL_RESPONSE, agent_id="jarvis", task_id="task-99")` → `"agents.approval.jarvis.task-99.response"`
- [ ] `Topics.resolve(Topics.Agents.TOOLS, agent_id="evil.>", tool_name="x")` raises `ValueError`
- [ ] `Topics.ALL_TOPICS` is a non-empty `list[str]` containing every template
- [ ] No external dependencies (pure Python)
- [ ] `from __future__ import annotations` present
- [ ] All modified files pass project-configured lint/format checks with zero errors

## Implementation Notes

- Use nested classes (`class Pipeline`, `class Agents`, etc.) as simple namespaces inside `Topics`
- `ALL_TOPICS` can be a class-level list populated at module load
- `resolve()` uses `str.format_map()` or equivalent — validate kwargs before substitution
- Topic segments use kebab-case (as per API contract)

## Coach Validation Commands

```bash
python -c "from nats_core.topics import Topics; print(Topics.resolve(Topics.Pipeline.BUILD_COMPLETE, feature_id='FEAT-001'))"
python -c "from nats_core.topics import Topics; print(Topics.for_project('finproxy', 'pipeline.build-complete.FEAT-001'))"
python -c "from nats_core.topics import Topics; print(len(Topics.ALL_TOPICS))"
ruff check src/nats_core/topics.py
mypy src/nats_core/topics.py
```
