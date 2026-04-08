"""NATSClient — async client for publish / subscribe over NATS.

Wraps the nats-py library with typed envelope construction, project-scoped
topic prefixing, and safe JSON deserialisation in the subscriber path.
Also provides fleet convenience methods (register, deregister, heartbeat,
fleet registry) and the ``NATSKVManifestRegistry`` backed by JetStream KV.
"""

from __future__ import annotations

import fnmatch
import json
import logging
import uuid
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import Any

import nats
import nats.aio.client
import nats.aio.subscription
import nats.errors
from pydantic import BaseModel, ValidationError

from nats_core.config import NATSConfig
from nats_core.envelope import EventType, MessageEnvelope
from nats_core.events._fleet import AgentDeregistrationPayload, AgentHeartbeatPayload
from nats_core.manifest import AgentManifest, ManifestRegistry
from nats_core.topics import Topics

logger = logging.getLogger(__name__)

_KV_BUCKET_NAME = "agent-registry"


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

    # ------------------------------------------------------------------
    # Fleet convenience methods
    # ------------------------------------------------------------------

    async def _get_kv_bucket(self) -> Any:
        """Get or create the agent-registry KV bucket.

        Returns:
            A NATS JetStream KV bucket handle.

        Raises:
            RuntimeError: If the client is not connected or bucket is unavailable.
        """
        if self._nc is None:
            msg = "client is not connected"
            raise RuntimeError(msg)

        try:
            js = self._nc.jetstream()
            return await js.key_value(_KV_BUCKET_NAME)
        except Exception as exc:
            msg = "registry unavailable"
            raise RuntimeError(msg) from exc

    async def register_agent(self, manifest: AgentManifest) -> None:
        """Publish manifest to ``fleet.register`` and store in KV bucket.

        Args:
            manifest: The agent manifest to register.

        Raises:
            RuntimeError: If the client is not connected.
        """
        payload_bytes = manifest.model_dump_json().encode()

        # 1. Publish to fleet.register topic
        await self.publish(
            topic=Topics.Fleet.REGISTER,
            payload=manifest,
            event_type=EventType.AGENT_REGISTER,
            source_id=manifest.agent_id,
        )

        # 2. Store in KV bucket
        kv = await self._get_kv_bucket()
        await kv.put(manifest.agent_id, payload_bytes)

    async def deregister_agent(self, agent_id: str, reason: str = "shutdown") -> None:
        """Publish deregistration to ``fleet.deregister`` and delete from KV.

        Args:
            agent_id: The agent identifier to deregister.
            reason: Human-readable reason for deregistration.

        Raises:
            RuntimeError: If the client is not connected.
        """
        payload = AgentDeregistrationPayload(agent_id=agent_id, reason=reason)

        # 1. Publish to fleet.deregister topic
        await self.publish(
            topic=Topics.Fleet.DEREGISTER,
            payload=payload,
            event_type=EventType.AGENT_DEREGISTER,
            source_id=agent_id,
        )

        # 2. Delete from KV (idempotent — ignore KeyNotFoundError)
        try:
            kv = await self._get_kv_bucket()
            await kv.delete(agent_id)
        except (KeyError, Exception):
            logger.debug("KV delete for '%s' was a no-op (key not found)", agent_id)

    async def heartbeat(self, heartbeat: AgentHeartbeatPayload) -> None:
        """Publish heartbeat to ``fleet.heartbeat.{agent_id}``.

        Args:
            heartbeat: The heartbeat payload containing agent status.

        Raises:
            RuntimeError: If the client is not connected.
        """
        topic = Topics.resolve(Topics.Fleet.HEARTBEAT, agent_id=heartbeat.agent_id)
        await self.publish(
            topic=topic,
            payload=heartbeat,
            event_type=EventType.AGENT_HEARTBEAT,
            source_id=heartbeat.agent_id,
        )

    async def get_fleet_registry(self) -> dict[str, AgentManifest]:
        """Read all registered agents from the ``agent-registry`` KV bucket.

        Returns:
            A dict mapping ``agent_id`` to ``AgentManifest``.

        Raises:
            RuntimeError: If the KV bucket is unavailable.
        """
        kv = await self._get_kv_bucket()
        result: dict[str, AgentManifest] = {}

        try:
            keys = await kv.keys()
        except Exception as exc:
            msg = "registry unavailable"
            raise RuntimeError(msg) from exc

        for key in keys:
            entry = await kv.get(key)
            manifest = AgentManifest.model_validate_json(entry.value)
            result[manifest.agent_id] = manifest

        return result

    async def watch_fleet(
        self,
        callback: Callable[[str, AgentManifest | None], Awaitable[None]],
    ) -> None:
        """Watch the ``agent-registry`` KV for put/delete events.

        Calls ``callback(agent_id, manifest_or_none)`` for each change.
        This is a long-running coroutine — callers should wrap it in
        ``asyncio.create_task()``.

        Args:
            callback: Async function called with ``(key, manifest)`` for PUT events
                and ``(key, None)`` for DEL/PURGE events.

        Raises:
            RuntimeError: If the client is not connected or bucket unavailable.
        """
        kv = await self._get_kv_bucket()
        watcher = await kv.watch(">")

        async for entry in watcher:
            if entry.operation == "PUT":
                manifest = AgentManifest.model_validate_json(entry.value)
                await callback(entry.key, manifest)
            else:
                # DEL or PURGE
                await callback(entry.key, None)

    async def call_agent_tool(
        self,
        agent_id: str,
        tool_name: str,
        params: dict[str, Any],
        timeout: float = 30.0,
    ) -> Any:
        """Invoke a tool on a remote agent via NATS request-reply.

        Publishes to agents.{agent_id}.tools.{tool_name} and awaits response.

        Args:
            agent_id: Target agent identifier.
            tool_name: Tool name from the agent's manifest.
            params: Tool parameters matching the tool's JSON Schema.
            timeout: Request timeout in seconds (default: 30.0).

        Returns:
            Deserialised response from the target agent (JSON-decoded).

        Raises:
            RuntimeError: If client is not connected.
            ValueError: If agent_id or tool_name contain wildcards or invalid characters.
            TimeoutError: If the agent does not respond within timeout.
        """
        if self._nc is None:
            msg = "client is not connected"
            raise RuntimeError(msg)

        topic = Topics.resolve(
            Topics.Agents.TOOLS, agent_id=agent_id, tool_name=tool_name
        )

        payload = json.dumps(params).encode()

        try:
            response = await self._nc.request(topic, payload, timeout=timeout)
        except (nats.errors.NoRespondersError, nats.errors.TimeoutError):
            msg = (
                f"agent '{agent_id}' did not respond to tool "
                f"'{tool_name}' within {timeout}s"
            )
            raise TimeoutError(msg)

        return json.loads(response.data)


# ---------------------------------------------------------------------------
# NATSKVManifestRegistry — JetStream KV-backed ManifestRegistry
# ---------------------------------------------------------------------------


class NATSKVManifestRegistry(ManifestRegistry):
    """NATS JetStream KV-backed implementation of :class:`ManifestRegistry`.

    Delegates all storage to the ``agent-registry`` KV bucket.
    ``find_by_intent`` and ``find_by_tool`` call :meth:`list_all` then
    filter in-process.

    Args:
        client: A connected ``NATSClient`` instance.
        bucket: KV bucket name (default: ``"agent-registry"``).
    """

    def __init__(self, client: NATSClient, bucket: str = _KV_BUCKET_NAME) -> None:
        self._client = client
        self._bucket = bucket

    async def _get_kv(self) -> Any:
        """Get the JetStream KV bucket handle.

        Returns:
            A NATS KV bucket handle.

        Raises:
            RuntimeError: If the underlying client is not connected.
        """
        if self._client._nc is None:
            msg = "client is not connected"
            raise RuntimeError(msg)

        js = self._client._nc.jetstream()
        return await js.key_value(self._bucket)

    async def register(self, manifest: AgentManifest) -> None:  # type: ignore[override]
        """Store a manifest in the KV bucket keyed by ``agent_id``.

        Args:
            manifest: The agent manifest to register.
        """
        kv = await self._get_kv()
        await kv.put(manifest.agent_id, manifest.model_dump_json().encode())

    async def deregister(self, agent_id: str) -> None:  # type: ignore[override]
        """Remove a manifest from the KV bucket by ``agent_id``.

        If the key is not present, this method is a no-op.

        Args:
            agent_id: The agent identifier to remove.
        """
        kv = await self._get_kv()
        try:
            await kv.delete(agent_id)
        except KeyError:
            pass

    async def get(self, agent_id: str) -> AgentManifest | None:  # type: ignore[override]
        """Retrieve a manifest from the KV bucket by ``agent_id``.

        Args:
            agent_id: The agent identifier to look up.

        Returns:
            The matching manifest, or ``None`` if not found.
        """
        kv = await self._get_kv()
        try:
            entry = await kv.get(agent_id)
            return AgentManifest.model_validate_json(entry.value)
        except KeyError:
            return None

    async def list_all(self) -> list[AgentManifest]:
        """Retrieve all manifests from the KV bucket.

        Returns:
            A list of all registered agent manifests.
        """
        kv = await self._get_kv()
        try:
            keys = await kv.keys()
        except Exception:
            return []

        results: list[AgentManifest] = []
        for key in keys:
            entry = await kv.get(key)
            manifest = AgentManifest.model_validate_json(entry.value)
            results.append(manifest)
        return results

    async def find_by_intent(self, intent: str) -> list[AgentManifest]:  # type: ignore[override]
        """Return all manifests whose intent patterns match *intent*.

        Uses :func:`fnmatch.fnmatch` for glob-style matching, consistent
        with :class:`InMemoryManifestRegistry`.

        Args:
            intent: The intent string to match against registered patterns.

        Returns:
            A list of manifests with at least one matching intent pattern.
        """
        all_manifests = await self.list_all()
        results: list[AgentManifest] = []
        for manifest in all_manifests:
            for cap in manifest.intents:
                if fnmatch.fnmatch(intent, cap.pattern):
                    results.append(manifest)
                    break
        return results

    async def find_by_tool(self, tool_name: str) -> list[AgentManifest]:  # type: ignore[override]
        """Return all manifests that expose a tool named *tool_name*.

        Args:
            tool_name: The tool name to search for.

        Returns:
            A list of manifests that include the named tool.
        """
        all_manifests = await self.list_all()
        results: list[AgentManifest] = []
        for manifest in all_manifests:
            for tool in manifest.tools:
                if tool.name == tool_name:
                    results.append(manifest)
                    break
        return results
