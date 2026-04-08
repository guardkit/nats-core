"""Jarvis domain event payload schemas.

Covers Jarvis's intent classification and routing flow: intent classified,
dispatch, agent result, and notification.

``IntentClassifiedPayload.confidence`` uses ``Field(ge=0.0, le=1.0)`` —
the same range as ``IntentCapability.confidence`` in the fleet manifest.

This is a private module; public names are re-exported from
``nats_core.events``.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class IntentClassifiedPayload(BaseModel):
    """Payload for Jarvis intent classification events.

    Published on ``jarvis.intent.classified`` when Jarvis has determined
    the user's intent from free-text input and selected a target agent to
    handle it.

    Attributes:
        input_text: Original user text that was classified.
        intent: Classified intent label (e.g., ``"software.build"``).
        confidence: Classification confidence score between 0.0 and 1.0.
        target_agent: Identifier of the agent selected to handle the intent.
        correlation_id: Optional identifier linking related messages.
    """

    model_config = ConfigDict(extra="ignore")

    input_text: str = Field(
        description="Original user text that was classified",
    )
    intent: str = Field(
        description="Classified intent label (e.g., 'software.build')",
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Classification confidence score between 0.0 and 1.0",
    )
    target_agent: str = Field(
        description="Identifier of the agent selected to handle the intent",
    )
    correlation_id: str | None = Field(
        default=None,
        description="Optional identifier linking related messages",
    )


class DispatchPayload(BaseModel):
    """Payload for Jarvis dispatch events.

    Published on ``jarvis.dispatch.{agent}`` when Jarvis routes a
    classified intent to the selected target agent for execution.

    Attributes:
        intent: The classified intent label.
        target_agent: Identifier of the agent receiving the dispatch.
        input_text: Original user text being dispatched.
        correlation_id: Identifier linking related messages in this flow.
        context: Additional context data for the target agent.
    """

    model_config = ConfigDict(extra="ignore")

    intent: str = Field(
        description="The classified intent label",
    )
    target_agent: str = Field(
        description="Identifier of the agent receiving the dispatch",
    )
    input_text: str = Field(
        description="Original user text being dispatched",
    )
    correlation_id: str = Field(
        description="Identifier linking related messages in this flow",
    )
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context data for the target agent",
    )


class AgentResultPayload(BaseModel):
    """Payload for Jarvis agent result events.

    Published on ``jarvis.dispatch.{agent}`` (or a dedicated result topic)
    by the target agent after completing the dispatched intent.

    Attributes:
        agent_id: Identifier of the agent that produced the result.
        intent: The intent label that was executed.
        result: Key-value result data from the agent execution.
        correlation_id: Identifier linking this result to the original dispatch.
        success: Whether the agent completed the intent successfully.
    """

    model_config = ConfigDict(extra="ignore")

    agent_id: str = Field(
        description="Identifier of the agent that produced the result",
    )
    intent: str = Field(
        description="The intent label that was executed",
    )
    result: dict[str, Any] = Field(
        description="Key-value result data from the agent execution",
    )
    correlation_id: str = Field(
        description="Identifier linking this result to the original dispatch",
    )
    success: bool = Field(
        description="Whether the agent completed the intent successfully",
    )


class NotificationPayload(BaseModel):
    """Payload for Jarvis notification events.

    Published on ``jarvis.notification.{adapter}`` when Jarvis needs to
    send a notification through an adapter (e.g., Slack, email).

    Attributes:
        message: The notification message text.
        level: Severity level of the notification.
        adapter: Target adapter for delivery (e.g., ``"slack"``, ``"email"``).
        correlation_id: Optional identifier linking related messages.
    """

    model_config = ConfigDict(extra="ignore")

    message: str = Field(
        description="The notification message text",
    )
    level: Literal["info", "warning", "error"] = Field(
        default="info",
        description="Severity level of the notification",
    )
    adapter: str = Field(
        description="Target adapter for delivery (e.g., 'slack', 'email')",
    )
    correlation_id: str | None = Field(
        default=None,
        description="Optional identifier linking related messages",
    )
