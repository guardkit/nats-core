"""NATS connection and environment configuration.

Provides :class:`NATSConfig`, a pydantic-settings model that reads
NATS-related configuration from environment variables (prefixed with
``NATS_``) and optional ``.env`` files.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class NATSConfig(BaseSettings):
    """Configuration for NATS connectivity.

    Reads values from environment variables prefixed with ``NATS_``
    and falls back to an optional ``.env`` file.
    """

    model_config = SettingsConfigDict(env_prefix="NATS_", env_file=".env")
