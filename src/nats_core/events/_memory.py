"""Memory episode event schema for cross-repo contract."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# 900 KB, binary (matches the 64KB == 65536 convention in manifest.py).
# Sits ~148KB below the NATS default 1MB max_payload, leaving headroom for the
# subject + Nats-Msg-Id header. Guard is enforced by publish_episode (TASK-MEP-003).
MAX_EPISODE_BODY_BYTES = 900 * 1024  # 921600


class MemoryEpisodeV1(BaseModel):
    """Canonical framework-neutral memory episode (the cross-repo write contract).

    This model defines the authoritative schema for memory episodes published to NATS
    and consumed by the fleet-memory relay. It reconciles previous definitions into
    a single cross-repo contract.

    The model uses `extra="ignore"` for forward compatibility, allowing unknown fields
    to be dropped during validation.
    """

    model_config = ConfigDict(extra="ignore")  # forward-compat: unknown keys survive

    episode_id: str = Field(
        min_length=1,
        description="Unique episode identifier; must match Nats-Msg-Id header for deduplication",
    )

    project_id: str = Field(
        min_length=1,
        description="Project identifier for subject partition; renamed from relay's 'project'",
    )

    episode_type: str = Field(
        min_length=1,
        pattern=r"^[a-zA-Z0-9][a-zA-Z0-9\-_]*$",
        description="Coarse source category; NATS-safe identifier used as subject segment",
    )

    content_format: str = Field(
        description="Content format indicator (json/markdown/text); not an enum for flexibility",
    )

    body: str = Field(
        description="The episode content payload",
    )

    payload_type: str | None = Field(
        default=None,
        description="Typed-payload-registry key for JSON path resolution",
    )

    source_ref: str | None = Field(
        default=None,
        description="Source reference identifier (e.g., commit SHA, URL)",
    )

    name: str | None = Field(
        default=None,
        description="Human-readable episode name or title",
    )

    source: str | None = Field(
        default=None,
        description="Source system or agent identifier",
    )

    occurred_at: datetime | None = Field(
        default=None,
        description="Timestamp when the event occurred",
    )

    published_at: datetime | None = Field(
        default=None,
        description="Timestamp when the episode was published to NATS",
    )

    ingest_hints: dict[str, Any] | None = Field(
        default=None,
        description="Optional metadata hints for downstream ingestion processing",
    )
