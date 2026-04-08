"""NATSClient — async client for publish / subscribe over NATS.

Wraps the nats-py library with typed envelope construction, project-scoped
topic prefixing, and safe JSON deserialisation in the subscriber path.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import Any

import nats
import nats.aio.client
import nats.aio.subscription
from pydantic import BaseModel, ValidationError

from nats_core.config import NATSConfig
from nats_core.envelope import EventType, MessageEnvelope
from nats_core.topics import Topics

logger = logging.getLogger(__name__)


class NATSClient:
    """Async NATS client for the Jarvis fleet messaging layer.

    Provides connection lifecycle management, typed publish with automatic
    ``MessageEnvelope`` wrapping, and typed subscribe with safe JSON parsing.

    Args:
        config: NATS connection configuration.
        source_id: Identifier for this client instance used in envelope ``source_id``.
            Defaults to the ``config.name`` value.

    Raises:
        ValueError: If *source_id* is an empty string.
    """

    def __init__(self, config: NATSConfig, source_id: str | None = None) -> None:
        resolved_source_id = source_id if source_id is not None else config.name
        if not resolved_source_id or not resolved_source_id.strip():
            msg = "source_id must not be empty"
            raise ValueError(msg)

        self._config = config
        self._source_id = resolved_source_id
        self._nc: nats.aio.client.Client | None = None

    async def connect(self) -> None:
        """Establish a connection to the NATS server.

        Uses connection parameters from the ``NATSConfig`` supplied at
        construction time.  Calling ``connect()`` on an already-connected
        client raises ``RuntimeError``.

        Raises:
            RuntimeError: If the client is already connected.
        """
        if self._nc is not None:
            msg = "client is already connected"
            raise RuntimeError(msg)

        connect_kwargs = self._config.to_connect_kwargs()
        self._nc = await nats.connect(**connect_kwargs)

    async def disconnect(self) -> None:
        """Drain all subscriptions and close the connection.

        Safe to call when not connected (no-op).
        """
        if self._nc is None:
            return

        nc = self._nc
        self._nc = None
        await nc.drain()
        await nc.close()

    async def publish(
        self,
        topic: str,
        payload: BaseModel,
        event_type: EventType,
        source_id: str,
        project: str | None = None,
        correlation_id: str | None = None,
    ) -> None:
        """Publish a message wrapped in a ``MessageEnvelope``.

        Args:
            topic: Resolved NATS subject string (no placeholders).
            payload: Pydantic model whose fields become ``envelope.payload``.
            event_type: Event classification for the envelope.
            source_id: Originating agent/service identifier.
            project: Optional project scope; prefixes the topic when supplied.
            correlation_id: Optional correlation identifier for tracing.

        Raises:
            RuntimeError: If the client is not connected.
            ValueError: If *topic* contains leading or trailing whitespace.
        """
        if self._nc is None:
            msg = "client is not connected"
            raise RuntimeError(msg)

        if topic != topic.strip():
            msg = "topic must not contain leading or trailing whitespace"
            raise ValueError(msg)

        if project is not None:
            topic = Topics.for_project(project, topic)

        envelope = MessageEnvelope(
            message_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            version="1.0",
            source_id=source_id,
            event_type=event_type,
            project=project,
            correlation_id=correlation_id,
            payload=payload.model_dump(),
        )

        data = envelope.model_dump_json().encode()
        await self._nc.publish(topic, data)

    async def subscribe(
        self,
        topic: str,
        callback: Callable[[MessageEnvelope], Awaitable[None]],
    ) -> nats.aio.subscription.Subscription:
        """Subscribe to a NATS subject with envelope-aware deserialization.

        The internal callback parses incoming bytes as a ``MessageEnvelope``.
        Invalid JSON or validation failures are logged to stderr without
        raising, so the subscriber does not crash.

        Args:
            topic: NATS subject to subscribe to.
            callback: Async function called with each valid ``MessageEnvelope``.

        Returns:
            The nats-py ``Subscription`` object.

        Raises:
            RuntimeError: If the client is not connected.
        """
        if self._nc is None:
            msg = "client is not connected"
            raise RuntimeError(msg)

        async def _internal_callback(msg: Any) -> None:
            try:
                envelope = MessageEnvelope.model_validate_json(msg.data)
            except (ValidationError, ValueError) as exc:
                logger.error("Failed to parse NATS message as MessageEnvelope: %s", exc)
                return

            await callback(envelope)

        sub: nats.aio.subscription.Subscription = await self._nc.subscribe(
            topic, cb=_internal_callback
        )
        return sub
