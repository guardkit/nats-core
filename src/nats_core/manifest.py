"""Agent manifest and capability declarations for the fleet registry.

Defines the capability models (IntentCapability, ToolCapability) and the
AgentManifest published to ``fleet.register`` as the agent_register event
payload per DDR-002.  AgentManifest enforces kebab-case ``agent_id`` format
(ASSUM-008).

Also provides the ``ManifestRegistry`` abstract base class and the
``InMemoryManifestRegistry`` concrete implementation for looking up agents
by intent pattern or tool name.
"""

from __future__ import annotations

import abc
import fnmatch
import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class IntentCapability(BaseModel):
    """Declares an intent pattern that an agent can handle.

    Attributes:
        pattern: Glob or regex pattern the agent matches against incoming intents.
        signals: Optional keywords that boost matching confidence.
        confidence: Baseline confidence score for this intent (0.0–1.0).
        description: Human-readable description of the intent capability.
    """

    model_config = ConfigDict(extra="ignore")

    pattern: str = Field(min_length=1, description="Intent matching pattern")
    signals: list[str] = Field(
        default_factory=list,
        description="Keywords that boost matching confidence",
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Baseline confidence score for this intent",
    )
    description: str = Field(description="Human-readable description of the capability")


class ToolCapability(BaseModel):
    """Declares a tool that an agent exposes to the fleet.

    Attributes:
        name: Unique tool name within the agent.
        description: Human-readable description of the tool.
        parameters: JSON Schema describing the tool's input parameters.
        returns: Description of the return type.
        risk_level: Risk classification for approval gating.
        async_mode: Whether the tool executes asynchronously.
        requires_approval: Whether human approval is required before execution.
    """

    model_config = ConfigDict(extra="ignore")

    name: str = Field(min_length=1, description="Unique tool name within the agent")
    description: str = Field(description="Human-readable description of the tool")
    parameters: dict[str, Any] = Field(description="JSON Schema for tool input parameters")
    returns: str = Field(description="Description of the return type")
    risk_level: Literal["read_only", "mutating", "destructive"] = Field(
        default="read_only",
        description="Risk classification for approval gating",
    )
    async_mode: bool = Field(
        default=False,
        description="Whether the tool executes asynchronously",
    )
    requires_approval: bool = Field(
        default=False,
        description="Whether human approval is required before execution",
    )


class AgentManifest(BaseModel):
    """Full agent capability manifest published to ``fleet.register``.

    Serves as the payload for ``EventType.AGENT_REGISTER``.  The BDD spec
    refers to this as "AgentRegistrationPayload"; it is implemented as
    ``AgentManifest`` per DDR-002 which specifies publishing the full
    manifest directly.

    Attributes:
        agent_id: Kebab-case agent identifier (ASSUM-008).
        name: Human-readable agent name.
        version: Semantic version of the agent.
        intents: Intent patterns the agent can handle.
        tools: Tools the agent exposes.
        template: Agent template or archetype name.
        max_concurrent: Maximum concurrent tasks the agent can process.
        status: Current operational status.
        trust_tier: Trust classification for permission scoping.
        required_permissions: Permissions the agent needs to operate.
        container_id: Optional container or process identifier.
        metadata: Arbitrary key-value metadata.
    """

    model_config = ConfigDict(extra="ignore")

    agent_id: str = Field(
        pattern=r"^[a-z][a-z0-9-]*$",
        description="Kebab-case agent identifier",
    )
    name: str = Field(description="Human-readable agent name")
    version: str = Field(default="0.1.0", description="Semantic version of the agent")
    intents: list[IntentCapability] = Field(
        default_factory=list,
        description="Intent patterns the agent can handle",
    )
    tools: list[ToolCapability] = Field(
        default_factory=list,
        description="Tools the agent exposes",
    )
    template: str = Field(description="Agent template or archetype name")
    max_concurrent: int = Field(
        default=1,
        ge=1,
        description="Maximum concurrent tasks the agent can process",
    )
    status: Literal["ready", "starting", "degraded"] = Field(
        default="ready",
        description="Current operational status",
    )
    trust_tier: Literal["core", "specialist", "extension"] = Field(
        default="specialist",
        description="Trust classification for permission scoping",
    )
    required_permissions: list[str] = Field(
        default_factory=list,
        description="Permissions the agent needs to operate",
    )
    container_id: str | None = Field(
        default=None,
        description="Optional container or process identifier",
    )
    metadata: dict[str, str] = Field(
        default_factory=dict,
        description="Arbitrary key-value metadata",
    )

    @field_validator("metadata")
    @classmethod
    def metadata_size_must_not_exceed_64kb(cls, v: dict[str, str]) -> dict[str, str]:
        """Reject metadata payloads larger than 64KB when JSON-encoded.

        Args:
            v: The metadata dictionary to validate.

        Returns:
            The validated metadata dictionary.

        Raises:
            ValueError: If the JSON-encoded metadata exceeds 65536 bytes.
        """
        if len(json.dumps(v).encode()) > 65536:
            msg = "metadata exceeds the maximum allowed size of 64KB"
            raise ValueError(msg)
        return v


# ---------------------------------------------------------------------------
# Registry abstraction
# ---------------------------------------------------------------------------


class ManifestRegistry(abc.ABC):
    """Abstract base class for agent manifest registries.

    Subclasses must implement all abstract methods to provide storage,
    retrieval, and lookup of :class:`AgentManifest` instances.
    """

    @abc.abstractmethod
    def register(self, manifest: AgentManifest) -> None:
        """Store a manifest keyed by its ``agent_id``.

        Args:
            manifest: The agent manifest to register.
        """

    @abc.abstractmethod
    def deregister(self, agent_id: str) -> None:
        """Remove a manifest by ``agent_id``.

        If the ``agent_id`` is not present, this method is a no-op.

        Args:
            agent_id: The agent identifier to remove.
        """

    @abc.abstractmethod
    def get(self, agent_id: str) -> AgentManifest | None:
        """Retrieve a manifest by ``agent_id``.

        Args:
            agent_id: The agent identifier to look up.

        Returns:
            The matching manifest, or ``None`` if not found.
        """

    @abc.abstractmethod
    def find_by_intent(self, intent: str) -> list[AgentManifest]:
        """Return all manifests whose intent patterns match *intent*.

        Args:
            intent: The intent string to match against registered patterns.

        Returns:
            A list of manifests with at least one matching intent pattern.
        """

    @abc.abstractmethod
    def find_by_tool(self, tool_name: str) -> list[AgentManifest]:
        """Return all manifests that expose a tool named *tool_name*.

        Args:
            tool_name: The tool name to search for.

        Returns:
            A list of manifests that include the named tool.
        """


class InMemoryManifestRegistry(ManifestRegistry):
    """In-memory implementation of :class:`ManifestRegistry`.

    Stores manifests in a plain dictionary keyed by ``agent_id``.
    Suitable for testing and single-process deployments.
    """

    def __init__(self) -> None:
        self._store: dict[str, AgentManifest] = {}

    def register(self, manifest: AgentManifest) -> None:
        """Store a manifest keyed by its ``agent_id``.

        Args:
            manifest: The agent manifest to register.
        """
        self._store[manifest.agent_id] = manifest

    def deregister(self, agent_id: str) -> None:
        """Remove a manifest by ``agent_id``.

        If the ``agent_id`` is not present, this method is a no-op.

        Args:
            agent_id: The agent identifier to remove.
        """
        self._store.pop(agent_id, None)

    def get(self, agent_id: str) -> AgentManifest | None:
        """Retrieve a manifest by ``agent_id``.

        Args:
            agent_id: The agent identifier to look up.

        Returns:
            The matching manifest, or ``None`` if not found.
        """
        return self._store.get(agent_id)

    def find_by_intent(self, intent: str) -> list[AgentManifest]:
        """Return all manifests whose intent patterns match *intent*.

        Uses :func:`fnmatch.fnmatch` for glob-style matching so that
        patterns like ``software.*`` match ``software.build``.

        Args:
            intent: The intent string to match against registered patterns.

        Returns:
            A list of manifests with at least one matching intent pattern.
        """
        results: list[AgentManifest] = []
        for manifest in self._store.values():
            for cap in manifest.intents:
                if fnmatch.fnmatch(intent, cap.pattern):
                    results.append(manifest)
                    break
        return results

    def find_by_tool(self, tool_name: str) -> list[AgentManifest]:
        """Return all manifests that expose a tool named *tool_name*.

        Args:
            tool_name: The tool name to search for.

        Returns:
            A list of manifests that include the named tool.
        """
        results: list[AgentManifest] = []
        for manifest in self._store.values():
            for tool in manifest.tools:
                if tool.name == tool_name:
                    results.append(manifest)
                    break
        return results
