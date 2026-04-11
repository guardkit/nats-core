---
id: TASK-NC04
title: AgentManifest + ManifestRegistry
status: completed
created: 2026-04-08 00:00:00+00:00
updated: '2026-04-11T00:00:00+00:00'
priority: high
task_type: declarative
tags:
- nats-client
- manifest
- registry
- fleet
complexity: 4
wave: 3
implementation_mode: direct
parent_review: TASK-1T1W
feature_id: FEAT-1T1W
dependencies:
- TASK-NC03
consumer_context:
- task: TASK-NC03
  consumes: EventPayloadModels
  framework: Pydantic BaseModel (nats_core.events)
  driver: pydantic
  format_note: "AgentManifest.intents uses IntentCapability (not an events model)\
    \ but manifest.py must not import from events/ \u2014 keep dependency direction:\
    \ events depend on envelope, manifest is standalone"
test_results:
  status: pending
  coverage: null
  last_run: null
autobuild_state:
  current_turn: 1
  max_turns: 30
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/nats-core/.guardkit/worktrees/FEAT-3845
  base_branch: main
  started_at: '2026-04-08T21:51:19.080298'
  last_updated: '2026-04-08T21:57:45.098421'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-04-08T21:51:19.080298'
    player_summary: Added ConfigDict(extra='ignore') to IntentCapability and ToolCapability
      models. Created abstract ManifestRegistry base class with abc.ABC and five abstract
      methods (register, deregister, get, find_by_intent, find_by_tool). Implemented
      InMemoryManifestRegistry using a dict[str, AgentManifest] store with fnmatch-based
      glob matching for find_by_intent. Updated __init__.py exports with ManifestRegistry
      and InMemoryManifestRegistry. Added factory functions to conftest.py for test
      data creation.
    player_success: true
    coach_success: true
completed: '2026-04-11T00:00:00+00:00'
completed_location: tasks/completed/nats-client/
---

# Task: AgentManifest + ManifestRegistry

## Description

Implement `src/nats_core/manifest.py` containing the `AgentManifest` model (the fleet
registration payload), the `ManifestRegistry` abstract base class, and the
`InMemoryManifestRegistry` in-process implementation used for testing.

## Scope

### `AgentManifest`

```python
class AgentManifest(BaseModel):
    # Identity
    agent_id: str
    name: str
    version: str = "0.1.0"

    # Routing (Jarvis intent router)
    intents: list[IntentCapability] = []

    # Tools (MCP servers, agent-to-agent calls)
    tools: list[ToolCapability] = []

    # Operational
    template: str
    max_concurrent: int = 1
    status: Literal["ready", "starting", "degraded"] = "ready"

    # Trust and permissions
    trust_tier: Literal["core", "specialist", "extension"] = "specialist"
    required_permissions: list[str] = []

    # Metadata
    container_id: str | None = None
    metadata: dict[str, str] = {}
```

### `IntentCapability`

```python
class IntentCapability(BaseModel):
    pattern: str           # e.g. "software.build"
    signals: list[str]     # Signal words for intent matching
    confidence: float      # 0.0–1.0 (Field ge=0.0, le=1.0)
    description: str
```

### `ToolCapability`

```python
class ToolCapability(BaseModel):
    name: str
    description: str
    parameters: dict[str, Any]       # JSON Schema for input
    returns: str
    risk_level: Literal["read_only", "mutating", "destructive"] = "read_only"
    async_mode: bool = False
    requires_approval: bool = False
```

### `ManifestRegistry` (ABC)

```python
class ManifestRegistry(ABC):
    @abstractmethod
    async def register(self, manifest: AgentManifest) -> None: ...
    @abstractmethod
    async def deregister(self, agent_id: str) -> None: ...
    @abstractmethod
    async def get(self, agent_id: str) -> AgentManifest | None: ...
    @abstractmethod
    async def list_all(self) -> list[AgentManifest]: ...
    @abstractmethod
    async def find_by_intent(self, intent: str) -> list[AgentManifest]: ...
    @abstractmethod
    async def find_by_tool(self, tool_name: str) -> list[AgentManifest]: ...
```

### `InMemoryManifestRegistry`

In-memory implementation backed by a `dict[str, AgentManifest]`. Thread-safe for
single-process testing use. Implements all `ManifestRegistry` methods.

`find_by_intent(intent)` — returns agents whose `intents` list contains any pattern
that is a prefix of or equal to the queried intent string.

`find_by_tool(tool_name)` — returns agents whose `tools` list contains a tool
matching `tool_name`.

## Acceptance Criteria

- [ ] `AgentManifest(agent_id="x", name="X Agent", template="basic")` instantiates with defaults
- [ ] `IntentCapability.confidence` is validated `ge=0.0, le=1.0`
- [ ] `ManifestRegistry` is abstract — instantiating it directly raises `TypeError`
- [ ] `InMemoryManifestRegistry.register()` stores manifest keyed by `agent_id`
- [ ] `InMemoryManifestRegistry.deregister("unknown")` does not raise
- [ ] `InMemoryManifestRegistry.find_by_intent("software.build")` returns agents with matching intent pattern
- [ ] `InMemoryManifestRegistry.find_by_tool("lint")` returns agents with that tool
- [ ] All models use `ConfigDict(extra="ignore")`
- [ ] All models use `from __future__ import annotations`
- [ ] `manifest.py` does NOT import from `nats_core.events` (no circular dependency)
- [ ] All modified files pass project-configured lint/format checks with zero errors

## Seam Tests

```python
"""Seam test: verify AgentManifest serialises to fleet registration wire format."""
import pytest


@pytest.mark.seam
@pytest.mark.integration_contract("EventPayloadModels")
def test_agent_manifest_serialises_for_fleet_registration():
    """Verify AgentManifest.model_dump_json() produces valid fleet wire format.

    Contract: manifest.py must not import from nats_core.events — it is standalone.
    Producer: TASK-NC03 (establishes events package; manifest is independent)
    """
    from nats_core.manifest import AgentManifest, IntentCapability, ToolCapability

    manifest = AgentManifest(
        agent_id="test-agent",
        name="Test Agent",
        template="basic",
        intents=[
            IntentCapability(
                pattern="software.build",
                signals=["build", "compile"],
                confidence=0.9,
                description="Build software",
            )
        ],
        tools=[
            ToolCapability(
                name="lint",
                description="Run linter",
                parameters={"type": "object", "properties": {}},
                returns="str",
            )
        ],
    )

    data = manifest.model_dump()
    assert data["agent_id"] == "test-agent"
    assert len(data["intents"]) == 1
    assert len(data["tools"]) == 1

    # Verify round-trip
    restored = AgentManifest.model_validate_json(manifest.model_dump_json())
    assert restored.agent_id == manifest.agent_id
```

## Implementation Notes

- `dict[str, Any]` in `ToolCapability.parameters` — use `from typing import Any`
- `InMemoryManifestRegistry` internal store: `_store: dict[str, AgentManifest]`
- `NATSKVManifestRegistry` (the NATS-backed implementation) lives in `client.py` (TASK-NC06)

## Coach Validation Commands

```bash
python -c "from nats_core.manifest import AgentManifest, InMemoryManifestRegistry; print('OK')"
python -c "from nats_core.manifest import ManifestRegistry; ManifestRegistry()" 2>&1 | grep -i "error\|abstract\|TypeError"
ruff check src/nats_core/manifest.py
mypy src/nats_core/manifest.py
```
