---
id: TASK-FR-003
title: ManifestRegistry ABC and InMemoryManifestRegistry
status: backlog
task_type: feature
priority: high
created: 2026-04-08T00:00:00Z
updated: 2026-04-08T00:00:00Z
complexity: 4
parent_review: TASK-B5F3
feature_id: FEAT-FR01
wave: 3
implementation_mode: task-work
dependencies:
  - TASK-FR-002
consumer_context:
  - task: TASK-FR-002
    consumes: AgentManifest
    framework: "Pydantic BaseModel from nats_core.manifest"
    driver: "pydantic>=2.0"
    format_note: "Import as: from nats_core.manifest import AgentManifest — model is produced by TASK-FR-002 and stored/retrieved by this registry"
---

# TASK-FR-003: ManifestRegistry ABC and InMemoryManifestRegistry

## Description

Implement the `ManifestRegistry` abstract base class and its `InMemoryManifestRegistry`
implementation. This is the registry interface contract — all other registry implementations
(NATS KV) must satisfy this ABC.

`InMemoryManifestRegistry` is a first-class citizen, not a test double. It must be
fully correct and publishable as part of the library.

## Interface to Implement

### `src/nats_core/manifest.py` — add after models

```python
from __future__ import annotations

from abc import ABC, abstractmethod


class ManifestRegistry(ABC):
    """Abstract registry for agent manifests."""

    @abstractmethod
    async def register(self, manifest: AgentManifest) -> None:
        """Store or update a manifest. Upserts — re-registration replaces previous entry."""

    @abstractmethod
    async def deregister(self, agent_id: str) -> None:
        """Remove a manifest. Silently ignored if agent_id not found."""

    @abstractmethod
    async def get(self, agent_id: str) -> AgentManifest | None:
        """Retrieve a manifest by agent_id. Returns None if not found."""

    @abstractmethod
    async def list_all(self) -> list[AgentManifest]:
        """Return all registered manifests."""

    @abstractmethod
    async def find_by_intent(self, intent: str) -> list[AgentManifest]:
        """Return agents whose intents include the given pattern."""

    @abstractmethod
    async def find_by_tool(self, tool_name: str) -> list[AgentManifest]:
        """Return agents that expose a tool with the given name."""


class InMemoryManifestRegistry(ManifestRegistry):
    """Dict-backed manifest registry for testing and NATS-free environments."""

    def __init__(self) -> None:
        self._store: dict[str, AgentManifest] = {}

    async def register(self, manifest: AgentManifest) -> None:
        if not manifest.intents:
            msg = "at least one intent capability is required"
            raise ValueError(msg)
        self._store[manifest.agent_id] = manifest

    async def deregister(self, agent_id: str) -> None:
        self._store.pop(agent_id, None)

    async def get(self, agent_id: str) -> AgentManifest | None:
        return self._store.get(agent_id)

    async def list_all(self) -> list[AgentManifest]:
        return list(self._store.values())

    async def find_by_intent(self, intent: str) -> list[AgentManifest]:
        return [
            m for m in self._store.values()
            if any(cap.pattern == intent for cap in m.intents)
        ]

    async def find_by_tool(self, tool_name: str) -> list[AgentManifest]:
        return [
            m for m in self._store.values()
            if any(tool.name == tool_name for tool in m.tools)
        ]
```

## Acceptance Criteria

- [ ] `ManifestRegistry` is an `ABC` — cannot be instantiated directly
- [ ] `InMemoryManifestRegistry.register()` upserts — re-registering the same `agent_id` replaces previous entry
- [ ] `InMemoryManifestRegistry.register()` raises `ValueError` if `manifest.intents` is empty
- [ ] `InMemoryManifestRegistry.deregister()` is idempotent — no error if `agent_id` unknown
- [ ] `InMemoryManifestRegistry.get()` returns `None` for unknown `agent_id`
- [ ] `InMemoryManifestRegistry.find_by_intent()` matches on `IntentCapability.pattern` (exact match)
- [ ] `InMemoryManifestRegistry.find_by_tool()` matches on `ToolCapability.name` (exact match)
- [ ] All methods are `async` — `InMemoryManifestRegistry` must be awaitable even without I/O
- [ ] All modified files pass project-configured lint/format checks with zero errors

## Seam Tests

The following seam test validates the integration contract with TASK-FR-002. Implement this test to verify the boundary before integration.

```python
"""Seam test: verify AgentManifest contract from TASK-FR-002."""
import pytest


@pytest.mark.seam
@pytest.mark.integration_contract("AgentManifest")
async def test_agent_manifest_storable_in_registry():
    """Verify AgentManifest produced by TASK-FR-002 is accepted by ManifestRegistry.

    Contract: AgentManifest from nats_core.manifest, pydantic BaseModel
    Producer: TASK-FR-002
    """
    from nats_core.manifest import AgentManifest, IntentCapability, InMemoryManifestRegistry

    manifest = AgentManifest(
        agent_id="test-agent",
        name="Test Agent",
        template="base",
        intents=[IntentCapability(pattern="test.intent", confidence=0.9, description="test")],
    )

    registry = InMemoryManifestRegistry()
    await registry.register(manifest)

    result = await registry.get("test-agent")
    assert result is not None
    assert result.agent_id == "test-agent"
```
