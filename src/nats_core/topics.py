"""Topic Registry — single source of truth for all NATS subject strings.

Provides typed string constants organised into six namespace classes
(Pipeline, Agents, Fleet, Jarvis, System, Memory), template resolution via
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

    Access topic templates as class attributes on the six inner namespace
    classes: ``Pipeline``, ``Agents``, ``Fleet``, ``Jarvis``, ``System``,
    ``Memory``.

    Use :meth:`resolve` to substitute ``{placeholder}`` tokens and
    :meth:`for_project` to scope a subject to a project namespace.
    """

    # -- Namespace classes ---------------------------------------------------

    class Pipeline(metaclass=_ImmutableNamespaceMeta):
        """Pipeline domain topics."""

        # DEPRECATED: use BUILD_QUEUED
        FEATURE_PLANNED: str = "pipeline.feature-planned.{feature_id}"
        FEATURE_READY_FOR_BUILD: str = "pipeline.feature-ready-for-build.{feature_id}"
        PLANNING_QUEUED: str = "pipeline.planning-queued.{correlation_id}"
        # Planning lifecycle (Phase SPL — keyed on correlation_id; no feature
        # identity exists until the spec-ready handoff mints one).
        PLANNING_STARTED: str = "pipeline.planning-started.{correlation_id}"
        PLANNING_COMPLETE: str = "pipeline.planning-complete.{correlation_id}"
        PLANNING_FAILED: str = "pipeline.planning-failed.{correlation_id}"
        SPEC_READY_FOR_BUILD: str = "pipeline.spec-ready-for-build.{correlation_id}"
        BUILD_QUEUED: str = "pipeline.build-queued.{feature_id}"
        BUILD_STARTED: str = "pipeline.build-started.{feature_id}"
        BUILD_PROGRESS: str = "pipeline.build-progress.{feature_id}"
        BUILD_PAUSED: str = "pipeline.build-paused.{feature_id}"
        BUILD_RESUMED: str = "pipeline.build-resumed.{feature_id}"
        BUILD_CANCELLED: str = "pipeline.build-cancelled.{feature_id}"
        BUILD_COMPLETE: str = "pipeline.build-complete.{feature_id}"
        BUILD_FAILED: str = "pipeline.build-failed.{feature_id}"
        STAGE_COMPLETE: str = "pipeline.stage-complete.{feature_id}"
        STAGE_GATED: str = "pipeline.stage-gated.{feature_id}"
        ALL: str = "pipeline.>"
        ALL_BUILDS: str = "pipeline.build-*.>"

    class Agents(metaclass=_ImmutableNamespaceMeta):
        """Agents domain topics.

        **The ``plan-{correlation_id}`` approval-topic convention (NORMATIVE —
        WS1 Session I item 2; FEAT-SPL-003 ASSUM-002).** A build approval rides
        ``agents.approval.{agent_id}.{task_id}`` keyed on a build ``task_id``,
        but a Mode P planning run has no ``task_id`` until the spec-ready
        handoff mints a feature. Mode P therefore fills the ``{task_id}`` slot
        with the literal ``plan-{correlation_id}`` — i.e. it publishes on
        ``agents.approval.{agent_id}.plan-{correlation_id}`` (and the response
        on the same subject plus ``.response``). This is a namespacing of the
        existing subject, NOT a new stream: the fourth subject token stays
        opaque to consumers, which detect a planning checkpoint by the
        request's checkpoint details (never by parsing the run-id shape out of
        the subject). ``PLANNING_APPROVAL_REQUEST`` / ``PLANNING_APPROVAL_RESPONSE``
        pin the convention so jarvis and WS2 consumers can resolve it directly;
        ``approval_decision.gate_id`` (backward-edge contract §7 item 4) cites it.
        """

        STATUS: str = "agents.status.{agent_id}"
        STATUS_ALL: str = "agents.status.>"
        APPROVAL_REQUEST: str = "agents.approval.{agent_id}.{task_id}"
        APPROVAL_RESPONSE: str = "agents.approval.{agent_id}.{task_id}.response"
        # Planning approval convention (NORMATIVE): the {task_id} slot is the
        # literal ``plan-{correlation_id}`` — see the class docstring.
        PLANNING_APPROVAL_REQUEST: str = "agents.approval.{agent_id}.plan-{correlation_id}"
        PLANNING_APPROVAL_RESPONSE: str = (
            "agents.approval.{agent_id}.plan-{correlation_id}.response"
        )
        COMMAND: str = "agents.command.{agent_id}"
        COMMAND_BROADCAST: str = "agents.command.broadcast"
        RESULT: str = "agents.result.{agent_id}"
        TOOLS: str = "agents.{agent_id}.tools.{tool_name}"
        TOOLS_ALL: str = "agents.{agent_id}.tools.>"

    class Deploy(metaclass=_ImmutableNamespaceMeta):
        """Deploy domain topics (WS2 B7 — the last-mile deploy/QA/live-gate stage).

        The DEPLOY and LIVE_GATE forge stages after PULL_REQUEST_REVIEW
        (scope-design §4). Every subject is keyed on ``correlation_id`` — the
        build/feature spine — because a deploy run has no identity of its own
        beyond its forge run id (which rides in the payload, not the subject).
        The QA-verdict and live-gate-result notifications live here too so the
        whole last-mile stage shares one namespace. These are notifications for
        jarvis (the phone loop) and the dashboard; forge's authoritative
        live-gate input stays the frozen seam's stdout envelope.
        """

        DEPLOY_QUEUED: str = "deploy.queued.{correlation_id}"
        DEPLOY_STARTED: str = "deploy.started.{correlation_id}"
        DEPLOY_COMPLETE: str = "deploy.complete.{correlation_id}"
        DEPLOY_FAILED: str = "deploy.failed.{correlation_id}"
        # O-32 revert-on-gate-fail receipt (nats-core 0.7.1) — same family grammar.
        DEPLOY_REVERTED: str = "deploy.reverted.{correlation_id}"
        QA_VERDICT: str = "deploy.qa-verdict.{correlation_id}"
        LIVE_GATE_RESULT: str = "deploy.live-gate-result.{correlation_id}"
        ALL: str = "deploy.>"

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

    class Memory(metaclass=_ImmutableNamespaceMeta):
        """Memory domain topics (post-Graphiti memory write path)."""

        EPISODE: str = "memory.episode.{project_id}.{episode_type}"
        ALL: str = "memory.episode.>"

    # -- ALL_TOPICS ----------------------------------------------------------

    ALL_TOPICS: list[str] = [
        v
        for cls in (Pipeline, Agents, Deploy, Fleet, Jarvis, System, Memory)  # noqa: RUF012
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

        **NORMATIVE (dashboard ask A-6):** this ``{leading-token}.{topic}``
        prefix is THE tenant fan-out convention for client-visible delivery
        events — not an ad-hoc string. Amended 2026-07-08 (Rich): the leading
        token is the **TENANT slug** (account-aligned), NOT a repo name — a
        client tenant may own several repos, so the reduced client-facing event
        carries the ``project``/repo in its payload while the subject prefix
        carries the tenant (first instance: ``finproxy.delivery….{feat}``). The
        producer half (forge's DF-008-reduced client-facing delivery event on
        ``{tenant_prefix}.>``) is dashboard ask A-8, owned by WS2 B8 — the
        repo→tenant mapping is producer-side configuration, never code. Internal
        payloads (tasks_failed, branch, evidence refs) must NEVER appear on a
        tenant prefix (directly readable by the client's own NATS users).

        Args:
            project: The tenant slug (e.g. ``"finproxy"``); account-aligned.
            topic: A resolved or template NATS subject string.

        Returns:
            The tenant-scoped subject: ``"{project}.{topic}"``.

        Raises:
            ValueError: If *project* is empty or contains invalid characters.
        """
        _validate_identifier(project, label="project")
        return f"{project}.{topic}"
