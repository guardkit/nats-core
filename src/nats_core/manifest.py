"""Agent manifest and capability declarations for the fleet registry.

Defines the capability models (IntentCapability, ToolCapability) and the
AgentManifest published to ``fleet.register`` as the agent_register event
payload per DDR-002.  AgentManifest enforces kebab-case ``agent_id`` format
(ASSUM-008).
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class IntentCapability(BaseModel):
    """Declares an intent pattern that an agent can handle.

    Attributes:
        pattern: Glob or regex pattern the agent matches against incoming intents.
        signals: Optional keywords that boost matching confidence.
        confidence: Baseline confidence score for this intent (0.0–1.0).
        description: Human-readable description of the intent capability.
    """

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
