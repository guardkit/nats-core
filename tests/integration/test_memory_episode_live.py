"""Integration test for MemoryEpisodeV1 round-trip on GB10 (memory subject).

Proves that memory episodes can be published via NATSClient.publish_episode() and
consumed via a direct subscription to the memory.episode.{project_id}.{episode_type}
subject, with the subscriber decoding the raw body using
MemoryEpisodeV1.model_validate_json().

This test does NOT assert JetStream server-side deduplication and does NOT
require a pre-configured JetStream stream — it demonstrates the basic pub-sub
contract for the memory episode pathway.

Requires:
  - Live NATS on GB10 via Tailscale (100.84.90.91:4222)
  - RICH_NATS_PASSWORD set (via .env or env var)
  - pytest -m integration to run

TASK-MEP-005.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime

import nats.aio.client
import pytest

from nats_core.client import NATSClient
from nats_core.config import NATSConfig
from nats_core.events import MemoryEpisodeV1
from nats_core.topics import Topics

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="module")]


# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------


def _make_memory_episode(**overrides: object) -> MemoryEpisodeV1:
    """Create a MemoryEpisodeV1 with sensible defaults and optional overrides.

    Args:
        **overrides: Keyword arguments to override default field values.

    Returns:
        A MemoryEpisodeV1 instance with defaults plus caller-specified overrides.
    """
    defaults: dict[str, object] = {
        "episode_id": f"ep-{uuid.uuid4().hex[:12]}",
        "project_id": "test-project",
        "episode_type": "integration_test",
        "content_format": "markdown",
        "body": "Test episode content for integration testing",
        "name": "Test Episode",
        "source": "integration-test-suite",
        "occurred_at": datetime.now(UTC),
    }
    defaults.update(overrides)
    return MemoryEpisodeV1(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_memory_episode_publish_and_subscribe_round_trip(
    nats_client: nats.aio.client.Client,
) -> None:
    """Test that a memory episode can be published and consumed via direct subscription.

    Publishes via NATSClient.publish_episode(), subscribes to the resolved subject,
    and verifies that the subscriber receives the episode intact via
    MemoryEpisodeV1.model_validate_json(msg.data).
    """
    # Arrange: create a NATSClient and a test episode
    client = NATSClient(
        config=NATSConfig(url="nats://100.84.90.91:4222", name="test-memory-client"),
        source_id="integration-test",
    )
    client._nc = nats_client  # Reuse the fixture's connection

    episode = _make_memory_episode(
        episode_id=f"ep-test-{uuid.uuid4().hex[:8]}",
        project_id="test-project",
        episode_type="round_trip_test",
        body="Round-trip test content",
    )

    # Resolve the subject the episode will be published to
    subject = Topics.resolve(
        Topics.Memory.EPISODE,
        project_id=episode.project_id,
        episode_type=episode.episode_type,
    )

    # Subscribe before publishing
    received_episodes: list[MemoryEpisodeV1] = []

    async def on_message(msg: object) -> None:
        # Decode the raw message body as MemoryEpisodeV1
        decoded = MemoryEpisodeV1.model_validate_json(msg.data)  # type: ignore[attr-defined]
        received_episodes.append(decoded)

    await nats_client.subscribe(subject, cb=on_message)

    # Act: publish the episode
    await client.publish_episode(episode)

    # Wait for the message to arrive (give it up to 2 seconds)
    await asyncio.sleep(0.5)

    # Assert: verify the episode was received and matches the original
    assert len(received_episodes) == 1, "Expected exactly one episode to be received"

    received = received_episodes[0]
    assert received.episode_id == episode.episode_id
    assert received.project_id == episode.project_id
    assert received.episode_type == episode.episode_type
    assert received.content_format == episode.content_format
    assert received.body == episode.body
    assert received.name == episode.name
    assert received.source == episode.source


async def test_memory_episode_with_minimal_fields(
    nats_client: nats.aio.client.Client,
) -> None:
    """Test that a minimal memory episode (only required fields) round-trips correctly."""
    # Arrange: create a minimal episode with only required fields
    client = NATSClient(
        config=NATSConfig(url="nats://100.84.90.91:4222", name="test-memory-minimal"),
        source_id="integration-test-minimal",
    )
    client._nc = nats_client

    episode = MemoryEpisodeV1(
        episode_id=f"ep-minimal-{uuid.uuid4().hex[:8]}",
        project_id="minimal-project",
        episode_type="minimal_test",
        content_format="text",
        body="Minimal test content",
    )

    subject = Topics.resolve(
        Topics.Memory.EPISODE,
        project_id=episode.project_id,
        episode_type=episode.episode_type,
    )

    received_episodes: list[MemoryEpisodeV1] = []

    async def on_message(msg: object) -> None:
        decoded = MemoryEpisodeV1.model_validate_json(msg.data)  # type: ignore[attr-defined]
        received_episodes.append(decoded)

    await nats_client.subscribe(subject, cb=on_message)

    # Act: publish and wait
    await client.publish_episode(episode)
    await asyncio.sleep(0.5)

    # Assert: verify minimal fields are preserved
    assert len(received_episodes) == 1
    received = received_episodes[0]
    assert received.episode_id == episode.episode_id
    assert received.project_id == episode.project_id
    assert received.episode_type == episode.episode_type
    assert received.content_format == episode.content_format
    assert received.body == episode.body
    # Optional fields should be None
    assert received.name is None
    assert received.source is None
    assert received.payload_type is None
    assert received.source_ref is None


async def test_memory_episode_with_all_optional_fields(
    nats_client: nats.aio.client.Client,
) -> None:
    """Test that a memory episode with all optional fields round-trips correctly."""
    # Arrange: create an episode with all optional fields populated
    client = NATSClient(
        config=NATSConfig(url="nats://100.84.90.91:4222", name="test-memory-full"),
        source_id="integration-test-full",
    )
    client._nc = nats_client

    now = datetime.now(UTC)
    episode = MemoryEpisodeV1(
        episode_id=f"ep-full-{uuid.uuid4().hex[:8]}",
        project_id="full-project",
        episode_type="full_test",
        content_format="json",
        body='{"test": "data"}',
        payload_type="test.payload",
        source_ref="github.com/test/repo#abc123",
        name="Full Episode Test",
        source="test-agent-full",
        occurred_at=now,
        published_at=now,
        ingest_hints={"priority": "high", "tags": ["test", "integration"]},
    )

    subject = Topics.resolve(
        Topics.Memory.EPISODE,
        project_id=episode.project_id,
        episode_type=episode.episode_type,
    )

    received_episodes: list[MemoryEpisodeV1] = []

    async def on_message(msg: object) -> None:
        decoded = MemoryEpisodeV1.model_validate_json(msg.data)  # type: ignore[attr-defined]
        received_episodes.append(decoded)

    await nats_client.subscribe(subject, cb=on_message)

    # Act: publish and wait
    await client.publish_episode(episode)
    await asyncio.sleep(0.5)

    # Assert: verify all fields are preserved
    assert len(received_episodes) == 1
    received = received_episodes[0]
    assert received.episode_id == episode.episode_id
    assert received.project_id == episode.project_id
    assert received.episode_type == episode.episode_type
    assert received.content_format == episode.content_format
    assert received.body == episode.body
    assert received.payload_type == episode.payload_type
    assert received.source_ref == episode.source_ref
    assert received.name == episode.name
    assert received.source == episode.source
    assert received.occurred_at == episode.occurred_at
    assert received.published_at == episode.published_at
    assert received.ingest_hints == episode.ingest_hints


async def test_memory_episode_multiple_subscribers_same_message(
    nats_client: nats.aio.client.Client,
) -> None:
    """Test that multiple subscribers all receive the same published episode."""
    # Arrange: create a client and episode
    client = NATSClient(
        config=NATSConfig(url="nats://100.84.90.91:4222", name="test-memory-multi"),
        source_id="integration-test-multi",
    )
    client._nc = nats_client

    episode = _make_memory_episode(
        episode_id=f"ep-multi-{uuid.uuid4().hex[:8]}",
        project_id="multi-project",
        episode_type="multi_test",
    )

    subject = Topics.resolve(
        Topics.Memory.EPISODE,
        project_id=episode.project_id,
        episode_type=episode.episode_type,
    )

    # Set up multiple subscribers
    received_1: list[MemoryEpisodeV1] = []
    received_2: list[MemoryEpisodeV1] = []
    received_3: list[MemoryEpisodeV1] = []

    async def on_message_1(msg: object) -> None:
        decoded = MemoryEpisodeV1.model_validate_json(msg.data)  # type: ignore[attr-defined]
        received_1.append(decoded)

    async def on_message_2(msg: object) -> None:
        decoded = MemoryEpisodeV1.model_validate_json(msg.data)  # type: ignore[attr-defined]
        received_2.append(decoded)

    async def on_message_3(msg: object) -> None:
        decoded = MemoryEpisodeV1.model_validate_json(msg.data)  # type: ignore[attr-defined]
        received_3.append(decoded)

    await nats_client.subscribe(subject, cb=on_message_1)
    await nats_client.subscribe(subject, cb=on_message_2)
    await nats_client.subscribe(subject, cb=on_message_3)

    # Act: publish once
    await client.publish_episode(episode)
    await asyncio.sleep(0.5)

    # Assert: all three subscribers received the same episode
    assert len(received_1) == 1
    assert len(received_2) == 1
    assert len(received_3) == 1

    for received in [received_1[0], received_2[0], received_3[0]]:
        assert received.episode_id == episode.episode_id
        assert received.project_id == episode.project_id
        assert received.body == episode.body
