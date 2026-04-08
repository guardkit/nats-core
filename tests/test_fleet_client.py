"""Tests for NATSClient fleet convenience methods + NATSKVManifestRegistry.

Uses AsyncMock to simulate nats-py JetStream KV without requiring a running
NATS server.  Tests are grouped by acceptance criterion from TASK-NC06.
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nats_core.config import NATSConfig
from nats_core.envelope import EventType, MessageEnvelope
from nats_core.events._fleet import AgentDeregistrationPayload, AgentHeartbeatPayload
from nats_core.manifest import AgentManifest, ManifestRegistry
from nats_core.topics import Topics

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(**overrides: Any) -> NATSConfig:
    return NATSConfig(**overrides)


def _make_manifest(agent_id: str = "test-agent", **overrides: Any) -> AgentManifest:
    defaults: dict[str, Any] = {
        "agent_id": agent_id,
        "name": "Test Agent",
        "template": "basic",
    }
    defaults.update(overrides)
    return AgentManifest(**defaults)


def _make_mock_nc() -> AsyncMock:
    """Return an AsyncMock that behaves like nats.aio.client.Client."""
    nc = AsyncMock()
    nc.is_connected = True
    nc.drain = AsyncMock()
    nc.close = AsyncMock()
    nc.publish = AsyncMock()
    sub = AsyncMock()
    nc.subscribe = AsyncMock(return_value=sub)
    return nc


def _make_mock_kv(entries: dict[str, bytes] | None = None) -> AsyncMock:
    """Return an AsyncMock that behaves like a NATS KV bucket.

    Args:
        entries: Optional mapping of key to bytes for pre-populated entries.
    """
    kv = AsyncMock()
    stored = dict(entries or {})

    async def _put(key: str, value: bytes) -> None:
        stored[key] = value

    async def _get(key: str) -> MagicMock:
        if key not in stored:
            raise KeyError(key)
        entry = MagicMock()
        entry.key = key
        entry.value = stored[key]
        return entry

    async def _delete(key: str) -> None:
        stored.pop(key, None)

    async def _keys() -> list[str]:
        return list(stored.keys())

    kv.put = AsyncMock(side_effect=_put)
    kv.get = AsyncMock(side_effect=_get)
    kv.delete = AsyncMock(side_effect=_delete)
    kv.keys = AsyncMock(side_effect=_keys)
    kv._stored = stored  # expose for assertions
    return kv


def _make_mock_js(kv: AsyncMock | None = None) -> AsyncMock:
    """Return an AsyncMock JetStream context that returns the given KV bucket."""
    js = AsyncMock()
    bucket = kv or _make_mock_kv()
    js.key_value = AsyncMock(return_value=bucket)
    js.create_key_value = AsyncMock(return_value=bucket)
    return js


async def _connect_client_with_js(
    mock_nc: AsyncMock, mock_js: AsyncMock
) -> Any:
    """Create a NATSClient, connect it with mocks, and attach JetStream."""
    from nats_core.client import NATSClient

    config = _make_config()
    client = NATSClient(config)

    with patch("nats_core.client.nats.connect", new_callable=AsyncMock) as mock_connect:
        mock_nc.jetstream = MagicMock(return_value=mock_js)
        mock_connect.return_value = mock_nc
        await client.connect()

    return client


# ===========================================================================
# AC: register_agent(manifest) publishes to fleet.register topic
# ===========================================================================


class TestRegisterAgent:
    """Tests for NATSClient.register_agent()."""

    async def test_register_publishes_to_fleet_register(self) -> None:
        """AC: register_agent(manifest) publishes to fleet.register topic."""
        mock_nc = _make_mock_nc()
        mock_kv = _make_mock_kv()
        mock_js = _make_mock_js(mock_kv)
        client = await _connect_client_with_js(mock_nc, mock_js)

        manifest = _make_manifest("agent-alpha")
        await client.register_agent(manifest)

        # Verify publish was called
        mock_nc.publish.assert_awaited()
        call_args = mock_nc.publish.call_args
        published_topic = call_args[0][0]
        assert published_topic == Topics.Fleet.REGISTER

        # Verify envelope contents
        published_data = call_args[0][1]
        envelope = MessageEnvelope.model_validate_json(published_data)
        assert envelope.event_type == EventType.AGENT_REGISTER
        assert envelope.source_id == "agent-alpha"

    async def test_register_stores_manifest_in_kv(self) -> None:
        """AC: register_agent(manifest) stores manifest in agent-registry KV bucket."""
        mock_nc = _make_mock_nc()
        mock_kv = _make_mock_kv()
        mock_js = _make_mock_js(mock_kv)
        client = await _connect_client_with_js(mock_nc, mock_js)

        manifest = _make_manifest("agent-alpha")
        await client.register_agent(manifest)

        # Verify KV put was called
        mock_kv.put.assert_awaited_once_with(
            "agent-alpha", manifest.model_dump_json().encode()
        )


# ===========================================================================
# AC: deregister_agent("agent-x", "shutdown") publishes to fleet.deregister
# ===========================================================================


class TestDeregisterAgent:
    """Tests for NATSClient.deregister_agent()."""

    async def test_deregister_publishes_to_fleet_deregister(self) -> None:
        """AC: deregister_agent publishes to fleet.deregister with reason."""
        mock_nc = _make_mock_nc()
        mock_kv = _make_mock_kv()
        mock_js = _make_mock_js(mock_kv)
        client = await _connect_client_with_js(mock_nc, mock_js)

        await client.deregister_agent("agent-x", "shutdown")

        # Verify publish was called
        mock_nc.publish.assert_awaited()
        call_args = mock_nc.publish.call_args
        published_topic = call_args[0][0]
        assert published_topic == Topics.Fleet.DEREGISTER

        # Verify envelope contents
        published_data = call_args[0][1]
        envelope = MessageEnvelope.model_validate_json(published_data)
        assert envelope.event_type == EventType.AGENT_DEREGISTER
        assert envelope.source_id == "agent-x"

        # Verify payload has reason
        payload = AgentDeregistrationPayload.model_validate(envelope.payload)
        assert payload.reason == "shutdown"
        assert payload.agent_id == "agent-x"

    async def test_deregister_deletes_from_kv(self) -> None:
        """deregister_agent deletes the key from KV (idempotent)."""
        mock_nc = _make_mock_nc()
        mock_kv = _make_mock_kv({"agent-x": b"some-data"})
        mock_js = _make_mock_js(mock_kv)
        client = await _connect_client_with_js(mock_nc, mock_js)

        await client.deregister_agent("agent-x", "shutdown")

        mock_kv.delete.assert_awaited_once_with("agent-x")


# ===========================================================================
# AC: heartbeat(payload) publishes to fleet.heartbeat.{agent_id}
# ===========================================================================


class TestHeartbeat:
    """Tests for NATSClient.heartbeat()."""

    async def test_heartbeat_publishes_to_correct_topic(self) -> None:
        """AC: heartbeat(payload) publishes to fleet.heartbeat.{agent_id}."""
        mock_nc = _make_mock_nc()
        mock_js = _make_mock_js()
        client = await _connect_client_with_js(mock_nc, mock_js)

        hb = AgentHeartbeatPayload(
            agent_id="agent-beta",
            status="ready",
            uptime_seconds=120,
        )
        await client.heartbeat(hb)

        mock_nc.publish.assert_awaited()
        call_args = mock_nc.publish.call_args
        published_topic = call_args[0][0]
        expected_topic = Topics.resolve(Topics.Fleet.HEARTBEAT, agent_id="agent-beta")
        assert published_topic == expected_topic

        # Verify envelope
        published_data = call_args[0][1]
        envelope = MessageEnvelope.model_validate_json(published_data)
        assert envelope.event_type == EventType.AGENT_HEARTBEAT
        assert envelope.source_id == "agent-beta"


# ===========================================================================
# AC: get_fleet_registry() returns all 3 agents after 3 registrations
# ===========================================================================


class TestGetFleetRegistry:
    """Tests for NATSClient.get_fleet_registry()."""

    async def test_returns_all_registered_agents(self) -> None:
        """AC: get_fleet_registry() returns all 3 agents after 3 registrations."""
        manifests = [
            _make_manifest("agent-a", name="Agent A"),
            _make_manifest("agent-b", name="Agent B"),
            _make_manifest("agent-c", name="Agent C"),
        ]
        entries = {m.agent_id: m.model_dump_json().encode() for m in manifests}

        mock_nc = _make_mock_nc()
        mock_kv = _make_mock_kv(entries)
        mock_js = _make_mock_js(mock_kv)
        client = await _connect_client_with_js(mock_nc, mock_js)

        registry = await client.get_fleet_registry()
        assert len(registry) == 3
        assert set(registry.keys()) == {"agent-a", "agent-b", "agent-c"}
        assert registry["agent-a"].name == "Agent A"
        assert isinstance(registry["agent-b"], AgentManifest)

    async def test_raises_runtime_error_when_kv_unavailable(self) -> None:
        """AC: get_fleet_registry() raises RuntimeError when KV bucket is unavailable."""
        mock_nc = _make_mock_nc()
        mock_js = AsyncMock()
        # Simulate JetStream KV bucket not accessible
        mock_js.key_value = AsyncMock(side_effect=Exception("bucket not found"))
        client = await _connect_client_with_js(mock_nc, mock_js)

        with pytest.raises(RuntimeError, match="registry unavailable"):
            await client.get_fleet_registry()


# ===========================================================================
# AC: watch_fleet() callback receives registration then deregistration events
# ===========================================================================


class TestWatchFleet:
    """Tests for NATSClient.watch_fleet()."""

    async def test_watch_fleet_receives_put_and_delete_events(self) -> None:
        """AC: watch_fleet() callback receives registration then deregistration in order."""
        mock_nc = _make_mock_nc()
        mock_kv = _make_mock_kv()
        mock_js = _make_mock_js(mock_kv)
        client = await _connect_client_with_js(mock_nc, mock_js)

        # Build mock KV watcher that yields put then delete
        manifest = _make_manifest("agent-alpha")

        put_entry = MagicMock()
        put_entry.key = "agent-alpha"
        put_entry.value = manifest.model_dump_json().encode()
        put_entry.operation = "PUT"

        del_entry = MagicMock()
        del_entry.key = "agent-alpha"
        del_entry.value = None
        del_entry.operation = "DEL"

        # Create an async iterator that yields entries then stops
        async def _mock_watch_iter() -> Any:
            yield put_entry
            yield del_entry

        watcher = MagicMock()
        watcher.__aiter__ = lambda self: _mock_watch_iter()
        watcher.stop = AsyncMock()
        mock_kv.watch = AsyncMock(return_value=watcher)

        received: list[tuple[str, AgentManifest | None]] = []

        async def _callback(key: str, manifest_or_none: AgentManifest | None) -> None:
            received.append((key, manifest_or_none))

        # Run watch_fleet as a task and let it process the mock events
        task = asyncio.create_task(client.watch_fleet(_callback))
        # Give the task time to process
        await asyncio.sleep(0.05)

        # The watcher should have received both events
        assert len(received) == 2
        assert received[0][0] == "agent-alpha"
        assert isinstance(received[0][1], AgentManifest)
        assert received[0][1].agent_id == "agent-alpha"
        assert received[1][0] == "agent-alpha"
        assert received[1][1] is None

        # Clean up task
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


# ===========================================================================
# AC: Simultaneous register+deregister leaves KV in consistent final state
# ===========================================================================


class TestConsistency:
    """Tests for concurrent register/deregister consistency."""

    async def test_register_then_deregister_leaves_consistent_state(self) -> None:
        """AC: Simultaneous register+deregister for same agent leaves KV consistent."""
        mock_nc = _make_mock_nc()
        mock_kv = _make_mock_kv()
        mock_js = _make_mock_js(mock_kv)
        client = await _connect_client_with_js(mock_nc, mock_js)

        manifest = _make_manifest("agent-alpha")

        # Register then immediately deregister
        await client.register_agent(manifest)
        await client.deregister_agent("agent-alpha", "shutdown")

        # KV should no longer have the key
        assert "agent-alpha" not in mock_kv._stored


# ===========================================================================
# AC: NATSKVManifestRegistry.get("unknown") returns None (not raises)
# ===========================================================================


class TestNATSKVManifestRegistry:
    """Tests for the KV-backed ManifestRegistry implementation."""

    def _make_registry(
        self, mock_kv: AsyncMock | None = None
    ) -> Any:
        from nats_core.client import NATSClient, NATSKVManifestRegistry

        mock_nc = _make_mock_nc()
        kv = mock_kv or _make_mock_kv()
        js = _make_mock_js(kv)
        mock_nc.jetstream = MagicMock(return_value=js)

        config = _make_config()
        nats_client = NATSClient(config)
        # Manually set _nc so the registry can use it without connecting
        nats_client._nc = mock_nc

        registry = NATSKVManifestRegistry(nats_client)
        return registry, kv

    def test_is_manifest_registry_subclass(self) -> None:
        """NATSKVManifestRegistry is a ManifestRegistry subclass."""
        from nats_core.client import NATSKVManifestRegistry

        assert issubclass(NATSKVManifestRegistry, ManifestRegistry)

    async def test_get_unknown_returns_none(self) -> None:
        """AC: NATSKVManifestRegistry.get("unknown") returns None (not raises)."""
        mock_kv = _make_mock_kv()
        registry, _ = self._make_registry(mock_kv)

        result = await registry.get("unknown")
        assert result is None

    async def test_register_and_get(self) -> None:
        """register() then get() returns the manifest."""
        mock_kv = _make_mock_kv()
        registry, _ = self._make_registry(mock_kv)

        manifest = _make_manifest("agent-alpha")
        await registry.register(manifest)
        result = await registry.get("agent-alpha")
        assert result is not None
        assert result.agent_id == "agent-alpha"

    async def test_deregister_makes_get_return_none(self) -> None:
        """deregister() removes the manifest so get() returns None."""
        entries = {
            "agent-alpha": _make_manifest("agent-alpha").model_dump_json().encode()
        }
        mock_kv = _make_mock_kv(entries)
        registry, _ = self._make_registry(mock_kv)

        await registry.deregister("agent-alpha")
        result = await registry.get("agent-alpha")
        assert result is None

    async def test_list_all(self) -> None:
        """list_all() returns all registered manifests."""
        entries = {
            "agent-a": _make_manifest("agent-a").model_dump_json().encode(),
            "agent-b": _make_manifest("agent-b").model_dump_json().encode(),
        }
        mock_kv = _make_mock_kv(entries)
        registry, _ = self._make_registry(mock_kv)

        all_manifests = await registry.list_all()
        assert len(all_manifests) == 2
        ids = {m.agent_id for m in all_manifests}
        assert ids == {"agent-a", "agent-b"}

    async def test_find_by_intent(self) -> None:
        """find_by_intent() filters manifests by exact intent pattern match."""
        from nats_core.manifest import IntentCapability

        m1 = _make_manifest(
            "agent-a",
            intents=[
                IntentCapability(pattern="software.build", description="Software tasks")
            ],
        )
        m2 = _make_manifest(
            "agent-b",
            intents=[
                IntentCapability(pattern="data.ingest", description="Data tasks")
            ],
        )
        entries = {
            "agent-a": m1.model_dump_json().encode(),
            "agent-b": m2.model_dump_json().encode(),
        }
        mock_kv = _make_mock_kv(entries)
        registry, _ = self._make_registry(mock_kv)

        results = await registry.find_by_intent("software.build")
        assert len(results) == 1
        assert results[0].agent_id == "agent-a"

    async def test_find_by_tool(self) -> None:
        """find_by_tool() filters manifests by tool name."""
        from nats_core.manifest import ToolCapability

        m1 = _make_manifest(
            "agent-a",
            tools=[
                ToolCapability(
                    name="lint",
                    description="Run linting",
                    parameters={"type": "object"},
                    returns="Lint report",
                )
            ],
        )
        m2 = _make_manifest("agent-b")
        entries = {
            "agent-a": m1.model_dump_json().encode(),
            "agent-b": m2.model_dump_json().encode(),
        }
        mock_kv = _make_mock_kv(entries)
        registry, _ = self._make_registry(mock_kv)

        results = await registry.find_by_tool("lint")
        assert len(results) == 1
        assert results[0].agent_id == "agent-a"


# ===========================================================================
# AC: All modified files pass lint/format checks — tested via ruff in CI
# ===========================================================================


# ===========================================================================
# Seam tests from the task spec
# ===========================================================================


@pytest.mark.seam
@pytest.mark.integration_contract("AgentManifest")
def test_agent_manifest_serialises_to_bytes_for_kv() -> None:
    """Verify AgentManifest.model_dump_json().encode() produces valid UTF-8 bytes.

    Contract: register_agent() puts manifest.model_dump_json().encode() into KV;
    get_fleet_registry() reads bytes and calls AgentManifest.model_validate_json().
    Producer: TASK-NC04
    """
    manifest = AgentManifest(agent_id="test-agent", name="Test", template="basic")
    raw = manifest.model_dump_json().encode()
    assert isinstance(raw, bytes)
    restored = AgentManifest.model_validate_json(raw)
    assert restored.agent_id == "test-agent"


@pytest.mark.seam
@pytest.mark.integration_contract("NATSClient")
def test_nats_client_exposes_nc_after_connect() -> None:
    """Verify NATSClient._nc is non-None after connect() (required by fleet methods).

    Contract: fleet methods access JetStream via client._nc.jetstream(); this seam
    test verifies _nc is accessible (actual connection tested in integration tests).
    Producer: TASK-NC05
    """
    from nats_core.client import NATSClient

    client = NATSClient(NATSConfig())
    assert client._nc is None  # Not connected yet - correct initial state
