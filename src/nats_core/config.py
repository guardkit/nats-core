"""NATS connection and environment configuration.

Provides :class:`NATSConfig`, a pydantic-settings model that reads
NATS-related configuration from environment variables (prefixed with
``NATS_``) and optional ``.env`` files.
"""

from __future__ import annotations

import urllib.parse

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class NATSConfig(BaseSettings):
    """Configuration for NATS connectivity.

    Reads values from environment variables prefixed with ``NATS_``
    and falls back to an optional ``.env`` file.
    """

    model_config = SettingsConfigDict(env_prefix="NATS_", env_file=".env")

    url: str = Field(
        default="nats://localhost:4222",
        description="NATS server URL (nats:// or tls:// scheme)",
    )
    connect_timeout: float = Field(
        default=5.0,
        ge=0.0,
        description="Connection timeout in seconds",
    )
    reconnect_time_wait: float = Field(
        default=2.0,
        ge=0.0,
        description="Time to wait between reconnection attempts in seconds",
    )
    max_reconnect_attempts: int = Field(
        default=60,
        ge=0,
        description="Maximum number of reconnection attempts (0 means no retries)",
    )
    name: str = Field(
        default="nats-core-client",
        min_length=1,
        description="Client name used to identify this connection",
    )

    @field_validator("url")
    @classmethod
    def url_must_have_valid_scheme(cls, v: str) -> str:
        """Validate that the URL uses nats:// or tls:// scheme.

        Args:
            v: The URL string to validate.

        Returns:
            The validated URL string.

        Raises:
            ValueError: If the URL is empty or uses an unsupported scheme.
        """
        if not v:
            msg = "url must not be empty"
            raise ValueError(msg)
        parsed = urllib.parse.urlparse(v)
        if parsed.scheme not in ("nats", "tls"):
            msg = f"url scheme must be 'nats' or 'tls', got '{parsed.scheme}'"
            raise ValueError(msg)
        return v

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, v: str) -> str:
        """Validate that the client name is not blank or whitespace-only.

        Args:
            v: The name string to validate.

        Returns:
            The stripped name string.

        Raises:
            ValueError: If the name is blank or whitespace-only.
        """
        if not v.strip():
            msg = "name must not be blank"
            raise ValueError(msg)
        return v.strip()
