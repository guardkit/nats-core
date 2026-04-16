"""Topic Registry — single source of truth for all NATS subject strings.

Provides typed string constants organised into five namespace classes
(Pipeline, Agents, Fleet, Jarvis, System), template resolution via
``Topics.resolve()``, and multi-tenancy project scoping via
``Topics.for_project()``.

This module is pure-declarative: no I/O, no async, no external dependencies.
"""

from __future__ import annotations

import re

# Regex for extracting {placeholder} tokens from template strings.
_PLACEHOLDER_RE = re.compile(r"\{(\w+)\}")

# Identifier allowlist: starts with alphanumeric, then alphanumeric / hyphen / underscore.
# Use \A and \Z (not ^ and $) to avoid matching strings with trailing newlines.
_IDENTIFIER_RE = re.compile(r"\A[a-zA-Z0-9][a-zA-Z0-9\-_]*\Z")


def _validate_identifier(value: str, *, label: str) -> None:
    """Validate that *value* is a safe NATS subject segment.

    Args:
        value: The identifier string to validate.
        label: Human-readable name used in error messages (e.g. ``"feature_id"``).

    Raises:
        ValueError: If the identifier is empty, contains dots, spaces,
            wildcard tokens, control characters, or shell metacharacters.
    """
    if not value:
        msg = f"{label} must not be empty"
        raise ValueError(msg)
    if not _IDENTIFIER_RE.match(value):
        # Provide a targeted message for common single-cause violations.
        if "." in value:
            msg = f"{label} must not contain dots: {value!r}"
            raise ValueError(msg)
        if "*" in value or ">" in value:
            msg = f"{label} must not contain wildcard tokens: {value!r}"
            raise ValueError(msg)
        # Check if the *only* problem is whitespace (no other forbidden chars).
        stripped = value.replace(" ", "")
        if stripped and _IDENTIFIER_RE.match(stripped):
            msg = f"{label} must not contain spaces: {value!r}"
            raise ValueError(msg)
        msg = f"{label} contains invalid characters: {value!r}"
        raise ValueError(msg)


class _ImmutableNamespaceMeta(type):
    """Metaclass that prevents reassignment of class attributes on namespace classes."""

    def __setattr__(cls, name: str, value: object) -> None:
        if name in cls.__dict__:
            msg = f"cannot reassign {cls.__name__}.{name}"
            raise AttributeError(msg)
        super().__setattr__(name, value)


class Topics:
    """Registry of all NATS subject templates used by the fleet.

    Access topic templates as class attributes on the five inner namespace
    classes: ``Pipeline``, ``Agents``, ``Fleet``, ``Jarvis``, ``System``.

    Use :meth:`resolve` to substitute ``{placeholder}`` tokens and
    :meth:`for_project` to scope a subject to a project namespace.
    """

    # -- Namespace classes ---------------------------------------------------

    class Pipeline(metaclass=_ImmutableNamespaceMeta):
        """Pipeline domain topics."""

        # DEPRECATED: use BUILD_QUEUED
        FEATURE_PLANNED: str = "pipeline.feature-planned.{feature_id}"
        FEATURE_READY_FOR_BUILD: str = "pipeline.feature-ready-for-build.{feature_id}"
        BUILD_QUEUED: str = "pipeline.build-queued.{feature_id}"
        BUILD_STARTED: str = "pipeline.build-started.{feature_id}"
        BUILD_PROGRESS: str = "pipeline.build-progress.{feature_id}"
        BUILD_PAUSED: str = "pipeline.build-paused.{feature_id}"
        BUILD_RESUMED: str = "pipeline.build-resumed.{feature_id}"
        BUILD_COMPLETE: str = "pipeline.build-complete.{feature_id}"
        BUILD_FAILED: str = "pipeline.build-failed.{feature_id}"
        STAGE_COMPLETE: str = "pipeline.stage-complete.{feature_id}"
        STAGE_GATED: str = "pipeline.stage-gated.{feature_id}"
        ALL: str = "pipeline.>"
        ALL_BUILDS: str = "pipeline.build-*.>"

    class Agents(metaclass=_ImmutableNamespaceMeta):
        """Agents domain topics."""

        STATUS: str = "agents.status.{agent_id}"
        STATUS_ALL: str = "agents.status.>"
        APPROVAL_REQUEST: str = "agents.approval.{agent_id}.{task_id}"
        APPROVAL_RESPONSE: str = "agents.approval.{agent_id}.{task_id}.response"
        COMMAND: str = "agents.command.{agent_id}"
        COMMAND_BROADCAST: str = "agents.command.broadcast"
        RESULT: str = "agents.result.{agent_id}"
        TOOLS: str = "agents.{agent_id}.tools.{tool_name}"
        TOOLS_ALL: str = "agents.{agent_id}.tools.>"

    class Fleet(metaclass=_ImmutableNamespaceMeta):
        """Fleet domain topics."""

        REGISTER: str = "fleet.register"
        DEREGISTER: str = "fleet.deregister"
        HEARTBEAT: str = "fleet.heartbeat.{agent_id}"
        HEARTBEAT_ALL: str = "fleet.heartbeat.>"
        ALL: str = "fleet.>"

    class Jarvis(metaclass=_ImmutableNamespaceMeta):
        """Jarvis domain topics."""

        COMMAND: str = "jarvis.command.{adapter}"
        INTENT_CLASSIFIED: str = "jarvis.intent.classified"
        DISPATCH: str = "jarvis.dispatch.{agent}"
        NOTIFICATION: str = "jarvis.notification.{adapter}"

    class System(metaclass=_ImmutableNamespaceMeta):
        """System domain topics."""

        HEALTH: str = "system.health.{component}"

    # -- ALL_TOPICS ----------------------------------------------------------

    ALL_TOPICS: list[str] = [
        v
        for cls in (Pipeline, Agents, Fleet, Jarvis, System)  # noqa: RUF012
        for k, v in vars(cls).items()
        if isinstance(v, str) and not k.startswith("_") and ">" not in v and "*" not in v
    ]

    # -- Resolution helpers --------------------------------------------------

    @staticmethod
    def resolve(template: str, **kwargs: str) -> str:
        """Substitute ``{placeholder}`` tokens in *template* with *kwargs*.

        Args:
            template: A topic template string (e.g. ``"pipeline.build-started.{feature_id}"``).
            **kwargs: Mapping of placeholder names to values.

        Returns:
            The fully-resolved NATS subject string.

        Raises:
            KeyError: If a required placeholder is missing from *kwargs*.
            ValueError: If an unexpected kwarg is provided, or any value
                fails identifier validation.
        """
        expected = set(_PLACEHOLDER_RE.findall(template))
        provided = set(kwargs)

        missing = expected - provided
        if missing:
            msg = f"Missing required placeholder(s): {', '.join(sorted(missing))}"
            raise KeyError(msg)

        unexpected = provided - expected
        if unexpected:
            msg = f"Unexpected placeholder(s): {', '.join(sorted(unexpected))}"
            raise ValueError(msg)

        for name, value in kwargs.items():
            _validate_identifier(value, label=name)

        return template.format(**kwargs)

    @staticmethod
    def for_project(project: str, topic: str) -> str:
        """Scope *topic* to a project namespace for multi-tenancy.

        Args:
            project: The project identifier (e.g. ``"finproxy"``).
            topic: A resolved or template NATS subject string.

        Returns:
            The project-scoped subject: ``"{project}.{topic}"``.

        Raises:
            ValueError: If *project* is empty or contains invalid characters.
        """
        _validate_identifier(project, label="project")
        return f"{project}.{topic}"
