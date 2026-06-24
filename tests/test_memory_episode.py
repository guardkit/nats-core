"""Tests for MemoryEpisodeV1 schema and MAX_EPISODE_BODY_BYTES constant."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from nats_core import MemoryEpisodeV1
from nats_core.events import MAX_EPISODE_BODY_BYTES, MemoryEpisodeV1 as EventsMemoryEpisodeV1


def test_max_episode_body_bytes_constant() -> None:
    """Test that MAX_EPISODE_BODY_BYTES is defined correctly."""
    assert MAX_EPISODE_BODY_BYTES == 900 * 1024
    assert MAX_EPISODE_BODY_BYTES == 921600


def test_memory_episode_imports() -> None:
    """Test that MemoryEpisodeV1 can be imported from both nats_core and nats_core.events."""
    # Should import from top-level
    from nats_core import MemoryEpisodeV1 as TopLevelEpisode

    # Should import from events submodule
    from nats_core.events import MemoryEpisodeV1 as EventsEpisode

    # Both should be the same class
    assert TopLevelEpisode is EventsEpisode
    assert TopLevelEpisode is MemoryEpisodeV1


def test_memory_episode_required_fields() -> None:
    """Test that MemoryEpisodeV1 requires all mandatory fields."""
    # Valid minimal episode
    episode = MemoryEpisodeV1(
        episode_id="e1",
        project_id="finproxy",
        episode_type="feature_outcome",
        content_format="markdown",
        body="Test episode content",
    )

    assert episode.episode_id == "e1"
    assert episode.project_id == "finproxy"
    assert episode.episode_type == "feature_outcome"
    assert episode.content_format == "markdown"
    assert episode.body == "Test episode content"


def test_memory_episode_missing_required_field() -> None:
    """Test that missing required fields raise ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        MemoryEpisodeV1(
            episode_id="e1",
            project_id="finproxy",
            # Missing episode_type
            content_format="markdown",
            body="content",
        )
    assert "episode_type" in str(exc_info.value)


def test_episode_type_nats_safe_identifier_valid() -> None:
    """Test that valid NATS-safe identifiers are accepted."""
    valid_types = [
        "feature_outcome",
        "structured_json",
        "agent-heartbeat",
        "task123",
        "A1B2C3",
        "test_type",
        "test-type",
    ]

    for episode_type in valid_types:
        episode = MemoryEpisodeV1(
            episode_id="e1",
            project_id="finproxy",
            episode_type=episode_type,
            content_format="text",
            body="content",
        )
        assert episode.episode_type == episode_type


def test_episode_type_nats_safe_identifier_invalid() -> None:
    """Test that invalid NATS-safe identifiers are rejected."""
    invalid_types = [
        "evil.>",  # Contains dot and wildcard
        "bad type",  # Contains space
        "test.type",  # Contains dot
        "type>wild",  # Contains >
        "type*wild",  # Contains *
        ".leading",  # Starts with dot
        "-leading",  # Starts with dash
        "_leading",  # Starts with underscore
        "",  # Empty string
    ]

    for episode_type in invalid_types:
        with pytest.raises(ValidationError) as exc_info:
            MemoryEpisodeV1(
                episode_id="e1",
                project_id="finproxy",
                episode_type=episode_type,
                content_format="text",
                body="x",
            )
        error_str = str(exc_info.value)
        assert "episode_type" in error_str.lower()


def test_memory_episode_optional_fields() -> None:
    """Test that optional fields work correctly."""
    now = datetime.now(timezone.utc)

    episode = MemoryEpisodeV1(
        episode_id="e1",
        project_id="finproxy",
        episode_type="structured_json",
        content_format="json",
        body='{"key": "value"}',
        payload_type="agent.heartbeat",
        source_ref="github.com/org/repo#123",
        name="Test Episode",
        source="test-agent",
        occurred_at=now,
        published_at=now,
        ingest_hints={"priority": "high", "tags": ["test"]},
    )

    assert episode.payload_type == "agent.heartbeat"
    assert episode.source_ref == "github.com/org/repo#123"
    assert episode.name == "Test Episode"
    assert episode.source == "test-agent"
    assert episode.occurred_at == now
    assert episode.published_at == now
    assert episode.ingest_hints == {"priority": "high", "tags": ["test"]}


def test_memory_episode_optional_fields_default_none() -> None:
    """Test that optional fields default to None."""
    episode = MemoryEpisodeV1(
        episode_id="e1",
        project_id="finproxy",
        episode_type="feature_outcome",
        content_format="text",
        body="content",
    )

    assert episode.payload_type is None
    assert episode.source_ref is None
    assert episode.name is None
    assert episode.source is None
    assert episode.occurred_at is None
    assert episode.published_at is None
    assert episode.ingest_hints is None


def test_no_group_id_field() -> None:
    """Test that group_id is not a field (it was dropped)."""
    episode = MemoryEpisodeV1(
        episode_id="e1",
        project_id="finproxy",
        episode_type="feature_outcome",
        content_format="text",
        body="content",
    )

    # group_id should not be in model fields (access from class, not instance)
    assert "group_id" not in MemoryEpisodeV1.model_fields
    assert not hasattr(episode, "group_id")


def test_content_format_is_string_not_enum() -> None:
    """Test that content_format is a plain string, not an enum."""
    # Should accept any string, not just predefined values
    formats = ["json", "markdown", "text", "html", "custom_format", "anything"]

    for fmt in formats:
        episode = MemoryEpisodeV1(
            episode_id="e1",
            project_id="finproxy",
            episode_type="test",
            content_format=fmt,
            body="content",
        )
        assert episode.content_format == fmt


def test_extra_fields_ignored_forward_compat() -> None:
    """Test that extra unknown fields are ignored (forward compatibility)."""
    json_data = {
        "episode_id": "e1",
        "project_id": "finproxy",
        "episode_type": "feature_outcome",
        "content_format": "markdown",
        "body": "content",
        "unknown_field": "should be ignored",
        "future_feature": 123,
    }

    episode = MemoryEpisodeV1.model_validate(json_data)

    # Extra fields should not be present
    assert not hasattr(episode, "unknown_field")
    assert not hasattr(episode, "future_feature")

    # Required fields should be present
    assert episode.episode_id == "e1"


def test_model_validate_json_with_extra_fields() -> None:
    """Test that model_validate_json drops unknown keys."""
    json_str = """{
        "episode_id": "e1",
        "project_id": "finproxy",
        "episode_type": "test",
        "content_format": "json",
        "body": "content",
        "extra_key": "ignored"
    }"""

    episode = MemoryEpisodeV1.model_validate_json(json_str)

    assert episode.episode_id == "e1"
    assert not hasattr(episode, "extra_key")


def test_episode_id_min_length() -> None:
    """Test that episode_id requires min_length=1."""
    with pytest.raises(ValidationError) as exc_info:
        MemoryEpisodeV1(
            episode_id="",  # Empty string
            project_id="finproxy",
            episode_type="test",
            content_format="text",
            body="content",
        )
    assert "episode_id" in str(exc_info.value)


def test_project_id_min_length() -> None:
    """Test that project_id requires min_length=1."""
    with pytest.raises(ValidationError) as exc_info:
        MemoryEpisodeV1(
            episode_id="e1",
            project_id="",  # Empty string
            episode_type="test",
            content_format="text",
            body="content",
        )
    assert "project_id" in str(exc_info.value)


def test_all_fields_have_descriptions() -> None:
    """Test that all fields have Field(description=...) configured."""
    for field_name, field_info in MemoryEpisodeV1.model_fields.items():
        assert (
            field_info.description is not None
        ), f"Field {field_name} is missing a description"
        assert len(field_info.description) > 0, f"Field {field_name} has an empty description"


def test_model_config_extra_ignore() -> None:
    """Test that model_config is set to ignore extra fields."""
    # This is tested indirectly by test_extra_fields_ignored_forward_compat,
    # but we also verify the config directly
    assert MemoryEpisodeV1.model_config.get("extra") == "ignore"
