---
id: TASK-FR-004
title: NATSKVManifestRegistry
status: completed
task_type: feature
priority: high
created: 2026-04-08T00:00:00Z
updated: '2026-04-11T00:00:00+00:00'
complexity: 6
parent_review: TASK-B5F3
feature_id: FEAT-FR01
wave: 4
implementation_mode: task-work
dependencies:
  - TASK-FR-003
consumer_context:
  - task: TASK-FR-003
    consumes: ManifestRegistry
    framework: "ABC from nats_core.manifest"
    driver: "abc.ABC"
    format_note: "Import as: from nats_core.manifest import ManifestRegistry — NATSKVManifestRegistry must subclass ManifestRegistry and implement all abstract methods"
completed: '2026-04-11T00:00:00+00:00'
completed_location: tasks/completed/fleet-registration/
---

# TASK-FR-004: NATSKVManifestRegistry

## Description

Implement `NATSKVManifestRegistry` — the NATS JetStream KV-backed production registry.
Lives in `src/nats_core/client.py` consistent with the existing `NATSClient` placement.

KV bucket name: `agent-registry`. Key per agent: `{agent_id}`. Value: JSON-serialised `AgentManifest`.

## Interface to Implement

### `src/nats_core/client.py` — add after NATSClient

```python
from __future__ import annotations

import logging
from nats.aio.client import Client as NATSConnection
from nats.js.kv import KeyValue
from nats_core.manifest import AgentManifest, ManifestRegistry

logger = logging.getLogger(__name__)

AGENT_REGISTRY_BUCKET = "agent-registry"


class NATSKVManifestRegistry(ManifestRegistry):
    """NATS JetStream KV-backed manifest registry.

    Backed by the 'agent-registry' KV bucket. Each entry is stored as
    JSON-serialised AgentManifest keyed by agent_id.
    """

    def __init__(self, kv: KeyValue) -> None:
        self._kv = kv

    @classmethod
    async def create(cls, nc: NATSConnection) -> NATSKVManifestRegistry:
        """Factory: bind to the agent-registry KV bucket (creates if missing)."""
        js = nc.jetstream()
        kv = await js.create_key_value(bucket=AGENT_REGISTRY_BUCKET)
        return cls(kv)

    async def register(self, manifest: AgentManifest) -> None:
        if not manifest.intents:
            msg = "at least one intent capability is required"
            raise ValueError(msg)
        payload = manifest.model_dump_json().encode()
        await self._kv.put(manifest.agent_id, payload)
        logger.debug("registered agent %s", manifest.agent_id)

    async def deregister(self, agent_id: str) -> None:
        try:
            await self._kv.delete(agent_id)
        except Exception:
            logger.debug("deregister: agent %s not found (ignored)", agent_id)

    async def get(self, agent_id: str) -> AgentManifest | None:
        try:
            entry = await self._kv.get(agent_id)
            return AgentManifest.model_validate_json(entry.value)
        except Exception:
            return None

    async def list_all(self) -> list[AgentManifest]:
        results: list[AgentManifest] = []
        try:
            keys = await self._kv.keys()
            for key in keys:
                manifest = await self.get(key)
                if manifest is not None:
                    results.append(manifest)
        except Exception:
            logger.warning("list_all: KV unavailable, returning empty list")
        return results

    async def find_by_intent(self, intent: str) -> list[AgentManifest]:
        return [
            m for m in await self.list_all()
            if any(cap.pattern == intent for cap in m.intents)
        ]

    async def find_by_tool(self, tool_name: str) -> list[AgentManifest]:
        return [
            m for m in await self.list_all()
            if any(tool.name == tool_name for tool in m.tools)
        ]
```

## Acceptance Criteria

- [ ] `NATSKVManifestRegistry` satisfies the `ManifestRegistry` ABC (mypy strict passes)
- [ ] `NATSKVManifestRegistry.register()` upserts via `kv.put()` — uses `agent_id` as key
- [ ] `NATSKVManifestRegistry.register()` raises `ValueError` if `manifest.intents` is empty
- [ ] `NATSKVManifestRegistry.deregister()` is idempotent — `kv.delete()` failure is silently logged, not raised
- [ ] `NATSKVManifestRegistry.get()` returns `None` if key not found (catches all KV exceptions)
- [ ] `NATSKVManifestRegistry.list_all()` returns `[]` if KV unavailable (graceful degradation)
- [ ] `NATSKVManifestRegistry.create()` classmethod creates bucket if it does not exist
- [ ] Values stored as `model_dump_json().encode()` — JSON bytes, not pickle or repr
- [ ] Values deserialized via `model_validate_json()` — not `model_validate(json.loads(...))`
- [ ] Logging uses `logger.debug/warning` — never `print()`
- [ ] All modified files pass project-configured lint/format checks with zero errors

## Implementation Notes

- Unit tests for this task should mock `KeyValue` — do not require a live NATS server
- The `create()` classmethod should use `create_key_value` not `bind` — ensures bucket exists
- KV exceptions from nats-py should be caught broadly (various exception types from JetStream)
- This task runs in Wave 4 parallel with TASK-FR-005 — no shared file writes

## Seam Tests

The following seam test validates the integration contract with TASK-FR-003. Implement this test to verify the boundary before integration.

```python
"""Seam test: verify ManifestRegistry contract from TASK-FR-003."""
import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.mark.seam
@pytest.mark.integration_contract("ManifestRegistry")
async def test_nats_kv_registry_satisfies_manifest_registry_abc():
    """Verify NATSKVManifestRegistry satisfies the ManifestRegistry ABC.

    Contract: ManifestRegistry ABC from nats_core.manifest
    Producer: TASK-FR-003
    """
    from nats_core.manifest import ManifestRegistry
    from nats_core.client import NATSKVManifestRegistry

    # Structural check: must be a subclass of ManifestRegistry
    assert issubclass(NATSKVManifestRegistry, ManifestRegistry)

    # Behavioural check: can be instantiated with a mock KV
    mock_kv = MagicMock()
    registry = NATSKVManifestRegistry(kv=mock_kv)
    assert isinstance(registry, ManifestRegistry)
```
