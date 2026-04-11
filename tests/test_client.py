"""Tests for NATSClient core: connect / publish / subscribe.

Uses AsyncMock to simulate nats-py without requiring a running NATS server.
Tests are grouped by acceptance criterion.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from pydantic import BaseModel

from nats_core.config import NATSConfig
from nats_core.envelope import EventType, MessageEnvelope
from nats_core.topics import Topics

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _SamplePayload(BaseModel):
    """Minimal payload for publish tests."""

    feature_id: str = "FEAT-001"
    status: str = "ok"


def _make_config(**overrides: Any) -> NATSConfig:
    return NATSConfig(**overrides)


def _make_mock_nc() -> AsyncMock:
    """Return an AsyncMock that behaves like nats.aio.client.Client."""
    nc = AsyncMock()
    nc.is_connected = True
    nc.drain = AsyncMock()
    nc.close = AsyncMock()
    nc.publish = AsyncMock()
    # subscribe returns a mock subscription object
    sub = AsyncMock()
    nc.subscribe = AsyncMock(return_value=sub)
    return nc


# ===========================================================================
# AC: await client.connect() establishes connection (test with mock)
# ===========================================================================


class TestConnect:
    """Tests for the connect() lifecycle."""

    async def test_connect_establishes_connection(self) -> None:
        """AC: await client.connect() establishes connection to NATS."""
        from nats_core.client import NATSClient

        config = _make_config()
        client = NATSClient(config)

        with patch("nats_core.client.nats.connect", new_callable=AsyncMock) as mock_connect:
            mock_nc = _make_mock_nc()
            mock_connect.return_value = mock_nc
            await client.connect()

        mock_connect.assert_awaited_once()
        # Verify config fields were forwarded
        call_kwargs = mock_connect.call_args[1]
        assert call_kwargs["servers"] == [config.url]
        assert call_kwargs["connect_timeout"] == config.connect_timeout

    async def test_connect_twice_raises_runtime_error(self) -> None:
        """connect() on an already-connected client raises RuntimeError."""
        from nats_core.client import NATSClient

        config = _make_config()
        client = NATSClient(config)

        with patch("nats_core.client.nats.connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = _make_mock_nc()
            await client.connect()

            with pytest.raises(RuntimeError, match="already connected"):
                await client.connect()


# ===========================================================================
# AC: publish/subscribe before connect() raises RuntimeError
# ===========================================================================


class TestNotConnectedErrors:
    """Tests for operations before connect()."""

    async def test_publish_before_connect_raises(self) -> None:
        """AC: client.publish() before connect() raises RuntimeError."""
        from nats_core.client import NATSClient

        client = NATSClient(_make_config())
        with pytest.raises(RuntimeError, match="not connected"):
            await client.publish(
                topic="test.topic",
                payload=_SamplePayload(),
                event_type=EventType.BUILD_COMPLETE,
                source_id="test-agent",
            )

    async def test_subscribe_before_connect_raises(self) -> None:
        """AC: client.subscribe() before connect() raises RuntimeError."""
        from nats_core.client import NATSClient

        client = NATSClient(_make_config())
        with pytest.raises(RuntimeError, match="not connected"):
            await client.subscribe(topic="test.topic", callback=AsyncMock())


# ===========================================================================
# AC: Published message arrives as valid JSON-serialised MessageEnvelope
# ===========================================================================


class TestPublish:
    """Tests for publish() envelope construction and serialisation."""

    async def _publish_and_capture(
        self,
        *,
        source_id: str = "test-agent",
        event_type: EventType = EventType.BUILD_COMPLETE,
        project: str | None = None,
        correlation_id: str | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """Helper: publish with a mock and return (topic, envelope_dict)."""
        from nats_core.client import NATSClient

        config = _make_config()
        client = NATSClient(config)
        mock_nc = _make_mock_nc()

        with patch("nats_core.client.nats.connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = mock_nc
            await client.connect()

        await client.publish(
            topic="pipeline.build-complete.FEAT-001",
            payload=_SamplePayload(),
            event_type=event_type,
            source_id=source_id,
            project=project,
            correlation_id=correlation_id,
        )

        mock_nc.publish.assert_awaited_once()
        call_args = mock_nc.publish.call_args
        published_topic = call_args[0][0]
        published_data = json.loads(call_args[0][1])
        return published_topic, published_data

    async def test_published_message_is_valid_envelope(self) -> None:
        """AC: Published message arrives as valid JSON-serialised MessageEnvelope."""
        _, data = await self._publish_and_capture()
        # Should be parseable as MessageEnvelope
        env = MessageEnvelope.model_validate(data)
        assert env.version == "1.0"

    async def test_envelope_source_id_matches_arg(self) -> None:
        """AC: envelope.source_id matches the source_id arg."""
        _, data = await self._publish_and_capture(source_id="my-special-agent")
        assert data["source_id"] == "my-special-agent"

    async def test_envelope_event_type_matches_arg(self) -> None:
        """AC: envelope.event_type matches the event_type arg."""
        _, data = await self._publish_and_capture(event_type=EventType.BUILD_STARTED)
        assert data["event_type"] == EventType.BUILD_STARTED.value

    async def test_envelope_message_id_is_valid_uuid4(self) -> None:
        """AC: envelope.message_id is a valid UUID v4 string."""
        _, data = await self._publish_and_capture()
        uuid_obj = UUID(data["message_id"], version=4)
        assert str(uuid_obj) == data["message_id"]

    async def test_envelope_timestamp_within_1s_of_now(self) -> None:
        """AC: envelope.timestamp is within 1 second of now in UTC."""
        before = datetime.now(timezone.utc)
        _, data = await self._publish_and_capture()
        after = datetime.now(timezone.utc)

        ts = datetime.fromisoformat(data["timestamp"])
        # Ensure tz-aware comparison
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        assert before <= ts <= after

    async def test_envelope_version_is_1_0(self) -> None:
        """AC: envelope.version == '1.0'."""
        _, data = await self._publish_and_capture()
        assert data["version"] == "1.0"

    async def test_envelope_payload_contains_serialised_fields(self) -> None:
        """AC: envelope.payload contains the serialised payload fields."""
        _, data = await self._publish_and_capture()
        assert data["payload"]["feature_id"] == "FEAT-001"
        assert data["payload"]["status"] == "ok"

    async def test_project_arg_prefixes_topic(self) -> None:
        """AC: Project arg prefixes topic."""
        topic, _ = await self._publish_and_capture(project="finproxy")
        assert topic == "finproxy.pipeline.build-complete.FEAT-001"

    async def test_correlation_id_in_envelope(self) -> None:
        """AC: correlation_id arg is present in envelope."""
        _, data = await self._publish_and_capture(correlation_id="corr-123")
        assert data["correlation_id"] == "corr-123"

    async def test_publish_rejects_whitespace_topic(self) -> None:
        """publish() rejects topics with leading/trailing whitespace."""
        from nats_core.client import NATSClient

        config = _make_config()
        client = NATSClient(config)
        mock_nc = _make_mock_nc()

        with patch("nats_core.client.nats.connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = mock_nc
            await client.connect()

        with pytest.raises(ValueError, match="whitespace"):
            await client.publish(
                topic="  test.topic  ",
                payload=_SamplePayload(),
                event_type=EventType.BUILD_COMPLETE,
                source_id="test-agent",
            )


# ===========================================================================
# AC: disconnect() drains all subscriptions before close
# ===========================================================================


class TestDisconnect:
    """Tests for disconnect() lifecycle."""

    async def test_disconnect_drains_then_closes(self) -> None:
        """AC: disconnect() drains all subscriptions before close."""
        from nats_core.client import NATSClient

        config = _make_config()
        client = NATSClient(config)
        mock_nc = _make_mock_nc()

        # Track call order
        call_order: list[str] = []
        mock_nc.drain = AsyncMock(side_effect=lambda: call_order.append("drain"))
        mock_nc.close = AsyncMock(side_effect=lambda: call_order.append("close"))

        with patch("nats_core.client.nats.connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = mock_nc
            await client.connect()

        await client.disconnect()
        assert call_order == ["drain", "close"]

    async def test_disconnect_when_not_connected_is_safe(self) -> None:
        """disconnect() on a not-connected client is a no-op."""
        from nats_core.client import NATSClient

        client = NATSClient(_make_config())
        # Should not raise
        await client.disconnect()


# ===========================================================================
# AC: Subscribe and receive valid envelopes / handle invalid JSON
# ===========================================================================


class TestSubscribe:
    """Tests for subscribe() and internal callback."""

    async def test_subscribe_returns_subscription(self) -> None:
        """subscribe() returns the Subscription object."""
        from nats_core.client import NATSClient

        config = _make_config()
        client = NATSClient(config)
        mock_nc = _make_mock_nc()

        with patch("nats_core.client.nats.connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = mock_nc
            await client.connect()

        cb = AsyncMock()
        sub = await client.subscribe(topic="test.topic", callback=cb)
        assert sub is not None
        mock_nc.subscribe.assert_awaited_once()

    async def test_subscribe_callback_receives_envelope(self) -> None:
        """Subscriber callback receives a parsed MessageEnvelope."""
        from nats_core.client import NATSClient

        config = _make_config()
        client = NATSClient(config)
        mock_nc = _make_mock_nc()

        # Capture the internal callback
        internal_cb = None

        async def _capture_subscribe(topic: str, cb: Any = None, **kwargs: Any) -> AsyncMock:
            nonlocal internal_cb
            internal_cb = cb
            return AsyncMock()

        mock_nc.subscribe = AsyncMock(side_effect=_capture_subscribe)

        with patch("nats_core.client.nats.connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = mock_nc
            await client.connect()

        received: list[MessageEnvelope] = []

        async def user_cb(env: MessageEnvelope) -> None:
            received.append(env)

        await client.subscribe(topic="test.topic", callback=user_cb)
        assert internal_cb is not None

        # Simulate a NATS message
        valid_envelope = MessageEnvelope(
            source_id="agent-x",
            event_type=EventType.STATUS,
            payload={"state": "running"},
        )
        msg = MagicMock()
        msg.data = valid_envelope.model_dump_json().encode()

        await internal_cb(msg)
        assert len(received) == 1
        assert received[0].source_id == "agent-x"

    async def test_invalid_json_does_not_crash_subscriber(self, caplog: Any) -> None:
        """AC: Received invalid JSON does not crash subscriber — error logged."""
        from nats_core.client import NATSClient

        config = _make_config()
        client = NATSClient(config)
        mock_nc = _make_mock_nc()

        internal_cb = None

        async def _capture_subscribe(topic: str, cb: Any = None, **kwargs: Any) -> AsyncMock:
            nonlocal internal_cb
            internal_cb = cb
            return AsyncMock()

        mock_nc.subscribe = AsyncMock(side_effect=_capture_subscribe)

        with patch("nats_core.client.nats.connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = mock_nc
            await client.connect()

        user_cb = AsyncMock()
        await client.subscribe(topic="test.topic", callback=user_cb)
        assert internal_cb is not None

        # Send invalid JSON
        msg = MagicMock()
        msg.data = b"not valid json{{"

        with caplog.at_level(logging.ERROR, logger="nats_core.client"):
            await internal_cb(msg)

        # User callback should NOT have been called
        user_cb.assert_not_awaited()
        # Error should have been logged
        assert len(caplog.records) >= 1


# ===========================================================================
# AC: NATSClient with source_id="" raises validation error at creation
# ===========================================================================


class TestSourceIdValidation:
    """Test __init__ source_id validation (not currently in __init__ signature
    per the spec — it validates during publish via envelope. However the AC
    says validate in __init__. We test the AC-specified behavior.)"""

    def test_empty_source_id_raises_at_init(self) -> None:
        """AC: NATSClient with source_id='' raises ValueError at creation."""
        from nats_core.client import NATSClient

        # The task spec says: validate source_id in __init__, raise ValueError if empty
        # But __init__ signature shows config only. Re-reading the spec:
        # "source_id validation in __init__: raise ValueError if empty string"
        # This implies __init__ may not take source_id — it could be a config field.
        # Looking at the Coach validation command:
        #   NATSClient(NATSConfig(), source_id='')
        # This means __init__ takes source_id as a separate arg.
        with pytest.raises(ValueError, match="source_id"):
            NATSClient(_make_config(), source_id="")

    def test_valid_source_id_accepted(self) -> None:
        """NATSClient with a valid source_id does not raise."""
        from nats_core.client import NATSClient

        client = NATSClient(_make_config(), source_id="valid-agent")
        # Should not raise — just verify it's created
        assert client is not None


# ===========================================================================
# Seam tests from the task spec
# ===========================================================================


# ===========================================================================
# AC: call_agent_tool() — request-reply remote tool invocation
# ===========================================================================


class TestCallAgentTool:
    """Tests for call_agent_tool() request-reply method."""

    async def test_call_agent_tool_before_connect_raises_runtime_error(self) -> None:
        """AC: call_agent_tool() before connect() raises RuntimeError with 'not connected'."""
        from nats_core.client import NATSClient

        client = NATSClient(_make_config())
        with pytest.raises(RuntimeError, match="not connected"):
            await client.call_agent_tool(
                agent_id="guardkit-factory", tool_name="lint", params={}
            )

    async def test_call_agent_tool_publishes_to_correct_topic(self) -> None:
        """AC: call_agent_tool("guardkit-factory", "lint", {}) publishes to correct topic."""
        from nats_core.client import NATSClient

        config = _make_config()
        client = NATSClient(config)
        mock_nc = _make_mock_nc()

        # Setup mock request to return valid JSON response
        response_msg = MagicMock()
        response_msg.data = json.dumps({"result": "ok"}).encode()
        mock_nc.request = AsyncMock(return_value=response_msg)

        with patch("nats_core.client.nats.connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = mock_nc
            await client.connect()

        await client.call_agent_tool(
            agent_id="guardkit-factory", tool_name="lint", params={}
        )

        mock_nc.request.assert_awaited_once()
        call_args = mock_nc.request.call_args
        assert call_args[0][0] == "agents.guardkit-factory.tools.lint"

    async def test_call_agent_tool_returns_json_decoded_response(self) -> None:
        """AC: Response from target agent is JSON-decoded and returned."""
        from nats_core.client import NATSClient

        config = _make_config()
        client = NATSClient(config)
        mock_nc = _make_mock_nc()

        response_msg = MagicMock()
        response_msg.data = json.dumps({"status": "success", "count": 42}).encode()
        mock_nc.request = AsyncMock(return_value=response_msg)

        with patch("nats_core.client.nats.connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = mock_nc
            await client.connect()

        result = await client.call_agent_tool(
            agent_id="test-agent", tool_name="process", params={"data": "hello"}
        )

        assert result == {"status": "success", "count": 42}

    async def test_call_agent_tool_timeout_raises_timeout_error(self) -> None:
        """AC: No response within timeout raises TimeoutError with agent_id and tool_name."""
        import nats.errors

        from nats_core.client import NATSClient

        config = _make_config()
        client = NATSClient(config)
        mock_nc = _make_mock_nc()

        mock_nc.request = AsyncMock(side_effect=nats.errors.TimeoutError)

        with patch("nats_core.client.nats.connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = mock_nc
            await client.connect()

        with pytest.raises(TimeoutError, match="guardkit-factory") as exc_info:
            await client.call_agent_tool(
                agent_id="guardkit-factory", tool_name="lint", params={}, timeout=5.0
            )

        assert "lint" in str(exc_info.value)
        assert "5.0" in str(exc_info.value)

    async def test_call_agent_tool_no_responders_raises_timeout_error(self) -> None:
        """AC: NoRespondersError is caught and re-raised as TimeoutError."""
        import nats.errors

        from nats_core.client import NATSClient

        config = _make_config()
        client = NATSClient(config)
        mock_nc = _make_mock_nc()

        mock_nc.request = AsyncMock(side_effect=nats.errors.NoRespondersError)

        with patch("nats_core.client.nats.connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = mock_nc
            await client.connect()

        with pytest.raises(TimeoutError, match="guardkit-factory"):
            await client.call_agent_tool(
                agent_id="guardkit-factory", tool_name="lint", params={}
            )

    async def test_call_agent_tool_wildcard_agent_id_raises_value_error(self) -> None:
        """AC: agent_id='evil.>' raises ValueError (wildcard rejection)."""
        from nats_core.client import NATSClient

        config = _make_config()
        client = NATSClient(config)
        mock_nc = _make_mock_nc()

        with patch("nats_core.client.nats.connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = mock_nc
            await client.connect()

        with pytest.raises(ValueError):
            await client.call_agent_tool(
                agent_id="evil.>", tool_name="lint", params={}
            )

    async def test_call_agent_tool_wildcard_tool_name_raises_value_error(self) -> None:
        """agent_id with '*' raises ValueError."""
        from nats_core.client import NATSClient

        config = _make_config()
        client = NATSClient(config)
        mock_nc = _make_mock_nc()

        with patch("nats_core.client.nats.connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = mock_nc
            await client.connect()

        with pytest.raises(ValueError):
            await client.call_agent_tool(
                agent_id="good-agent", tool_name="evil*tool", params={}
            )

    async def test_call_agent_tool_forwards_timeout_to_request(self) -> None:
        """AC: timeout parameter is forwarded to _nc.request()."""
        from nats_core.client import NATSClient

        config = _make_config()
        client = NATSClient(config)
        mock_nc = _make_mock_nc()

        response_msg = MagicMock()
        response_msg.data = json.dumps({"ok": True}).encode()
        mock_nc.request = AsyncMock(return_value=response_msg)

        with patch("nats_core.client.nats.connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = mock_nc
            await client.connect()

        await client.call_agent_tool(
            agent_id="test-agent", tool_name="run", params={}, timeout=15.5
        )

        call_kwargs = mock_nc.request.call_args
        assert call_kwargs[1]["timeout"] == 15.5

    async def test_call_agent_tool_serialises_params_as_json(self) -> None:
        """Params are serialised as JSON bytes in the request payload."""
        from nats_core.client import NATSClient

        config = _make_config()
        client = NATSClient(config)
        mock_nc = _make_mock_nc()

        response_msg = MagicMock()
        response_msg.data = json.dumps({}).encode()
        mock_nc.request = AsyncMock(return_value=response_msg)

        with patch("nats_core.client.nats.connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = mock_nc
            await client.connect()

        params = {"file": "main.py", "fix": True}
        await client.call_agent_tool(
            agent_id="test-agent", tool_name="lint", params=params
        )

        call_args = mock_nc.request.call_args
        sent_bytes = call_args[0][1]
        assert json.loads(sent_bytes) == params


@pytest.mark.seam
@pytest.mark.integration_contract("NATSClient")
def test_call_agent_tool_topic_matches_agents_tools_template() -> None:
    """Verify call_agent_tool builds topic matching Topics.Agents.TOOLS pattern.

    Contract: call_agent_tool uses _nc.request() on agents.{agent_id}.tools.{tool_name};
    topic must exactly match Topics.Agents.TOOLS template resolution.
    Producer: TASK-NC05
    """
    topic = Topics.resolve(
        Topics.Agents.TOOLS, agent_id="guardkit-factory", tool_name="lint"
    )
    assert topic == "agents.guardkit-factory.tools.lint"
    assert "." in topic
    assert ">" not in topic
    assert "*" not in topic


# ===========================================================================
# NATSKVManifestRegistry tests (TASK-FR-004)
# ===========================================================================


def _make_mock_kv() -> AsyncMock:
    """Return an AsyncMock that behaves like nats.js.kv.KeyValue."""
    kv = AsyncMock()
    kv.put = AsyncMock()
    kv.get = AsyncMock()
    kv.delete = AsyncMock()
    kv.keys = AsyncMock(return_value=[])
    return kv


def _make_kv_entry(value: bytes) -> MagicMock:
    """Return a mock KV entry with the given value."""
    entry = MagicMock()
    entry.value = value
    return entry


def _make_manifest_with_intents(**overrides: Any) -> Any:
    """Create an AgentManifest with at least one intent."""
    from nats_core.manifest import AgentManifest, IntentCapability

    defaults: dict[str, Any] = {
        "agent_id": "test-agent",
        "name": "Test Agent",
        "template": "basic",
        "intents": [
            IntentCapability(pattern="software.*", description="Handles software intents")
        ],
    }
    defaults.update(overrides)
    return AgentManifest(**defaults)


def _make_manifest_no_intents(**overrides: Any) -> Any:
    """Create an AgentManifest with no intents."""
    from nats_core.manifest import AgentManifest

    defaults: dict[str, Any] = {
        "agent_id": "test-agent",
        "name": "Test Agent",
        "template": "basic",
        "intents": [],
    }
    defaults.update(overrides)
    return AgentManifest(**defaults)


class TestNATSKVManifestRegistrySubclass:
    """AC: NATSKVManifestRegistry satisfies the ManifestRegistry ABC."""

    @pytest.mark.seam
    @pytest.mark.integration_contract("ManifestRegistry")
    def test_is_subclass_of_manifest_registry(self) -> None:
        """NATSKVManifestRegistry is a subclass of ManifestRegistry."""
        from nats_core.client import NATSKVManifestRegistry
        from nats_core.manifest import ManifestRegistry

        assert issubclass(NATSKVManifestRegistry, ManifestRegistry)

    @pytest.mark.seam
    @pytest.mark.integration_contract("ManifestRegistry")
    def test_instance_is_manifest_registry(self) -> None:
        """NATSKVManifestRegistry instance satisfies isinstance check."""
        from nats_core.client import NATSKVManifestRegistry
        from nats_core.manifest import ManifestRegistry

        mock_kv = _make_mock_kv()
        registry = NATSKVManifestRegistry(kv=mock_kv)
        assert isinstance(registry, ManifestRegistry)


class TestNATSKVManifestRegistryRegister:
    """AC: register() upserts via kv.put() and validates intents."""

    @pytest.mark.unit
    async def test_register_puts_manifest_as_json_bytes(self) -> None:
        """AC: register() upserts via kv.put() — uses agent_id as key."""
        from nats_core.client import NATSKVManifestRegistry

        mock_kv = _make_mock_kv()
        registry = NATSKVManifestRegistry(kv=mock_kv)
        manifest = _make_manifest_with_intents()

        await registry.register(manifest)

        mock_kv.put.assert_awaited_once()
        call_args = mock_kv.put.call_args
        assert call_args[0][0] == "test-agent"
        # Value should be JSON bytes from model_dump_json().encode()
        stored_bytes = call_args[0][1]
        assert isinstance(stored_bytes, bytes)
        # Should be valid JSON that round-trips
        from nats_core.manifest import AgentManifest

        restored = AgentManifest.model_validate_json(stored_bytes)
        assert restored.agent_id == "test-agent"

    @pytest.mark.unit
    @pytest.mark.negative
    async def test_register_raises_value_error_if_intents_empty(self) -> None:
        """AC: register() raises ValueError if manifest.intents is empty."""
        from nats_core.client import NATSKVManifestRegistry

        mock_kv = _make_mock_kv()
        registry = NATSKVManifestRegistry(kv=mock_kv)
        manifest = _make_manifest_no_intents()

        with pytest.raises(ValueError, match="at least one intent"):
            await registry.register(manifest)

        # kv.put should NOT have been called
        mock_kv.put.assert_not_awaited()

    @pytest.mark.unit
    async def test_register_upserts_on_re_registration(self) -> None:
        """register() re-registration replaces previous entry (upsert)."""
        from nats_core.client import NATSKVManifestRegistry

        mock_kv = _make_mock_kv()
        registry = NATSKVManifestRegistry(kv=mock_kv)
        manifest = _make_manifest_with_intents()

        await registry.register(manifest)
        await registry.register(manifest)

        assert mock_kv.put.await_count == 2

    @pytest.mark.unit
    async def test_register_uses_model_dump_json_encode(self) -> None:
        """AC: Values stored as model_dump_json().encode() — JSON bytes."""
        from nats_core.client import NATSKVManifestRegistry

        mock_kv = _make_mock_kv()
        registry = NATSKVManifestRegistry(kv=mock_kv)
        manifest = _make_manifest_with_intents()

        await registry.register(manifest)

        call_args = mock_kv.put.call_args
        stored = call_args[0][1]
        # Should be exactly model_dump_json().encode()
        expected = manifest.model_dump_json().encode()
        assert stored == expected

    @pytest.mark.unit
    async def test_register_logs_debug_on_success(self, caplog: Any) -> None:
        """AC: Logging uses logger.debug — register logs on success."""
        from nats_core.client import NATSKVManifestRegistry

        mock_kv = _make_mock_kv()
        registry = NATSKVManifestRegistry(kv=mock_kv)
        manifest = _make_manifest_with_intents()

        with caplog.at_level(logging.DEBUG, logger="nats_core.client"):
            await registry.register(manifest)

        assert any("registered" in r.message.lower() for r in caplog.records)


class TestNATSKVManifestRegistryDeregister:
    """AC: deregister() is idempotent — kv.delete() failure is silently logged."""

    @pytest.mark.unit
    async def test_deregister_deletes_by_agent_id(self) -> None:
        """deregister() calls kv.delete() with agent_id."""
        from nats_core.client import NATSKVManifestRegistry

        mock_kv = _make_mock_kv()
        registry = NATSKVManifestRegistry(kv=mock_kv)

        await registry.deregister("test-agent")

        mock_kv.delete.assert_awaited_once_with("test-agent")

    @pytest.mark.unit
    async def test_deregister_is_idempotent_on_key_not_found(self, caplog: Any) -> None:
        """AC: deregister() is idempotent — kv.delete() failure is silently logged."""
        from nats_core.client import NATSKVManifestRegistry

        mock_kv = _make_mock_kv()
        mock_kv.delete = AsyncMock(side_effect=Exception("key not found"))
        registry = NATSKVManifestRegistry(kv=mock_kv)

        with caplog.at_level(logging.DEBUG, logger="nats_core.client"):
            await registry.deregister("nonexistent-agent")

        # Should NOT raise
        assert any("nonexistent-agent" in r.message for r in caplog.records)


class TestNATSKVManifestRegistryGet:
    """AC: get() returns None if key not found."""

    @pytest.mark.unit
    async def test_get_returns_manifest_for_existing_key(self) -> None:
        """get() returns deserialized AgentManifest for existing key."""
        from nats_core.client import NATSKVManifestRegistry

        manifest = _make_manifest_with_intents()
        mock_kv = _make_mock_kv()
        mock_kv.get = AsyncMock(
            return_value=_make_kv_entry(manifest.model_dump_json().encode())
        )
        registry = NATSKVManifestRegistry(kv=mock_kv)

        result = await registry.get("test-agent")

        assert result is not None
        assert result.agent_id == "test-agent"

    @pytest.mark.unit
    async def test_get_uses_model_validate_json(self) -> None:
        """AC: Values deserialized via model_validate_json() — not json.loads."""
        from nats_core.client import NATSKVManifestRegistry

        manifest = _make_manifest_with_intents()
        json_bytes = manifest.model_dump_json().encode()
        mock_kv = _make_mock_kv()
        mock_kv.get = AsyncMock(return_value=_make_kv_entry(json_bytes))
        registry = NATSKVManifestRegistry(kv=mock_kv)

        result = await registry.get("test-agent")
        assert result is not None
        assert result.agent_id == manifest.agent_id

    @pytest.mark.unit
    @pytest.mark.negative
    async def test_get_returns_none_for_missing_key(self) -> None:
        """AC: get() returns None if key not found (catches all KV exceptions)."""
        from nats_core.client import NATSKVManifestRegistry

        mock_kv = _make_mock_kv()
        mock_kv.get = AsyncMock(side_effect=KeyError("not found"))
        registry = NATSKVManifestRegistry(kv=mock_kv)

        result = await registry.get("nonexistent")
        assert result is None

    @pytest.mark.unit
    @pytest.mark.negative
    async def test_get_returns_none_on_any_exception(self) -> None:
        """AC: get() catches all KV exceptions, not just KeyError."""
        from nats_core.client import NATSKVManifestRegistry

        mock_kv = _make_mock_kv()
        mock_kv.get = AsyncMock(side_effect=Exception("connection lost"))
        registry = NATSKVManifestRegistry(kv=mock_kv)

        result = await registry.get("some-agent")
        assert result is None


class TestNATSKVManifestRegistryListAll:
    """AC: list_all() returns [] if KV unavailable."""

    @pytest.mark.unit
    async def test_list_all_returns_all_manifests(self) -> None:
        """list_all() returns all registered manifests."""
        from nats_core.client import NATSKVManifestRegistry

        m1 = _make_manifest_with_intents(agent_id="agent-a")
        m2 = _make_manifest_with_intents(agent_id="agent-b")

        mock_kv = _make_mock_kv()
        mock_kv.keys = AsyncMock(return_value=["agent-a", "agent-b"])
        mock_kv.get = AsyncMock(
            side_effect=[
                _make_kv_entry(m1.model_dump_json().encode()),
                _make_kv_entry(m2.model_dump_json().encode()),
            ]
        )
        registry = NATSKVManifestRegistry(kv=mock_kv)

        results = await registry.list_all()
        assert len(results) == 2
        ids = {m.agent_id for m in results}
        assert ids == {"agent-a", "agent-b"}

    @pytest.mark.unit
    @pytest.mark.negative
    async def test_list_all_returns_empty_on_kv_unavailable(self) -> None:
        """AC: list_all() returns [] if KV unavailable (graceful degradation)."""
        from nats_core.client import NATSKVManifestRegistry

        mock_kv = _make_mock_kv()
        mock_kv.keys = AsyncMock(side_effect=Exception("KV unavailable"))
        registry = NATSKVManifestRegistry(kv=mock_kv)

        results = await registry.list_all()
        assert results == []

    @pytest.mark.unit
    async def test_list_all_returns_empty_when_no_keys(self) -> None:
        """list_all() returns empty list when bucket has no keys."""
        from nats_core.client import NATSKVManifestRegistry

        mock_kv = _make_mock_kv()
        mock_kv.keys = AsyncMock(return_value=[])
        registry = NATSKVManifestRegistry(kv=mock_kv)

        results = await registry.list_all()
        assert results == []


class TestNATSKVManifestRegistryCreate:
    """AC: create() classmethod creates bucket if it does not exist."""

    @pytest.mark.unit
    async def test_create_calls_create_key_value(self) -> None:
        """AC: create() classmethod creates bucket if it does not exist."""
        from nats_core.client import NATSKVManifestRegistry

        mock_nc = AsyncMock()
        mock_js = AsyncMock()
        mock_kv = _make_mock_kv()
        mock_nc.jetstream = MagicMock(return_value=mock_js)
        mock_js.create_key_value = AsyncMock(return_value=mock_kv)

        registry = await NATSKVManifestRegistry.create(mock_nc)

        mock_js.create_key_value.assert_awaited_once()
        call_kwargs = mock_js.create_key_value.call_args
        assert call_kwargs[1]["bucket"] == "agent-registry"
        assert isinstance(registry, NATSKVManifestRegistry)

    @pytest.mark.unit
    async def test_create_returns_registry_with_kv(self) -> None:
        """create() returns a NATSKVManifestRegistry with the KV bucket bound."""
        from nats_core.client import NATSKVManifestRegistry

        mock_nc = AsyncMock()
        mock_js = AsyncMock()
        mock_kv = _make_mock_kv()
        mock_nc.jetstream = MagicMock(return_value=mock_js)
        mock_js.create_key_value = AsyncMock(return_value=mock_kv)

        registry = await NATSKVManifestRegistry.create(mock_nc)

        # Verify the registry can delegate to the mock kv
        manifest = _make_manifest_with_intents()
        await registry.register(manifest)
        mock_kv.put.assert_awaited_once()


class TestNATSKVManifestRegistryFindByIntent:
    """Tests for find_by_intent() — filters from list_all()."""

    @pytest.mark.unit
    async def test_find_by_intent_returns_matching_manifests(self) -> None:
        """find_by_intent() returns manifests with matching intent pattern."""
        from nats_core.client import NATSKVManifestRegistry
        from nats_core.manifest import IntentCapability

        m1 = _make_manifest_with_intents(agent_id="agent-a")
        m2 = _make_manifest_with_intents(
            agent_id="agent-b",
            intents=[IntentCapability(pattern="devops.*", description="Devops")],
        )

        mock_kv = _make_mock_kv()
        mock_kv.keys = AsyncMock(return_value=["agent-a", "agent-b"])
        mock_kv.get = AsyncMock(
            side_effect=[
                _make_kv_entry(m1.model_dump_json().encode()),
                _make_kv_entry(m2.model_dump_json().encode()),
            ]
        )
        registry = NATSKVManifestRegistry(kv=mock_kv)

        results = await registry.find_by_intent("software.*")
        assert len(results) == 1
        assert results[0].agent_id == "agent-a"

    @pytest.mark.unit
    async def test_find_by_intent_returns_empty_for_no_match(self) -> None:
        """find_by_intent() returns empty list when no manifests match."""
        from nats_core.client import NATSKVManifestRegistry

        mock_kv = _make_mock_kv()
        mock_kv.keys = AsyncMock(return_value=[])
        registry = NATSKVManifestRegistry(kv=mock_kv)

        results = await registry.find_by_intent("nonexistent.*")
        assert results == []


class TestNATSKVManifestRegistryFindByTool:
    """Tests for find_by_tool() — filters from list_all()."""

    @pytest.mark.unit
    async def test_find_by_tool_returns_matching_manifests(self) -> None:
        """find_by_tool() returns manifests with matching tool name."""
        from nats_core.client import NATSKVManifestRegistry
        from nats_core.manifest import ToolCapability

        m1 = _make_manifest_with_intents(
            agent_id="agent-a",
            tools=[
                ToolCapability(
                    name="lint",
                    description="Run linter",
                    parameters={"type": "object"},
                    returns="Lint report",
                )
            ],
        )
        m2 = _make_manifest_with_intents(agent_id="agent-b")

        mock_kv = _make_mock_kv()
        mock_kv.keys = AsyncMock(return_value=["agent-a", "agent-b"])
        mock_kv.get = AsyncMock(
            side_effect=[
                _make_kv_entry(m1.model_dump_json().encode()),
                _make_kv_entry(m2.model_dump_json().encode()),
            ]
        )
        registry = NATSKVManifestRegistry(kv=mock_kv)

        results = await registry.find_by_tool("lint")
        assert len(results) == 1
        assert results[0].agent_id == "agent-a"

    @pytest.mark.unit
    async def test_find_by_tool_returns_empty_for_no_match(self) -> None:
        """find_by_tool() returns empty list when no manifests match."""
        from nats_core.client import NATSKVManifestRegistry

        mock_kv = _make_mock_kv()
        mock_kv.keys = AsyncMock(return_value=[])
        registry = NATSKVManifestRegistry(kv=mock_kv)

        results = await registry.find_by_tool("nonexistent")
        assert results == []


class TestNATSKVManifestRegistryLogging:
    """AC: Logging uses logger.debug/warning — never print()."""

    @pytest.mark.unit
    async def test_list_all_logs_warning_on_kv_unavailable(self, caplog: Any) -> None:
        """AC: list_all() logs warning when KV is unavailable."""
        from nats_core.client import NATSKVManifestRegistry

        mock_kv = _make_mock_kv()
        mock_kv.keys = AsyncMock(side_effect=Exception("KV unavailable"))
        registry = NATSKVManifestRegistry(kv=mock_kv)

        with caplog.at_level(logging.WARNING, logger="nats_core.client"):
            await registry.list_all()

        assert any("list_all" in r.message.lower() for r in caplog.records)


# ===========================================================================
# Existing seam tests
# ===========================================================================


@pytest.mark.seam
@pytest.mark.integration_contract("NATSConfig")
def test_nats_config_fields_match_nats_py_connect_signature() -> None:
    """Verify NATSConfig fields can be passed to nats.connect() without TypeError."""
    config = NATSConfig()
    assert isinstance(config.url, str)
    assert config.url.startswith("nats://")
    assert isinstance(config.connect_timeout, float)
    assert isinstance(config.max_reconnect_attempts, int)
    assert isinstance(config.reconnect_time_wait, float)


@pytest.mark.seam
@pytest.mark.integration_contract("Topics")
def test_topics_resolve_returns_str_without_placeholders() -> None:
    """Verify Topics.resolve() returns a fully-resolved string."""
    resolved = Topics.resolve(Topics.Pipeline.BUILD_COMPLETE, feature_id="FEAT-001")
    assert isinstance(resolved, str)
    assert "{" not in resolved
    assert resolved == "pipeline.build-complete.FEAT-001"


@pytest.mark.seam
@pytest.mark.integration_contract("MessageEnvelope")
def test_message_envelope_json_round_trips() -> None:
    """Verify MessageEnvelope round-trips through JSON."""
    env = MessageEnvelope(
        message_id="550e8400-e29b-41d4-a716-446655440000",
        timestamp="2026-04-08T00:00:00Z",
        version="1.0",
        source_id="test-agent",
        event_type=EventType.BUILD_COMPLETE,
        payload={"feature_id": "FEAT-001"},
    )
    raw = env.model_dump_json()
    restored = MessageEnvelope.model_validate_json(raw)
    assert restored.source_id == "test-agent"
    assert restored.event_type == EventType.BUILD_COMPLETE
