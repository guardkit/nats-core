"""NATS connection and environment configuration.

Provides :class:`NATSConfig`, a pydantic-settings model that reads
NATS-related configuration from environment variables (prefixed with
``NATS_``) and optional ``.env`` files.
"""

from __future__ import annotations

import pathlib
import urllib.parse
from typing import Any, Self

from pydantic import Field, SecretStr, field_validator, model_validator
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
    user: str | None = Field(
        default=None,
        description="Username for NATS user/password authentication",
    )
    password: SecretStr | None = Field(
        default=None,
        description="Password for NATS user/password authentication (masked in output)",
    )
    creds_file: str | None = Field(
        default=None,
        description="Path to NKey credentials file for NATS authentication",
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

    @field_validator("creds_file")
    @classmethod
    def creds_file_must_not_traverse(cls, v: str | None) -> str | None:
        """Validate that the credentials file path does not contain directory traversal.

        Args:
            v: The credentials file path to validate.

        Returns:
            The validated path string, or None if not set.

        Raises:
            ValueError: If the path contains ``..`` directory traversal.
        """
        if v is not None and ".." in pathlib.PurePosixPath(v).parts:
            msg = "creds_file must not contain '..' path traversal"
            raise ValueError(msg)
        return v

    @model_validator(mode="after")
    def auth_fields_are_consistent(self) -> Self:
        """Validate mutual-exclusivity rules for authentication fields.

        Rules:
            1. ``user`` and ``password`` must be provided together (both or neither).
            2. Password-based auth and ``creds_file`` are mutually exclusive.

        Returns:
            The validated model instance.

        Raises:
            ValueError: If auth field combinations are invalid.
        """
        has_user = self.user is not None
        has_password = self.password is not None
        has_creds = self.creds_file is not None

        if has_user != has_password:
            msg = "user and password must be provided together"
            raise ValueError(msg)

        if has_password and has_creds:
            msg = "password auth and creds_file are mutually exclusive"
            raise ValueError(msg)

        return self

    def to_connect_kwargs(self) -> dict[str, Any]:
        """Build keyword arguments for ``nats.aio.client.Client.connect()``.

        Maps NATSConfig fields to the parameter names expected by the
        nats-py client library.  Authentication fields are included only
        when they are set.

        Returns:
            A dict suitable for unpacking into ``Client.connect(**kwargs)``.
        """
        kwargs: dict[str, Any] = {
            "servers": [self.url],
            "connect_timeout": self.connect_timeout,
            "reconnect_time_wait": self.reconnect_time_wait,
            "max_reconnect_attempts": self.max_reconnect_attempts,
            "name": self.name,
        }

        if self.user is not None and self.password is not None:
            kwargs["user"] = self.user
            kwargs["password"] = self.password.get_secret_value()

        if self.creds_file is not None:
            kwargs["credentials"] = self.creds_file

        return kwargs
