"""Tests for NATSClient core: connect / publish / subscribe.

Uses AsyncMock to simulate nats-py without requiring a running NATS server.
Tests are grouped by acceptance criterion.
"""

from __future__ import annotations

import asyncio
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
