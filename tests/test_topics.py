"""Tests for nats_core.topics — Topic Registry.

Covers BDD scenarios from the topic-registry feature spec:
- Key examples / smoke: Core resolution, project scoping, wildcards
- Boundary: Minimal IDs, hyphens, wildcard syntax
- Negative: Empty IDs, dots, spaces, missing/extra vars, empty project, wildcards in IDs
- Edge-case: Immutability, composition, NATS validity, namespaces, idempotency
"""

from __future__ import annotations

import re

import pytest

from nats_core.topics import Topics

# ---------------------------------------------------------------------------
# @key-example @smoke — Core resolution for each domain
# ---------------------------------------------------------------------------


class TestKeyExamplesSmoke:
    """Core happy-path resolution scenarios."""

    @pytest.mark.smoke
    @pytest.mark.key_example
    def test_resolve_pipeline_build_started(self) -> None:
        result = Topics.resolve(Topics.Pipeline.BUILD_STARTED, feature_id="FEAT-AC1A")
        assert result == "pipeline.build-started.FEAT-AC1A"

    @pytest.mark.smoke
    @pytest.mark.key_example
    def test_resolve_agent_status(self) -> None:
        result = Topics.resolve(Topics.Agents.STATUS, agent_id="guardkit-factory")
        assert result == "agents.status.guardkit-factory"

    @pytest.mark.smoke
    @pytest.mark.key_example
    def test_fleet_register_fixed_string(self) -> None:
        assert Topics.Fleet.REGISTER == "fleet.register"

    @pytest.mark.smoke
    @pytest.mark.key_example
    def test_resolve_jarvis_dispatch(self) -> None:
        result = Topics.resolve(Topics.Jarvis.DISPATCH, agent="ideation-agent")
        assert result == "jarvis.dispatch.ideation-agent"

    @pytest.mark.smoke
    @pytest.mark.key_example
    def test_scope_to_project(self) -> None:
        resolved = "pipeline.build-started.FEAT-001"
        result = Topics.for_project("finproxy", resolved)
        assert result == "finproxy.pipeline.build-started.FEAT-001"

    @pytest.mark.key_example
    def test_pipeline_wildcard_all(self) -> None:
        assert Topics.Pipeline.ALL == "pipeline.>"

    @pytest.mark.key_example
    def test_resolve_agent_tools(self) -> None:
        result = Topics.resolve(
            Topics.Agents.TOOLS, agent_id="guardkit-factory", tool_name="lint"
        )
        assert result == "agents.guardkit-factory.tools.lint"

    @pytest.mark.key_example
    def test_resolve_approval_request(self) -> None:
        result = Topics.resolve(
            Topics.Agents.APPROVAL_REQUEST, agent_id="guardkit-factory", task_id="TASK-001"
        )
        assert result == "agents.approval.guardkit-factory.TASK-001"


# ---------------------------------------------------------------------------
# @boundary — Edge-of-range inputs
# ---------------------------------------------------------------------------


class TestBoundary:
    """Boundary condition scenarios."""

    @pytest.mark.boundary
    def test_minimal_length_identifier(self) -> None:
        result = Topics.resolve(Topics.Pipeline.BUILD_STARTED, feature_id="X")
        assert result == "pipeline.build-started.X"

    @pytest.mark.boundary
    def test_hyphens_and_numbers_in_id(self) -> None:
        result = Topics.resolve(Topics.Agents.STATUS, agent_id="my-agent-v2-01")
        assert result == "agents.status.my-agent-v2-01"

    @pytest.mark.boundary
    @pytest.mark.parametrize(
        "wildcard_topic",
        [
            Topics.Pipeline.ALL,
            Topics.Pipeline.ALL_BUILDS,
            Topics.Agents.STATUS_ALL,
            Topics.Agents.TOOLS_ALL,
            Topics.Fleet.HEARTBEAT_ALL,
            Topics.Fleet.ALL,
        ],
        ids=[
            "Pipeline.ALL",
            "Pipeline.ALL_BUILDS",
            "Agents.STATUS_ALL",
            "Agents.TOOLS_ALL",
            "Fleet.HEARTBEAT_ALL",
            "Fleet.ALL",
        ],
    )
    def test_wildcard_topics_end_with_gt(self, wildcard_topic: str) -> None:
        assert wildcard_topic.endswith(">")


# ---------------------------------------------------------------------------
# @negative — Invalid inputs
# ---------------------------------------------------------------------------


class TestNegative:
    """Invalid input and error-path scenarios."""

    @pytest.mark.negative
    @pytest.mark.boundary
    def test_empty_identifier_rejected(self) -> None:
        with pytest.raises(ValueError, match="(?i)empty"):
            Topics.resolve(Topics.Pipeline.BUILD_STARTED, feature_id="")

    @pytest.mark.negative
    @pytest.mark.boundary
    def test_dots_in_identifier_rejected(self) -> None:
        with pytest.raises(ValueError, match="(?i)dot|invalid"):
            Topics.resolve(Topics.Pipeline.BUILD_STARTED, feature_id="FEAT.001")

    @pytest.mark.negative
    @pytest.mark.boundary
    def test_spaces_in_identifier_rejected(self) -> None:
        with pytest.raises(ValueError, match="(?i)space|invalid"):
            Topics.resolve(Topics.Pipeline.BUILD_STARTED, feature_id="FEAT 001")

    @pytest.mark.negative
    @pytest.mark.smoke
    def test_missing_template_variable_raises(self) -> None:
        with pytest.raises(ValueError, match="(?i)missing|required"):
            Topics.resolve(Topics.Pipeline.BUILD_STARTED)

    @pytest.mark.negative
    def test_extra_template_variable_raises(self) -> None:
        with pytest.raises(ValueError, match="(?i)unexpected|extra"):
            Topics.resolve(
                Topics.Pipeline.BUILD_STARTED, feature_id="FEAT-001", unknown_var="X"
            )

    @pytest.mark.negative
    def test_empty_project_name_rejected(self) -> None:
        with pytest.raises(ValueError, match="(?i)empty"):
            Topics.for_project("", "pipeline.build-started.FEAT-001")

    @pytest.mark.negative
    def test_project_name_with_dots_rejected(self) -> None:
        with pytest.raises(ValueError, match="(?i)dot|invalid"):
            Topics.for_project("fin.proxy", "pipeline.build-started.FEAT-001")

    @pytest.mark.negative
    def test_identifier_with_wildcard_star_rejected(self) -> None:
        with pytest.raises(ValueError, match="(?i)wildcard|invalid"):
            Topics.resolve(Topics.Agents.STATUS, agent_id="agent-*")

    @pytest.mark.negative
    def test_identifier_with_wildcard_gt_rejected(self) -> None:
        with pytest.raises(ValueError, match="(?i)wildcard|invalid"):
            Topics.resolve(Topics.Agents.STATUS, agent_id="agent->")

    @pytest.mark.negative
    @pytest.mark.edge_case
    def test_identifier_with_control_chars_rejected(self) -> None:
        with pytest.raises(ValueError, match="(?i)invalid"):
            Topics.resolve(Topics.Agents.STATUS, agent_id="agent\n")

    @pytest.mark.negative
    @pytest.mark.edge_case
    def test_project_with_shell_metacharacters_rejected(self) -> None:
        with pytest.raises(ValueError, match="(?i)invalid"):
            Topics.for_project("fin;rm -rf", "pipeline.build-started.FEAT-001")


# ---------------------------------------------------------------------------
# @edge-case — Composition, validity, immutability, namespaces
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge-case and structural scenarios."""

    @pytest.mark.edge_case
    def test_resolve_then_scope(self) -> None:
        resolved = Topics.resolve(Topics.Pipeline.BUILD_COMPLETE, feature_id="FEAT-001")
        scoped = Topics.for_project("guardkit", resolved)
        assert scoped == "guardkit.pipeline.build-complete.FEAT-001"

    @pytest.mark.edge_case
    def test_scope_wildcard_topic(self) -> None:
        result = Topics.for_project("finproxy", Topics.Pipeline.ALL)
        assert result == "finproxy.pipeline.>"

    @pytest.mark.edge_case
    @pytest.mark.parametrize(
        ("topic_template", "kwargs"),
        [
            (Topics.Pipeline.FEATURE_PLANNED, {"feature_id": "F1"}),
            (Topics.Pipeline.BUILD_STARTED, {"feature_id": "F1"}),
            (Topics.Pipeline.BUILD_COMPLETE, {"feature_id": "F1"}),
            (Topics.Agents.STATUS, {"agent_id": "a1"}),
            (Topics.Agents.APPROVAL_REQUEST, {"agent_id": "a1", "task_id": "t1"}),
            (Topics.Agents.COMMAND, {"agent_id": "a1"}),
            (Topics.Agents.TOOLS, {"agent_id": "a1", "tool_name": "t"}),
            (Topics.Fleet.HEARTBEAT, {"agent_id": "a1"}),
            (Topics.Jarvis.COMMAND, {"adapter": "cli"}),
            (Topics.Jarvis.DISPATCH, {"agent": "a1"}),
            (Topics.System.HEALTH, {"component": "db"}),
        ],
        ids=[
            "Pipeline.FEATURE_PLANNED",
            "Pipeline.BUILD_STARTED",
            "Pipeline.BUILD_COMPLETE",
            "Agents.STATUS",
            "Agents.APPROVAL_REQUEST",
            "Agents.COMMAND",
            "Agents.TOOLS",
            "Fleet.HEARTBEAT",
            "Jarvis.COMMAND",
            "Jarvis.DISPATCH",
            "System.HEALTH",
        ],
    )
    def test_resolved_topics_are_valid_nats_subjects(
        self, topic_template: str, kwargs: dict[str, str]
    ) -> None:
        result = Topics.resolve(topic_template, **kwargs)
        # Only valid chars: alphanumeric, hyphens, underscores, dots, >
        assert re.fullmatch(r"[a-zA-Z0-9._>-]+", result), f"Invalid chars in: {result}"
        assert ".." not in result, f"Consecutive dots in: {result}"
        assert not result.startswith("."), f"Starts with dot: {result}"
        assert not result.endswith("."), f"Ends with dot: {result}"

    @pytest.mark.edge_case
    def test_topics_class_no_instantiation_needed(self) -> None:
        # Should be accessible as class attributes without instantiation
        assert isinstance(Topics.Pipeline.BUILD_STARTED, str)
        assert isinstance(Topics.Agents.STATUS, str)

    @pytest.mark.edge_case
    def test_approval_response_extends_request(self) -> None:
        request = Topics.resolve(
            Topics.Agents.APPROVAL_REQUEST, agent_id="factory", task_id="T1"
        )
        response = Topics.resolve(
            Topics.Agents.APPROVAL_RESPONSE, agent_id="factory", task_id="T1"
        )
        assert response == request + ".response"

    @pytest.mark.edge_case
    def test_all_five_namespaces_present(self) -> None:
        assert hasattr(Topics, "Pipeline")
        assert hasattr(Topics, "Agents")
        assert hasattr(Topics, "Fleet")
        assert hasattr(Topics, "Jarvis")
        assert hasattr(Topics, "System")

    @pytest.mark.edge_case
    def test_resolve_idempotent(self) -> None:
        r1 = Topics.resolve(Topics.Pipeline.BUILD_STARTED, feature_id="FEAT-001")
        r2 = Topics.resolve(Topics.Pipeline.BUILD_STARTED, feature_id="FEAT-001")
        assert r1 == r2

    @pytest.mark.edge_case
    def test_topic_constants_immutable(self) -> None:
        original = Topics.Pipeline.BUILD_STARTED
        with pytest.raises(AttributeError):
            Topics.Pipeline.BUILD_STARTED = "overwritten"  # type: ignore[misc]
        assert Topics.Pipeline.BUILD_STARTED == original


# ---------------------------------------------------------------------------
# ALL_TOPICS — Enumeration
# ---------------------------------------------------------------------------


class TestAllTopics:
    """Tests for Topics.ALL_TOPICS list."""

    def test_all_topics_is_list(self) -> None:
        assert isinstance(Topics.ALL_TOPICS, list)

    def test_all_topics_excludes_wildcards(self) -> None:
        for topic in Topics.ALL_TOPICS:
            assert ">" not in topic, f"Wildcard found in ALL_TOPICS: {topic}"
            assert "*" not in topic, f"Wildcard found in ALL_TOPICS: {topic}"

    def test_all_topics_includes_templates(self) -> None:
        # Non-wildcard templates should be in ALL_TOPICS
        assert Topics.Pipeline.BUILD_STARTED in Topics.ALL_TOPICS
        assert Topics.Fleet.REGISTER in Topics.ALL_TOPICS
        assert Topics.Jarvis.INTENT_CLASSIFIED in Topics.ALL_TOPICS
        assert Topics.System.HEALTH in Topics.ALL_TOPICS

    def test_all_topics_count(self) -> None:
        # Total non-wildcard constants:
        # Pipeline: 6 (excl ALL, ALL_BUILDS)
        # Agents: 6 (excl STATUS_ALL, TOOLS_ALL)
        # Fleet: 3 (excl HEARTBEAT_ALL, ALL)
        # Jarvis: 4 (none are wildcards)
        # System: 1
        # Total: 20
        assert len(Topics.ALL_TOPICS) == 20


# ---------------------------------------------------------------------------
# Re-export from __init__.py
# ---------------------------------------------------------------------------


class TestReExport:
    """Verify Topics is re-exported from the package."""

    def test_topics_importable_from_package(self) -> None:
        from nats_core import Topics as TopicsFromInit

        assert TopicsFromInit is Topics


# ---------------------------------------------------------------------------
# All constants existence check
# ---------------------------------------------------------------------------


class TestAllConstantsExist:
    """Verify all topic constants from the API contract are defined."""

    def test_pipeline_constants(self) -> None:
        assert Topics.Pipeline.FEATURE_PLANNED == "pipeline.feature-planned.{feature_id}"
        assert (
            Topics.Pipeline.FEATURE_READY_FOR_BUILD
            == "pipeline.feature-ready-for-build.{feature_id}"
        )
        assert Topics.Pipeline.BUILD_STARTED == "pipeline.build-started.{feature_id}"
        assert Topics.Pipeline.BUILD_PROGRESS == "pipeline.build-progress.{feature_id}"
        assert Topics.Pipeline.BUILD_COMPLETE == "pipeline.build-complete.{feature_id}"
        assert Topics.Pipeline.BUILD_FAILED == "pipeline.build-failed.{feature_id}"
        assert Topics.Pipeline.ALL == "pipeline.>"
        assert Topics.Pipeline.ALL_BUILDS == "pipeline.build-*.>"

    def test_agents_constants(self) -> None:
        assert Topics.Agents.STATUS == "agents.status.{agent_id}"
        assert Topics.Agents.STATUS_ALL == "agents.status.>"
        assert (
            Topics.Agents.APPROVAL_REQUEST == "agents.approval.{agent_id}.{task_id}"
        )
        assert (
            Topics.Agents.APPROVAL_RESPONSE
            == "agents.approval.{agent_id}.{task_id}.response"
        )
        assert Topics.Agents.COMMAND == "agents.command.{agent_id}"
        assert Topics.Agents.RESULT == "agents.result.{agent_id}"
        assert Topics.Agents.TOOLS == "agents.{agent_id}.tools.{tool_name}"
        assert Topics.Agents.TOOLS_ALL == "agents.{agent_id}.tools.>"

    def test_fleet_constants(self) -> None:
        assert Topics.Fleet.REGISTER == "fleet.register"
        assert Topics.Fleet.DEREGISTER == "fleet.deregister"
        assert Topics.Fleet.HEARTBEAT == "fleet.heartbeat.{agent_id}"
        assert Topics.Fleet.HEARTBEAT_ALL == "fleet.heartbeat.>"
        assert Topics.Fleet.ALL == "fleet.>"

    def test_jarvis_constants(self) -> None:
        assert Topics.Jarvis.COMMAND == "jarvis.command.{adapter}"
        assert Topics.Jarvis.INTENT_CLASSIFIED == "jarvis.intent.classified"
        assert Topics.Jarvis.DISPATCH == "jarvis.dispatch.{agent}"
        assert Topics.Jarvis.NOTIFICATION == "jarvis.notification.{adapter}"

    def test_system_constants(self) -> None:
        assert Topics.System.HEALTH == "system.health.{component}"
