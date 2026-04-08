---
complexity: 4
created: 2026-04-08 00:00:00+00:00
dependencies:
- TASK-FR-001
feature_id: FEAT-FR01
id: TASK-FR-002
implementation_mode: task-work
parent_review: TASK-B5F3
priority: high
status: design_approved
task_type: declarative
title: Fleet Registration Pydantic models
updated: 2026-04-08 00:00:00+00:00
wave: 2
---

# TASK-FR-002: Fleet Registration Pydantic models

## Description

Implement all Pydantic data models for the Fleet Registration feature.
These models are the single source of truth for wire format and validation.

## Models to Implement

### `src/nats_core/manifest.py`

```python
from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field, field_validator


class IntentCapability(BaseModel):
    """An intent this agent can handle, with confidence scoring."""
    pattern: str = Field(description="Intent pattern, e.g. 'software.build'")
    signals: list[str] = Field(default_factory=list, description="Signal words for intent matching")
    confidence: float = Field(ge=0.0, le=1.0, description="How well agent handles this intent")
    description: str = Field(description="Human-readable description")


class ToolCapability(BaseModel):
    """A specific operation this agent exposes for direct invocation."""
    name: str = Field(description="Tool name")
    description: str = Field(description="Human/model-readable description")
    parameters: dict[str, Any] = Field(description="JSON Schema for input")
    returns: str = Field(description="Return value description")
    risk_level: Literal["read_only", "mutating", "destructive"] = Field(
        default="read_only", description="Risk classification"
    )
    async_mode: bool = Field(default=False, description="True if long-running")
    requires_approval: bool = Field(default=False, description="True if human-in-the-loop needed")


class AgentManifest(BaseModel):
    """Complete capability declaration for a fleet agent."""
    # Identity
    agent_id: str = Field(description="Unique agent identifier")
    name: str = Field(description="Human-readable name")
    version: str = Field(default="0.1.0", description="Agent software version")

    # Routing
    intents: list[IntentCapability] = Field(default_factory=list, description="Jarvis routing capabilities")

    # Tools
    tools: list[ToolCapability] = Field(default_factory=list, description="Direct invocation operations")

    # Operational
    template: str = Field(description="Agent template name")
    max_concurrent: int = Field(default=1, ge=1, description="Max parallel tasks")
    status: Literal["ready", "starting", "degraded"] = Field(default="ready", description="Current status")

    # Trust
    trust_tier: Literal["core", "specialist", "extension"] = Field(
        default="specialist", description="Trust level"
    )
    required_permissions: list[str] = Field(default_factory=list, description="Required permissions")

    # Metadata
    container_id: str | None = Field(default=None, description="Docker container ID")
    metadata: dict[str, str] = Field(default_factory=dict, description="Extensible metadata")

    @field_validator("metadata")
    @classmethod
    def metadata_size_must_not_exceed_64kb(cls, v: dict[str, str]) -> dict[str, str]:
        import json
        if len(json.dumps(v).encode()) > 65536:
            msg = "metadata exceeds the maximum allowed size of 64KB"
            raise ValueError(msg)
        return v
```

### `src/nats_core/events/fleet.py`

```python
from __future__ import annotations

from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


class AgentHeartbeatPayload(BaseModel):
    """Lightweight periodic liveness signal."""
    agent_id: str = Field(description="Agent identifier")
    status: Literal["ready", "busy", "degraded", "draining"] = Field(description="Current status")
    queue_depth: int = Field(default=0, ge=0, description="Pending tasks")
    active_tasks: int = Field(default=0, ge=0, description="Currently executing")
    uptime_seconds: int = Field(ge=0, description="Agent uptime")
    last_task_completed_at: datetime | None = Field(default=None)
    active_workflow_states: dict[str, str] = Field(
        default_factory=dict, description="task_id -> state mapping"
    )


class AgentDeregistrationPayload(BaseModel):
    """Minimal graceful shutdown signal."""
    agent_id: str = Field(description="Agent identifier")
    reason: str = Field(default="shutdown", description="shutdown/maintenance/error")
```

## Acceptance Criteria

- [ ] `AgentManifest` validates `confidence` in `[0.0, 1.0]` — values outside rejected with `ValidationError`
- [ ] `AgentManifest.max_concurrent` rejects values `< 1` with `ValidationError`
- [ ] `AgentManifest` requires `agent_id`, `name`, `template` — missing any raises `ValidationError`
- [ ] `AgentManifest` requires at least zero intents (empty list is valid at model level; empty-list rejection is a registry concern)
- [ ] `metadata` validator rejects payloads > 64KB with descriptive error
- [ ] `AgentHeartbeatPayload.status` is constrained to `ready/busy/degraded/draining`
- [ ] `AgentDeregistrationPayload.reason` defaults to `"shutdown"`
- [ ] All models use `from __future__ import annotations`
- [ ] All fields have `Field(description=...)` annotation
- [ ] All modified files pass project-configured lint/format checks with zero errors

## Implementation Notes

- Use `model_config = ConfigDict(extra="ignore")` on `AgentManifest` for forward compatibility (ADR-002)
- `metadata` validator uses `json.dumps().encode()` for byte-accurate size check
- Keep models as pure data containers — no I/O, no NATS calls