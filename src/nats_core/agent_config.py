"""Agent runtime configuration models.

Provides :class:`AgentConfig`, a pydantic-settings model that aggregates
LLM endpoints (:class:`ModelConfig`), knowledge graph settings
(:class:`GraphitiConfig`), NATS connection (:class:`NATSConfig`), and
operational parameters such as heartbeat intervals and task timeouts.

``AgentConfig`` is LOCAL to each agent — it is never published to
``fleet.register``.
"""

from __future__ import annotations

from typing import Self

from pydantic import BaseModel, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from nats_core.config import NATSConfig


class ModelConfig(BaseModel):
    """LLM endpoint configuration nested within :class:`AgentConfig`.

    Attributes:
        reasoning_model: Model name for reasoning/orchestration tasks (required).
        reasoning_endpoint: API endpoint for the reasoning model.
        implementation_model: Optional model name for implementation tasks.
        implementation_endpoint: Optional endpoint for the implementation model.
        embedding_model: Optional model name for embeddings.
        embedding_endpoint: Optional endpoint for the embedding model.
    """

    reasoning_model: str = Field(
        min_length=1,
        description="Model name for reasoning/orchestration tasks",
    )
    reasoning_endpoint: str = Field(
        default="",
        description="API endpoint for the reasoning model (empty = provider default)",
    )
    implementation_model: str | None = Field(
        default=None,
        description="Optional model name for implementation tasks",
    )
    implementation_endpoint: str | None = Field(
        default=None,
        description="Optional endpoint for the implementation model",
    )
    embedding_model: str | None = Field(
        default=None,
        description="Optional model name for embeddings",
    )
    embedding_endpoint: str | None = Field(
        default=None,
        description="Optional endpoint for the embedding model",
    )


class GraphitiConfig(BaseModel):
    """Knowledge graph connection settings nested within :class:`AgentConfig`.

    Attributes:
        endpoint: FalkorDB bolt endpoint URL.
        default_group_ids: Default group IDs for knowledge graph queries.
    """

    endpoint: str = Field(
        default="bolt://localhost:7687",
        description="FalkorDB bolt endpoint URL",
    )
    default_group_ids: list[str] = Field(
        default_factory=lambda: ["appmilla-fleet"],
        description="Default group IDs for knowledge graph queries",
    )


class AgentConfig(BaseSettings):
    """Agent runtime configuration loaded from environment variables.

    Reads values from environment variables prefixed with ``AGENT_``
    and supports nested models via ``__`` delimiter (e.g.
    ``AGENT_MODELS__REASONING_MODEL``).

    This configuration is LOCAL to each agent and must never be
    published to ``fleet.register``.

    Attributes:
        models: LLM endpoint configuration (required — no default).
        graphiti: Optional knowledge graph connection settings.
        nats: NATS connection configuration.
        langsmith_project: Optional LangSmith tracing project name.
        langsmith_api_key: Optional LangSmith API key.
        heartbeat_interval_seconds: Interval between agent heartbeats.
        heartbeat_timeout_seconds: Liveness detection timeout.
        max_task_timeout_seconds: Maximum task execution timeout.
        gemini_api_key: Optional Google Gemini API key.
        anthropic_api_key: Optional Anthropic API key.
        openai_api_key: Optional OpenAI API key.
    """

    model_config = SettingsConfigDict(
        env_prefix="AGENT_",
        env_nested_delimiter="__",
    )

    models: ModelConfig = Field(
        description="LLM endpoint configuration (required — no default)",
    )
    graphiti: GraphitiConfig | None = Field(
        default=None,
        description="Optional knowledge graph connection settings",
    )
    nats: NATSConfig = Field(
        default_factory=NATSConfig,
        description="NATS connection configuration",
    )
    langsmith_project: str | None = Field(
        default=None,
        description="Optional LangSmith tracing project name",
    )
    langsmith_api_key: SecretStr | None = Field(
        default=None,
        description="Optional LangSmith API key",
    )
    heartbeat_interval_seconds: int = Field(
        default=30,
        ge=1,
        description="Interval between agent heartbeats in seconds",
    )
    heartbeat_timeout_seconds: int = Field(
        default=90,
        ge=1,
        description="Liveness detection timeout in seconds",
    )
    max_task_timeout_seconds: int = Field(
        default=600,
        ge=1,
        description="Maximum task execution timeout in seconds",
    )
    gemini_api_key: SecretStr | None = Field(
        default=None,
        description="Optional Google Gemini API key",
    )
    anthropic_api_key: SecretStr | None = Field(
        default=None,
        description="Optional Anthropic API key",
    )
    openai_api_key: SecretStr | None = Field(
        default=None,
        description="Optional OpenAI API key",
    )

    @model_validator(mode="after")
    def heartbeat_timeout_exceeds_interval(self) -> Self:
        """Validate that heartbeat timeout exceeds heartbeat interval.

        The timeout must be strictly greater than the interval to allow
        at least one missed heartbeat before declaring an agent dead.

        Returns:
            The validated model instance.

        Raises:
            ValueError: If timeout is not greater than interval.
        """
        if self.heartbeat_timeout_seconds <= self.heartbeat_interval_seconds:
            msg = (
                f"heartbeat_timeout_seconds ({self.heartbeat_timeout_seconds}) "
                f"must be greater than heartbeat_interval_seconds "
                f"({self.heartbeat_interval_seconds})"
            )
            raise ValueError(msg)
        return self
