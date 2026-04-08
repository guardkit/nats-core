# API Contract: Topic Registry

**Bounded Context:** Topic Registry (topics.py)
**Protocols:** NATS Events, Python Public API
**Version:** 1.0.0
**Date:** 2026-04-07

---

## Python Public API

### Topics Class

```python
from nats_core.topics import Topics

# Resolution
Topics.resolve(Topics.Pipeline.BUILD_STARTED, feature_id="FEAT-001")
# -> "pipeline.build-started.FEAT-001"

# Multi-tenancy scoping
Topics.for_project("finproxy", "pipeline.build-started.FEAT-001")
# -> "finproxy.pipeline.build-started.FEAT-001"

# All topic templates (for stream setup / monitoring)
Topics.ALL_TOPICS  # list[str] of every template
```

---

## Topic Hierarchy

### Pipeline Domain

| Constant | Template | Placeholders |
|----------|----------|-------------|
| `Topics.Pipeline.FEATURE_PLANNED` | `pipeline.feature-planned.{feature_id}` | feature_id |
| `Topics.Pipeline.FEATURE_READY_FOR_BUILD` | `pipeline.feature-ready-for-build.{feature_id}` | feature_id |
| `Topics.Pipeline.BUILD_STARTED` | `pipeline.build-started.{feature_id}` | feature_id |
| `Topics.Pipeline.BUILD_PROGRESS` | `pipeline.build-progress.{feature_id}` | feature_id |
| `Topics.Pipeline.BUILD_COMPLETE` | `pipeline.build-complete.{feature_id}` | feature_id |
| `Topics.Pipeline.BUILD_FAILED` | `pipeline.build-failed.{feature_id}` | feature_id |
| `Topics.Pipeline.ALL` | `pipeline.>` | (wildcard) |
| `Topics.Pipeline.ALL_BUILDS` | `pipeline.build-*.>` | (wildcard) |

### Agents Domain

| Constant | Template | Placeholders |
|----------|----------|-------------|
| `Topics.Agents.STATUS` | `agents.status.{agent_id}` | agent_id |
| `Topics.Agents.STATUS_ALL` | `agents.status.>` | (wildcard) |
| `Topics.Agents.APPROVAL_REQUEST` | `agents.approval.{agent_id}.{task_id}` | agent_id, task_id |
| `Topics.Agents.APPROVAL_RESPONSE` | `agents.approval.{agent_id}.{task_id}.response` | agent_id, task_id |
| `Topics.Agents.COMMAND` | `agents.command.{agent_id}` | agent_id |
| `Topics.Agents.RESULT` | `agents.result.{agent_id}` | agent_id |
| `Topics.Agents.TOOLS` | `agents.{agent_id}.tools.{tool_name}` | agent_id, tool_name |
| `Topics.Agents.TOOLS_ALL` | `agents.{agent_id}.tools.>` | agent_id |

### Fleet Domain

| Constant | Template | Placeholders |
|----------|----------|-------------|
| `Topics.Fleet.REGISTER` | `fleet.register` | (none) |
| `Topics.Fleet.DEREGISTER` | `fleet.deregister` | (none) |
| `Topics.Fleet.HEARTBEAT` | `fleet.heartbeat.{agent_id}` | agent_id |
| `Topics.Fleet.HEARTBEAT_ALL` | `fleet.heartbeat.>` | (wildcard) |
| `Topics.Fleet.ALL` | `fleet.>` | (wildcard) |

### Jarvis Domain

| Constant | Template | Placeholders |
|----------|----------|-------------|
| `Topics.Jarvis.COMMAND` | `jarvis.command.{adapter}` | adapter |
| `Topics.Jarvis.INTENT_CLASSIFIED` | `jarvis.intent.classified` | (none) |
| `Topics.Jarvis.DISPATCH` | `jarvis.dispatch.{agent}` | agent |
| `Topics.Jarvis.NOTIFICATION` | `jarvis.notification.{adapter}` | adapter |

### System Domain

| Constant | Template | Placeholders |
|----------|----------|-------------|
| `Topics.System.HEALTH` | `system.health.{component}` | component |

---

## Resolution Rules

1. `Topics.resolve(template, **kwargs)` -- substitutes `{placeholders}` with values
2. `Topics.for_project(project, topic)` -- prepends `{project}.` for multi-tenancy
3. Raises `KeyError` if a required placeholder is not provided
4. Topic segments use kebab-case (`build-started`, not `build_started`)
5. Wildcards use NATS `>` (multi-level) for "all" patterns

---

## ALL_TOPICS

```python
Topics.ALL_TOPICS: list[str]  # Every template string, for stream setup and monitoring
```

Useful for:
- NATS JetStream stream creation scripts
- Monitoring dashboard configuration
- Automated topic documentation generation
