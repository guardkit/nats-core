"""Factory functions for fleet registration test suite.

Uses dataclass-based mock data classes and factory functions (not fixtures)
per project conventions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from nats_core.manifest import (
    AgentManifest,
    InMemoryManifestRegistry,
    IntentCapability,
    ToolCapability,
)
from nats_core._routing import HeartbeatRecord
from nats_core.events._fleet import AgentDeregistrationPayload, AgentHeartbeatPayload


# ---------------------------------------------------------------------------
# Mock data classes
# ---------------------------------------------------------------------------


@dataclass
class MockIntent:
    """Mock intent data for factory functions."""

    pattern: str = "software.build"
    signals: list[str] = field(default_factory=lambda: ["build", "compile"])
    confidence: float = 0.9
    description: str = "Build software"


@dataclass
class MockManifest:
    """Mock manifest data for factory functions."""

    agent_id: str = "guardkit-factory"
    name: str = "GuardKit Factory"
    template: str = "factory"
    intents: list[dict[str, Any]] = field(default_factory=list)
    max_concurrent: int = 2


# ---------------------------------------------------------------------------
# Factory functions
# ---------------------------------------------------------------------------


def make_intent(**overrides: Any) -> dict[str, Any]:
    """Create an intent capability dict with sensible defaults.

    Args:
        **overrides: Keyword arguments to override default field values.

    Returns:
        A dict suitable for constructing an IntentCapability.
    """
    defaults: dict[str, Any] = {
        "pattern": "software.build",
        "signals": ["build", "compile"],
        "confidence": 0.9,
        "description": "Build software",
    }
    defaults.update(overrides)
    return defaults


def make_manifest(**overrides: Any) -> dict[str, Any]:
    """Create an agent manifest dict with sensible defaults.

    Args:
        **overrides: Keyword arguments to override default field values.

    Returns:
        A dict suitable for constructing an AgentManifest.
    """
    defaults: dict[str, Any] = {
        "agent_id": "guardkit-factory",
        "name": "GuardKit Factory",
        "template": "factory",
        "intents": [make_intent()],
        "max_concurrent": 2,
    }
    defaults.update(overrides)
    return defaults


def make_agent_manifest(**overrides: Any) -> AgentManifest:
    """Create an AgentManifest instance with sensible defaults.

    Args:
        **overrides: Keyword arguments to override default field values.

    Returns:
        An AgentManifest instance.
    """
    return AgentManifest(**make_manifest(**overrides))


def make_intent_capability(**overrides: Any) -> IntentCapability:
    """Create an IntentCapability instance with sensible defaults.

    Args:
        **overrides: Keyword arguments to override default field values.

    Returns:
        An IntentCapability instance.
    """
    return IntentCapability(**make_intent(**overrides))


def make_heartbeat_payload(**overrides: Any) -> AgentHeartbeatPayload:
    """Create an AgentHeartbeatPayload with sensible defaults.

    Args:
        **overrides: Keyword arguments to override default field values.

    Returns:
        An AgentHeartbeatPayload instance.
    """
    defaults: dict[str, Any] = {
        "agent_id": "guardkit-factory",
        "status": "ready",
        "queue_depth": 0,
        "active_tasks": 0,
        "uptime_seconds": 120,
    }
    defaults.update(overrides)
    return AgentHeartbeatPayload(**defaults)


def make_heartbeat_record(**overrides: Any) -> HeartbeatRecord:
    """Create a HeartbeatRecord with sensible defaults.

    Args:
        **overrides: Keyword arguments to override default field values.

    Returns:
        A HeartbeatRecord dataclass instance.
    """
    defaults: dict[str, Any] = {
        "agent_id": "guardkit-factory",
        "queue_depth": 0,
        "active_tasks": 0,
        "available": True,
    }
    defaults.update(overrides)
    return HeartbeatRecord(**defaults)


def make_in_memory_registry() -> InMemoryManifestRegistry:
    """Create an empty InMemoryManifestRegistry.

    Returns:
        A fresh InMemoryManifestRegistry with no registered manifests.
    """
    return InMemoryManifestRegistry()


def make_mock_kv_bucket() -> MagicMock:
    """Create a mock NATS KV bucket backed by a dict.

    Returns:
        A MagicMock that simulates KV bucket get/put/delete/keys operations.
    """
    store: dict[str, bytes] = {}

    bucket = MagicMock()

    async def _put(key: str, value: bytes) -> None:
        store[key] = value

    async def _get(key: str) -> MagicMock:
        if key not in store:
            raise KeyError(key)
        entry = MagicMock()
        entry.value = store[key]
        entry.key = key
        return entry

    async def _delete(key: str) -> None:
        if key not in store:
            raise KeyError(key)
        del store[key]

    async def _keys() -> list[str]:
        if not store:
            raise Exception("no keys found")  # noqa: TRY002
        return list(store.keys())

    bucket.put = AsyncMock(side_effect=_put)
    bucket.get = AsyncMock(side_effect=_get)
    bucket.delete = AsyncMock(side_effect=_delete)
    bucket.keys = AsyncMock(side_effect=_keys)
    bucket._store = store  # exposed for test inspection

    return bucket
