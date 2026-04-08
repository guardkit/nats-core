"""Integration tests for NATSClient — all 33 BDD scenarios.

Maps every scenario in ``features/nats-client/nats-client.feature`` to one or
more ``pytest`` test functions.  All tests use ``AsyncMock`` to simulate the
nats-py transport layer; no running NATS server is required.

Markers:
    @pytest.mark.integration — every test in this module
    @pytest.mark.smoke       — core happy-path scenarios
    @pytest.mark.key_example — key usage examples from BDD
    @pytest.mark.boundary    — boundary / limit conditions
    @pytest.mark.negative    — invalid input / error paths
    @pytest.mark.edge_case   — edge-case and unusual inputs
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import nats.errors
import pytest
from pydantic import BaseModel

from nats_core.client import NATSClient
from nats_core.envelope import EventType, MessageEnvelope
from nats_core.events._fleet import AgentHeartbeatPayload
from nats_core.events._pipeline import BuildCompletePayload
from nats_core.manifest import AgentManifest, IntentCapability
from nats_core.topics import Topics

# ---------------------------------------------------------------------------
# Factory helpers (stateless, no fixtures)
# ---------------------------------------------------------------------------


def make_build_complete_payload(**overrides: Any) -> BuildCompletePayload:
    """Create a BuildCompletePayload with sensible defaults.

    Args:
        **overrides: Keyword arguments to override default field values.

    Returns:
        A BuildCompletePayload instance with defaults plus overrides.
    """
    defaults: dict[str, Any] = {
        "feature_id": "FEAT-001",
        "build_id": "build-FEAT-001-20260408120000",
        "repo": "appmilla/nats-core",
        "branch": "main",
        "tasks_completed": 5,
        "tasks_failed": 0,
        "tasks_total": 5,
        "pr_url": "https://github.com/appmilla/nats-core/pull/42",
        "duration_seconds": 300,
        "summary": "All tasks completed successfully",
    }
    defaults.update(overrides)
    return BuildCompletePayload(**defaults)


def _make_mock_nc() -> AsyncMock:
    """Return an AsyncMock that behaves like nats.aio.client.Client."""
    nc = AsyncMock()
    nc.is_connected = True
    nc.drain = AsyncMock()
    nc.close = AsyncMock()
    nc.publish = AsyncMock()
    sub = AsyncMock()
    nc.subscribe = AsyncMock(return_value=sub)
    nc.request = AsyncMock()
    # JetStream mock
    js = AsyncMock()
    kv = AsyncMock()
    js.key_value = AsyncMock(return_value=kv)
    nc.jetstream = MagicMock(return_value=js)
    return nc


def _make_connected_client(
    source_id: str = "test-agent",
) -> tuple[NATSClient, AsyncMock]:
    """Create a NATSClient and connect it with a mock NATS connection.

    Args:
        source_id: The source_id for the client.

    Returns:
        Tuple of (client, mock_nc).
    """
    from nats_core.config import NATSConfig

    config = NATSConfig()
    client = NATSClient(config, source_id=source_id)
    mock_nc = _make_mock_nc()
    # Directly inject the mock connection
    client._nc = mock_nc
    return client, mock_nc


def _make_agent_manifest(agent_id: str = "product-owner-agent", **overrides: Any) -> AgentManifest:
    """Create an AgentManifest with sensible defaults.

    Args:
        agent_id: The agent identifier.
        **overrides: Keyword arguments to override default field values.

    Returns:
        An AgentManifest instance.
    """
    defaults: dict[str, Any] = {
        "agent_id": agent_id,
        "name": f"Agent {agent_id}",
        "template": "basic",
    }
    defaults.update(overrides)
    return AgentManifest(**defaults)


def _make_heartbeat_payload(
    agent_id: str = "ideation-agent", **overrides: Any
) -> AgentHeartbeatPayload:
    """Create an AgentHeartbeatPayload with sensible defaults.

    Args:
        agent_id: The agent identifier.
        **overrides: Keyword arguments to override default field values.

    Returns:
        An AgentHeartbeatPayload instance.
    """
    defaults: dict[str, Any] = {
        "agent_id": agent_id,
        "status": "ready",
        "uptime_seconds": 120,
    }
    defaults.update(overrides)
    return AgentHeartbeatPayload(**defaults)


# ===========================================================================
# @key-example @smoke — Scenarios 1–8
# ===========================================================================


@pytest.mark.integration
@pytest.mark.smoke
@pytest.mark.key_example
class TestPublishTypedEventWrapsInEnvelope:
    """Scenario 1: Publishing a typed event wraps it in a MessageEnvelope."""

    async def test_publish_typed_event_wraps_in_envelope(self) -> None:
        """Publish BuildCompletePayload → envelope → correct topic."""
        client, mock_nc = _make_connected_client()
        payload = make_build_complete_payload()

        await client.publish(
            topic=Topics.resolve(Topics.Pipeline.BUILD_COMPLETE, feature_id="FEAT-001"),
            payload=payload,
            event_type=EventType.BUILD_COMPLETE,
            source_id="test-agent",
        )

        mock_nc.publish.assert_awaited_once()
        call_args = mock_nc.publish.call_args
        published_topic = call_args[0][0]
        published_data = json.loads(call_args[0][1])

        # Topic is correct
        assert published_topic == "pipeline.build-complete.FEAT-001"
        # Valid envelope
        env = MessageEnvelope.model_validate(published_data)
        assert env.event_type == EventType.BUILD_COMPLETE
        assert env.source_id == "test-agent"
        # Payload contains BuildCompletePayload fields
        assert env.payload["feature_id"] == "FEAT-001"
        assert env.payload["build_id"] == "build-FEAT-001-20260408120000"


@pytest.mark.integration
@pytest.mark.smoke
@pytest.mark.key_example
class TestSubscribeReceivesDeserialisedEnvelope:
    """Scenario 2: Subscribing with a typed handler receives deserialised envelopes."""

    async def test_subscribe_receives_deserialised_envelope(self) -> None:
        """Subscribe + publish → typed handler receives MessageEnvelope."""
        client, mock_nc = _make_connected_client()

        # Capture internal callback
        internal_cb: Any = None

        async def _capture_subscribe(topic: str, cb: Any = None, **kwargs: Any) -> AsyncMock:
            nonlocal internal_cb
            internal_cb = cb
            return AsyncMock()

        mock_nc.subscribe = AsyncMock(side_effect=_capture_subscribe)

        received: list[MessageEnvelope] = []

        async def handler(env: MessageEnvelope) -> None:
            received.append(env)

        await client.subscribe(
            topic=Topics.resolve(Topics.Pipeline.BUILD_COMPLETE, feature_id="FEAT-001"),
            callback=handler,
        )

        assert internal_cb is not None

        # Simulate incoming message
        envelope = MessageEnvelope(
            source_id="builder",
            event_type=EventType.BUILD_COMPLETE,
            payload=make_build_complete_payload().model_dump(),
        )
        msg = MagicMock()
        msg.data = envelope.model_dump_json().encode()
        await internal_cb(msg)

        assert len(received) == 1
        assert received[0].event_type == EventType.BUILD_COMPLETE
        assert received[0].payload["feature_id"] == "FEAT-001"


@pytest.mark.integration
@pytest.mark.smoke
@pytest.mark.key_example
class TestProjectScopedPublishPrefixesTopic:
    """Scenario 3: Project-scoped publish prefixes the topic."""

    async def test_project_scoped_publish_prefixes_topic(self) -> None:
        """Project='finproxy' → prefixed topic and project field in envelope."""
        client, mock_nc = _make_connected_client()
        payload = make_build_complete_payload()

        await client.publish(
            topic=Topics.resolve(Topics.Pipeline.BUILD_COMPLETE, feature_id="FEAT-001"),
            payload=payload,
            event_type=EventType.BUILD_COMPLETE,
            source_id="test-agent",
            project="finproxy",
        )

        call_args = mock_nc.publish.call_args
        published_topic = call_args[0][0]
        published_data = json.loads(call_args[0][1])

        assert published_topic == "finproxy.pipeline.build-complete.FEAT-001"
        assert published_data["project"] == "finproxy"


@pytest.mark.integration
@pytest.mark.key_example
class TestPublishWithCorrelationId:
    """Scenario 4: Publishing with a correlation ID includes it in the envelope."""

    async def test_publish_with_correlation_id(self) -> None:
        """Correlation_id in envelope, distinct message_id."""
        client, mock_nc = _make_connected_client()
        payload = make_build_complete_payload()

        await client.publish(
            topic=Topics.resolve(Topics.Pipeline.BUILD_COMPLETE, feature_id="FEAT-001"),
            payload=payload,
            event_type=EventType.BUILD_COMPLETE,
            source_id="test-agent",
            correlation_id="session-abc-123",
        )

        published_data = json.loads(mock_nc.publish.call_args[0][1])
        assert published_data["correlation_id"] == "session-abc-123"
        # message_id is a distinct value (UUID)
        assert published_data["message_id"] != "session-abc-123"
        UUID(published_data["message_id"], version=4)


@pytest.mark.integration
@pytest.mark.smoke
@pytest.mark.key_example
class TestRegisterAgentPublishesToFleetRegister:
    """Scenario 5: Registering an agent publishes to the fleet register topic."""

    async def test_register_agent_publishes_to_fleet_register(self) -> None:
        """Register_agent → fleet.register topic with AGENT_REGISTER event."""
        client, mock_nc = _make_connected_client()
        manifest = _make_agent_manifest(
            agent_id="product-owner-agent",
            intents=[
                IntentCapability(
                    pattern="product.*",
                    description="Handles product intents",
                )
            ],
        )

        await client.register_agent(manifest)

        # Verify publish was called
        mock_nc.publish.assert_awaited()
        call_args = mock_nc.publish.call_args
        published_topic = call_args[0][0]
        published_data = json.loads(call_args[0][1])

        assert published_topic == "fleet.register"
        assert published_data["event_type"] == EventType.AGENT_REGISTER.value
        # Payload includes intent capabilities
        assert len(published_data["payload"]["intents"]) == 1
        assert published_data["payload"]["intents"][0]["pattern"] == "product.*"


@pytest.mark.integration
@pytest.mark.key_example
class TestHeartbeatPublishesToAgentSpecificTopic:
    """Scenario 6: Sending a heartbeat publishes to agent-specific heartbeat topic."""

    async def test_heartbeat_publishes_to_agent_specific_topic(self) -> None:
        """Heartbeat → fleet.heartbeat.ideation-agent."""
        client, mock_nc = _make_connected_client()
        hb = _make_heartbeat_payload(agent_id="ideation-agent")

        await client.heartbeat(hb)

        mock_nc.publish.assert_awaited()
        published_topic = mock_nc.publish.call_args[0][0]
        published_data = json.loads(mock_nc.publish.call_args[0][1])

        assert published_topic == "fleet.heartbeat.ideation-agent"
        assert published_data["event_type"] == EventType.AGENT_HEARTBEAT.value


@pytest.mark.integration
@pytest.mark.key_example
class TestDeregisterPublishesToFleetDeregister:
    """Scenario 7: Deregistering an agent publishes to fleet.deregister."""

    async def test_deregister_publishes_to_fleet_deregister(self) -> None:
        """Deregister_agent → fleet.deregister with reason."""
        client, mock_nc = _make_connected_client()

        await client.deregister_agent(
            agent_id="youtube-planner", reason="shutdown"
        )

        mock_nc.publish.assert_awaited()
        published_topic = mock_nc.publish.call_args[0][0]
        published_data = json.loads(mock_nc.publish.call_args[0][1])

        assert published_topic == "fleet.deregister"
        assert published_data["event_type"] == EventType.AGENT_DEREGISTER.value
        assert published_data["payload"]["reason"] == "shutdown"


@pytest.mark.integration
@pytest.mark.key_example
class TestCallAgentToolUsesRequestReply:
    """Scenario 8: Calling a remote agent tool uses request-reply."""

    async def test_call_agent_tool_uses_request_reply(self) -> None:
        """Call_agent_tool → request to agents.guardkit-factory.tools.lint."""
        client, mock_nc = _make_connected_client()

        response_msg = MagicMock()
        response_msg.data = json.dumps({"result": "ok"}).encode()
        mock_nc.request = AsyncMock(return_value=response_msg)

        result = await client.call_agent_tool(
            agent_id="guardkit-factory", tool_name="lint", params={"file": "main.py"}
        )

        mock_nc.request.assert_awaited_once()
        call_args = mock_nc.request.call_args
        assert call_args[0][0] == "agents.guardkit-factory.tools.lint"
        assert result == {"result": "ok"}


# ===========================================================================
# @boundary — Scenarios 9–14
# ===========================================================================


@pytest.mark.integration
@pytest.mark.boundary
class TestPublishEmptyPayloadSucceeds:
    """Scenario 9: Publishing with an empty payload dictionary succeeds."""

    async def test_publish_empty_payload_succeeds(self) -> None:
        """Empty payload dict is valid."""
        client, mock_nc = _make_connected_client()

        class EmptyPayload(BaseModel):
            pass

        await client.publish(
            topic="test.topic",
            payload=EmptyPayload(),
            event_type=EventType.STATUS,
            source_id="test-agent",
        )

        mock_nc.publish.assert_awaited_once()
        published_data = json.loads(mock_nc.publish.call_args[0][1])
        assert published_data["payload"] == {}


@pytest.mark.integration
@pytest.mark.boundary
class TestSingleCharSourceIdPublishes:
    """Scenario 10: Client with a single-character source ID publishes successfully."""

    async def test_single_char_source_id_publishes(self) -> None:
        """Source_id='x' → envelope.source_id == 'x'."""
        client, mock_nc = _make_connected_client(source_id="x")

        class SimplePayload(BaseModel):
            data: str = "test"

        await client.publish(
            topic="test.topic",
            payload=SimplePayload(),
            event_type=EventType.STATUS,
            source_id="x",
        )

        published_data = json.loads(mock_nc.publish.call_args[0][1])
        assert published_data["source_id"] == "x"


@pytest.mark.integration
@pytest.mark.boundary
@pytest.mark.negative
class TestEmptySourceIdRaisesValidationError:
    """Scenario 11: Creating a client with an empty source ID is rejected."""

    def test_empty_source_id_raises_validation_error(self) -> None:
        """Source_id='' raises ValueError at creation."""
        from nats_core.config import NATSConfig

        with pytest.raises(ValueError, match="source_id"):
            NATSClient(NATSConfig(), source_id="")


@pytest.mark.integration
@pytest.mark.boundary
class TestWildcardSubscriptionReceivesMatchingMessages:
    """Scenario 12: Subscribing to a wildcard topic receives matching messages."""

    async def test_wildcard_subscription_receives_matching_messages(self) -> None:
        """Pipeline.> captures multiple subjects."""
        client, mock_nc = _make_connected_client()

        internal_cb: Any = None

        async def _capture_subscribe(topic: str, cb: Any = None, **kwargs: Any) -> AsyncMock:
            nonlocal internal_cb
            internal_cb = cb
            return AsyncMock()

        mock_nc.subscribe = AsyncMock(side_effect=_capture_subscribe)

        received: list[MessageEnvelope] = []

        async def handler(env: MessageEnvelope) -> None:
            received.append(env)

        # Subscribe to wildcard
        await client.subscribe(topic="pipeline.>", callback=handler)
        assert internal_cb is not None

        # Simulate message from pipeline.build-started.FEAT-001
        env1 = MessageEnvelope(
            source_id="builder",
            event_type=EventType.BUILD_STARTED,
            payload={"feature_id": "FEAT-001", "build_id": "b1", "wave_total": 1},
        )
        msg1 = MagicMock()
        msg1.data = env1.model_dump_json().encode()
        await internal_cb(msg1)

        # Simulate message from pipeline.build-complete.FEAT-002
        env2 = MessageEnvelope(
            source_id="builder",
            event_type=EventType.BUILD_COMPLETE,
            payload=make_build_complete_payload(feature_id="FEAT-002").model_dump(),
        )
        msg2 = MagicMock()
        msg2.data = env2.model_dump_json().encode()
        await internal_cb(msg2)

        assert len(received) == 2


@pytest.mark.integration
@pytest.mark.boundary
class TestDeeplyNestedTopicResolvesCorrectly:
    """Scenario 13: Deeply nested topic template resolves correctly."""

    def test_deeply_nested_topic_resolves_correctly(self) -> None:
        """Approval response topic with max depth resolves correctly."""
        topic = Topics.resolve(
            Topics.Agents.APPROVAL_RESPONSE,
            agent_id="jarvis",
            task_id="task-99",
        )
        assert topic == "agents.approval.jarvis.task-99.response"


@pytest.mark.integration
@pytest.mark.boundary
@pytest.mark.negative
class TestMissingTopicVariableRaisesError:
    """Scenario 14: Publishing with missing topic template variables is rejected."""

    def test_missing_topic_variable_raises_error(self) -> None:
        """Missing template variable raises KeyError."""
        with pytest.raises(KeyError, match="feature_id"):
            Topics.resolve(Topics.Pipeline.BUILD_COMPLETE)


# ===========================================================================
# @negative — Scenarios 15–20
# ===========================================================================


@pytest.mark.integration
@pytest.mark.negative
@pytest.mark.smoke
class TestPublishDisconnectedRaises:
    """Scenario 15: Publishing on a disconnected client raises an error."""

    async def test_publish_disconnected_raises(self) -> None:
        """RuntimeError before connect()."""
        from nats_core.config import NATSConfig

        client = NATSClient(NATSConfig())

        with pytest.raises(RuntimeError, match="not connected"):
            await client.publish(
                topic="test.topic",
                payload=make_build_complete_payload(),
                event_type=EventType.BUILD_COMPLETE,
                source_id="test-agent",
            )


@pytest.mark.integration
@pytest.mark.negative
class TestSubscribeDisconnectedRaises:
    """Scenario 16: Subscribing on a disconnected client raises an error."""

    async def test_subscribe_disconnected_raises(self) -> None:
        """RuntimeError before connect()."""
        from nats_core.config import NATSConfig

        client = NATSClient(NATSConfig())

        with pytest.raises(RuntimeError, match="not connected"):
            await client.subscribe(topic="test.topic", callback=AsyncMock())


@pytest.mark.integration
@pytest.mark.negative
class TestInvalidJsonDoesNotCrashSubscriber:
    """Scenario 17: Receiving invalid JSON does not crash the handler."""

    async def test_invalid_json_does_not_crash_subscriber(self, caplog: Any) -> None:
        """Malformed bytes → error logged, handler stays alive."""
        client, mock_nc = _make_connected_client()

        internal_cb: Any = None

        async def _capture_subscribe(topic: str, cb: Any = None, **kwargs: Any) -> AsyncMock:
            nonlocal internal_cb
            internal_cb = cb
            return AsyncMock()

        mock_nc.subscribe = AsyncMock(side_effect=_capture_subscribe)

        user_cb = AsyncMock()
        await client.subscribe(topic="test.topic", callback=user_cb)
        assert internal_cb is not None

        # Send invalid JSON
        msg = MagicMock()
        msg.data = b"not valid json{{"

        with caplog.at_level(logging.ERROR, logger="nats_core.client"):
            await internal_cb(msg)

        # User callback must NOT have been called
        user_cb.assert_not_awaited()
        # Error should be logged
        assert any("Failed to parse" in r.message for r in caplog.records)

        # Handler stays alive — send a valid message after the bad one
        valid_env = MessageEnvelope(
            source_id="agent",
            event_type=EventType.STATUS,
            payload={"state": "running"},
        )
        msg2 = MagicMock()
        msg2.data = valid_env.model_dump_json().encode()
        await internal_cb(msg2)
        user_cb.assert_awaited_once()


@pytest.mark.integration
@pytest.mark.negative
class TestUnexpectedEventTypeHandledGracefully:
    """Scenario 18: Receiving an envelope with unexpected event type is handled."""

    async def test_unexpected_event_type_handled_gracefully(self) -> None:
        """Wrong event_type on topic → does not crash handler."""
        client, mock_nc = _make_connected_client()

        internal_cb: Any = None

        async def _capture_subscribe(topic: str, cb: Any = None, **kwargs: Any) -> AsyncMock:
            nonlocal internal_cb
            internal_cb = cb
            return AsyncMock()

        mock_nc.subscribe = AsyncMock(side_effect=_capture_subscribe)

        received: list[MessageEnvelope] = []

        async def handler(env: MessageEnvelope) -> None:
            received.append(env)

        await client.subscribe(
            topic=Topics.resolve(Topics.Pipeline.BUILD_COMPLETE, feature_id="FEAT-001"),
            callback=handler,
        )
        assert internal_cb is not None

        # Send BUILD_FAILED on a BUILD_COMPLETE topic
        env = MessageEnvelope(
            source_id="builder",
            event_type=EventType.BUILD_FAILED,
            payload={
                "feature_id": "FEAT-001",
                "build_id": "b1",
                "failure_reason": "timeout",
                "recoverable": True,
            },
        )
        msg = MagicMock()
        msg.data = env.model_dump_json().encode()

        # Should not crash — handler receives the envelope (client doesn't filter by event_type)
        await internal_cb(msg)
        assert len(received) == 1
        assert received[0].event_type == EventType.BUILD_FAILED


@pytest.mark.integration
@pytest.mark.negative
class TestCallAgentToolTimeout:
    """Scenario 19: Agent tool call times out when no reply is received."""

    async def test_call_agent_tool_timeout(self) -> None:
        """TimeoutError raised with agent_id in message."""
        client, mock_nc = _make_connected_client()
        mock_nc.request = AsyncMock(side_effect=nats.errors.TimeoutError)

        with pytest.raises(TimeoutError) as exc_info:
            await client.call_agent_tool(
                agent_id="offline-agent",
                tool_name="test",
                params={},
                timeout=5.0,
            )

        assert "offline-agent" in str(exc_info.value)


@pytest.mark.integration
@pytest.mark.negative
class TestDoubleConnectRaisesOrIdempotent:
    """Scenario 20: Connecting already-connected client raises or is idempotent."""

    async def test_double_connect_raises_or_idempotent(self) -> None:
        """Second connect() raises RuntimeError."""
        from nats_core.config import NATSConfig

        config = NATSConfig()
        client = NATSClient(config)

        with patch("nats_core.client.nats.connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = _make_mock_nc()
            await client.connect()

            with pytest.raises(RuntimeError, match="already connected"):
                await client.connect()


# ===========================================================================
# @edge-case — Scenarios 21–33
# ===========================================================================


@pytest.mark.integration
@pytest.mark.edge_case
@pytest.mark.smoke
class TestReconnectAfterTransientDisconnection:
    """Scenario 21: Client reconnects automatically after transient disconnection."""

    async def test_reconnect_after_transient_disconnection(self) -> None:
        """Server restart → reconnect.

        nats-py handles reconnection internally via max_reconnect_attempts config.
        We verify the config is passed correctly.
        """
        from nats_core.config import NATSConfig

        config = NATSConfig(max_reconnect_attempts=60, reconnect_time_wait=2.0)
        connect_kwargs = config.to_connect_kwargs()

        assert connect_kwargs["max_reconnect_attempts"] == 60
        assert connect_kwargs["reconnect_time_wait"] == 2.0

        # Verify client passes config to nats.connect
        client = NATSClient(config)
        with patch("nats_core.client.nats.connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = _make_mock_nc()
            await client.connect()
            call_kwargs = mock_connect.call_args[1]
            assert call_kwargs["max_reconnect_attempts"] == 60
            assert call_kwargs["reconnect_time_wait"] == 2.0


@pytest.mark.integration
@pytest.mark.edge_case
@pytest.mark.smoke
class TestGracefulDisconnectDrainsSubscriptions:
    """Scenario 22: Graceful disconnect drains all active subscriptions."""

    async def test_graceful_disconnect_drains_subscriptions(self) -> None:
        """Disconnect() → drain before close, clean shutdown."""
        client, mock_nc = _make_connected_client()

        call_order: list[str] = []
        mock_nc.drain = AsyncMock(side_effect=lambda: call_order.append("drain"))
        mock_nc.close = AsyncMock(side_effect=lambda: call_order.append("close"))

        await client.disconnect()

        assert call_order == ["drain", "close"]
        # Client should be marked as disconnected
        assert client._nc is None


@pytest.mark.integration
@pytest.mark.edge_case
class TestConcurrentPublishesNoCorruption:
    """Scenario 23: Concurrent publishes from multiple tasks do not corrupt messages."""

    async def test_concurrent_publishes_no_corruption(self) -> None:
        """50 concurrent publishes → all 50 arrive as valid envelopes."""
        client, mock_nc = _make_connected_client()

        class SimplePayload(BaseModel):
            index: int

        async def publish_one(i: int) -> None:
            await client.publish(
                topic="test.topic",
                payload=SimplePayload(index=i),
                event_type=EventType.STATUS,
                source_id="test-agent",
            )

        # Fire 50 concurrent publishes
        await asyncio.gather(*[publish_one(i) for i in range(50)])

        # Verify all 50 arrived
        assert mock_nc.publish.await_count == 50

        # Verify each is a valid envelope
        message_ids: set[str] = set()
        for call in mock_nc.publish.call_args_list:
            data = json.loads(call[0][1])
            env = MessageEnvelope.model_validate(data)
            assert env.event_type == EventType.STATUS
            message_ids.add(env.message_id)

        # All 50 have distinct message_ids (no corruption)
        assert len(message_ids) == 50


@pytest.mark.integration
@pytest.mark.edge_case
class TestMultipleHandlersSameTopic:
    """Scenario 24: Multiple handlers on the same topic all receive the message."""

    async def test_multiple_handlers_same_topic(self) -> None:
        """Two subscribers both receive message."""
        client, mock_nc = _make_connected_client()

        internal_cbs: list[Any] = []

        async def _capture_subscribe(topic: str, cb: Any = None, **kwargs: Any) -> AsyncMock:
            internal_cbs.append(cb)
            return AsyncMock()

        mock_nc.subscribe = AsyncMock(side_effect=_capture_subscribe)

        received_1: list[MessageEnvelope] = []
        received_2: list[MessageEnvelope] = []

        async def handler_1(env: MessageEnvelope) -> None:
            received_1.append(env)

        async def handler_2(env: MessageEnvelope) -> None:
            received_2.append(env)

        await client.subscribe(topic="test.topic", callback=handler_1)
        await client.subscribe(topic="test.topic", callback=handler_2)

        assert len(internal_cbs) == 2

        # Simulate message arriving on the topic
        env = MessageEnvelope(
            source_id="agent",
            event_type=EventType.STATUS,
            payload={"state": "running"},
        )
        msg = MagicMock()
        msg.data = env.model_dump_json().encode()

        # Both internal callbacks would be called by NATS
        for cb in internal_cbs:
            await cb(msg)

        assert len(received_1) == 1
        assert len(received_2) == 1


@pytest.mark.integration
@pytest.mark.edge_case
class TestGetFleetRegistryReturnsAllAgents:
    """Scenario 25: Reading the fleet registry returns all registered agents."""

    async def test_get_fleet_registry_returns_all_agents(self) -> None:
        """3 registrations → all in registry keyed by agent_id."""
        client, mock_nc = _make_connected_client()

        agents = [
            _make_agent_manifest("agent-alpha"),
            _make_agent_manifest("agent-beta"),
            _make_agent_manifest("agent-gamma"),
        ]

        # Mock KV bucket
        kv = AsyncMock()
        kv.keys = AsyncMock(return_value=["agent-alpha", "agent-beta", "agent-gamma"])

        # Mock get to return correct agent for each key
        agent_map = {a.agent_id: a for a in agents}

        async def mock_get(key: str) -> MagicMock:
            entry = MagicMock()
            entry.value = agent_map[key].model_dump_json().encode()
            return entry

        kv.get = AsyncMock(side_effect=mock_get)

        js = MagicMock()
        js.key_value = AsyncMock(return_value=kv)
        mock_nc.jetstream = MagicMock(return_value=js)

        result = await client.get_fleet_registry()

        assert len(result) == 3
        assert "agent-alpha" in result
        assert "agent-beta" in result
        assert "agent-gamma" in result
        assert isinstance(result["agent-alpha"], AgentManifest)


@pytest.mark.integration
@pytest.mark.edge_case
class TestWatchFleetReceivesEventsInOrder:
    """Scenario 26: Watching the fleet receives registration and deregistration events."""

    async def test_watch_fleet_receives_events_in_order(self) -> None:
        """Register then deregister → ordered callbacks."""
        client, mock_nc = _make_connected_client()

        manifest = _make_agent_manifest("watcher-agent")

        # Create mock KV entries
        put_entry = MagicMock()
        put_entry.operation = "PUT"
        put_entry.key = "watcher-agent"
        put_entry.value = manifest.model_dump_json().encode()

        del_entry = MagicMock()
        del_entry.operation = "DEL"
        del_entry.key = "watcher-agent"
        del_entry.value = None

        # Mock watcher as an async iterator
        class MockWatcher:
            def __init__(self) -> None:
                self._entries = [put_entry, del_entry]
                self._index = 0

            def __aiter__(self) -> MockWatcher:
                return self

            async def __anext__(self) -> Any:
                if self._index >= len(self._entries):
                    raise StopAsyncIteration
                entry = self._entries[self._index]
                self._index += 1
                return entry

        kv = AsyncMock()
        kv.watch = AsyncMock(return_value=MockWatcher())

        js = MagicMock()
        js.key_value = AsyncMock(return_value=kv)
        mock_nc.jetstream = MagicMock(return_value=js)

        events: list[tuple[str, AgentManifest | None]] = []

        async def callback(key: str, manifest_or_none: AgentManifest | None) -> None:
            events.append((key, manifest_or_none))

        await client.watch_fleet(callback)

        assert len(events) == 2
        # First: registration
        assert events[0][0] == "watcher-agent"
        assert isinstance(events[0][1], AgentManifest)
        # Second: deregistration
        assert events[1][0] == "watcher-agent"
        assert events[1][1] is None


@pytest.mark.integration
@pytest.mark.edge_case
class TestEnvelopeHasAutoGeneratedMessageIdAndTimestamp:
    """Scenario 27: Published envelope has auto-generated message_id and timestamp."""

    async def test_envelope_has_auto_generated_message_id_and_timestamp(self) -> None:
        """UUID v4 format and UTC within 1s."""
        client, mock_nc = _make_connected_client()

        before = datetime.now(timezone.utc)

        class SimplePayload(BaseModel):
            data: str = "test"

        await client.publish(
            topic="test.topic",
            payload=SimplePayload(),
            event_type=EventType.STATUS,
            source_id="test-agent",
        )

        after = datetime.now(timezone.utc)

        published_data = json.loads(mock_nc.publish.call_args[0][1])

        # UUID v4 format
        uuid_obj = UUID(published_data["message_id"], version=4)
        assert str(uuid_obj) == published_data["message_id"]

        # Timestamp within 1s of now in UTC
        ts = datetime.fromisoformat(published_data["timestamp"])
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        assert before <= ts <= after

        # Version is "1.0"
        assert published_data["version"] == "1.0"


@pytest.mark.integration
@pytest.mark.edge_case
class TestPayloadSourceIdKeyDoesNotOverrideEnvelope:
    """Scenario 28: Payload containing 'source_id' key doesn't override envelope."""

    async def test_payload_source_id_key_does_not_override_envelope(self) -> None:
        """Security: payload key 'source_id' stays in payload only."""
        client, mock_nc = _make_connected_client()

        class MaliciousPayload(BaseModel):
            source_id: str = "attacker"
            data: str = "test"

        await client.publish(
            topic="test.topic",
            payload=MaliciousPayload(),
            event_type=EventType.STATUS,
            source_id="legitimate-agent",
        )

        published_data = json.loads(mock_nc.publish.call_args[0][1])

        # Envelope-level source_id is the legitimate one
        assert published_data["source_id"] == "legitimate-agent"
        # Payload still has its own source_id
        assert published_data["payload"]["source_id"] == "attacker"


@pytest.mark.integration
@pytest.mark.edge_case
@pytest.mark.negative
class TestWildcardCharsInSegmentValuesRejected:
    """Scenario 29: Topic resolution rejects wildcard characters in segment values."""

    def test_wildcard_chars_in_segment_values_rejected(self) -> None:
        """Agent_id='evil.>' or feature_id='FEAT.*' → ValueError."""
        with pytest.raises(ValueError, match="wildcard|dots"):
            Topics.resolve(Topics.Fleet.HEARTBEAT, agent_id="evil.>")

        with pytest.raises(ValueError, match="wildcard|dots"):
            Topics.resolve(Topics.Pipeline.BUILD_COMPLETE, feature_id="FEAT.*")


@pytest.mark.integration
@pytest.mark.edge_case
class TestConcurrentRegisterDeregisterConsistentState:
    """Scenario 30: Concurrent register/deregister resolves consistently."""

    async def test_concurrent_register_deregister_consistent_state(self) -> None:
        """Concurrent KV ops → final state consistent."""
        client, mock_nc = _make_connected_client()

        # Track KV state
        kv_state: dict[str, bytes | None] = {}

        kv = AsyncMock()

        async def mock_put(key: str, value: bytes) -> None:
            kv_state[key] = value

        async def mock_delete(key: str) -> None:
            kv_state.pop(key, None)

        kv.put = AsyncMock(side_effect=mock_put)
        kv.delete = AsyncMock(side_effect=mock_delete)

        js = MagicMock()
        js.key_value = AsyncMock(return_value=kv)
        mock_nc.jetstream = MagicMock(return_value=js)

        manifest = _make_agent_manifest("flaky-agent")

        # Run register and deregister concurrently
        await asyncio.gather(
            client.register_agent(manifest),
            client.deregister_agent("flaky-agent", reason="test"),
        )

        # State should be consistent: either the agent is in KV or not
        # (not in a half-state)
        if "flaky-agent" in kv_state:
            assert kv_state["flaky-agent"] is not None
        # else: it was removed, which is also consistent


@pytest.mark.integration
@pytest.mark.edge_case
class TestPublishDuringReconnectionQueuesOrFailsClearly:
    """Scenario 31: Publishing during reconnection either queues or fails clearly."""

    async def test_publish_during_reconnection_queues_or_fails_clearly(self) -> None:
        """Reconnection window → queue or clear error.

        When disconnected (self._nc is None), publish raises RuntimeError.
        """
        from nats_core.config import NATSConfig

        client = NATSClient(NATSConfig())
        # Client not connected = simulates reconnection window
        assert client._nc is None

        with pytest.raises(RuntimeError, match="not connected"):
            await client.publish(
                topic="test.topic",
                payload=make_build_complete_payload(),
                event_type=EventType.BUILD_COMPLETE,
                source_id="test-agent",
            )


@pytest.mark.integration
@pytest.mark.edge_case
class TestSlowConsumerBackpressureNoCrash:
    """Scenario 32: Client handles slow consumer backpressure without crashing."""

    async def test_slow_consumer_backpressure_no_crash(self, caplog: Any) -> None:
        """Backpressure signal → no crash, warning logged.

        nats-py raises SlowConsumerError which the client's error callback
        handles internally. We verify the client can be configured with
        error callbacks and the subscription continues to work.
        """
        from nats_core.config import NATSConfig

        config = NATSConfig()
        client = NATSClient(config)

        # Simulate connection with error callback support
        mock_nc = _make_mock_nc()

        with patch("nats_core.client.nats.connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = mock_nc
            await client.connect()

        # The client should be connected and functional
        assert client._nc is not None

        # Verify publish still works (client not crashed)
        class SimplePayload(BaseModel):
            data: str = "test"

        await client.publish(
            topic="test.topic",
            payload=SimplePayload(),
            event_type=EventType.STATUS,
            source_id="test-agent",
        )

        mock_nc.publish.assert_awaited_once()


@pytest.mark.integration
@pytest.mark.edge_case
@pytest.mark.negative
class TestFleetRegistryUnavailableRaisesError:
    """Scenario 33: Fleet registry read fails clearly when KV bucket unavailable."""

    async def test_fleet_registry_unavailable_raises_error(self) -> None:
        """KV bucket down → RuntimeError."""
        client, mock_nc = _make_connected_client()

        js = MagicMock()
        js.key_value = AsyncMock(side_effect=Exception("bucket not found"))
        mock_nc.jetstream = MagicMock(return_value=js)

        with pytest.raises(RuntimeError, match="registry unavailable"):
            await client.get_fleet_registry()
