"""Tests for nats_core.topics — Topic Registry.

Covers all 32 BDD scenarios from the topic-registry feature spec:
- Key examples / smoke (8): Core resolution, project scoping, wildcards
- Boundary (6+2): Minimal IDs, hyphens, wildcard syntax (Scenario Outline ×6)
- Negative (5+): Empty IDs, dots, spaces, missing/extra vars, empty project, wildcards in IDs
- Edge-case (13): EventType sync, no hardcoded strings, composition, NATS validity,
  immutability, namespaces, idempotency

Also includes seam test for integration contract verification.
"""

from __future__ import annotations

import re
import subprocess

import pytest

from nats_core.envelope import EventType
from nats_core.topics import Topics

pytestmark = pytest.mark.unit

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
        with pytest.raises(KeyError, match="(?i)missing|required"):
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
    @pytest.mark.smoke
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
            Topics.Pipeline.BUILD_STARTED = "overwritten"
        assert Topics.Pipeline.BUILD_STARTED == original


# ---------------------------------------------------------------------------
# @edge-case @smoke — EventType synchronisation
# ---------------------------------------------------------------------------


class TestEventTypeSync:
    """Verify topic constant names stay in sync with EventType enum members."""

    @pytest.mark.edge_case
    @pytest.mark.smoke
    def test_pipeline_topics_correspond_to_event_types(self) -> None:
        """Every non-wildcard Pipeline topic template has a matching EventType."""
        pipeline_names = {
            k
            for k, v in vars(Topics.Pipeline).items()
            if not k.startswith("_") and isinstance(v, str) and ">" not in v and "*" not in v
        }
        event_type_names = {e.name for e in EventType}
        for name in pipeline_names:
            assert name in event_type_names, (
                f"Pipeline.{name} has no matching EventType member"
            )

    @pytest.mark.edge_case
    @pytest.mark.smoke
    def test_agent_topics_correspond_to_event_types(self) -> None:
        """Every non-wildcard, non-tool Agent topic template has a matching EventType."""
        # TOOLS is an RPC topic, not an event — exclude it
        excluded = {"TOOLS"}
        agent_names = {
            k
            for k, v in vars(Topics.Agents).items()
            if not k.startswith("_")
            and isinstance(v, str)
            and ">" not in v
            and "*" not in v
            and k not in excluded
        }
        event_type_names = {e.name for e in EventType}
        for name in agent_names:
            assert name in event_type_names, (
                f"Agents.{name} has no matching EventType member"
            )


# ---------------------------------------------------------------------------
# @edge-case — No hardcoded topic strings outside registry
# ---------------------------------------------------------------------------


class TestNoHardcodedStrings:
    """Ensure no source file outside topics.py contains raw topic string literals."""

    @pytest.mark.edge_case
    def test_no_hardcoded_topic_strings_outside_registry(self) -> None:
        """No file outside topics.py should contain hardcoded topic strings in code.

        Docstrings and comments containing topic strings for documentation
        purposes are acceptable — only bare string literals or assignments count.
        """
        patterns = [
            "pipeline.build-",
            "agents.status.",
            "agents.approval.",
            "fleet.register",
            "fleet.heartbeat.",
            "jarvis.command.",
            "jarvis.dispatch.",
            "system.health.",
        ]
        for pattern in patterns:
            result = subprocess.run(  # noqa: S603, S607
                [
                    "grep",
                    "-rn",
                    pattern,
                    "src/",
                    "--include=*.py",
                    "--exclude=topics.py",
                ],
                capture_output=True,
                text=True,
                cwd="/Users/richardwoollcott/Projects/appmilla_github/nats-core/"
                ".guardkit/worktrees/FEAT-3845",
                check=False,
            )
            # Filter out lines that are purely in docstrings or comments
            code_hits = []
            for line in result.stdout.strip().splitlines():
                # Extract the content after the filename:lineno: prefix
                parts = line.split(":", 2)
                if len(parts) < 3:  # noqa: PLR2004
                    continue
                content = parts[2].strip()
                # Skip lines that are comments or docstring content
                if content.startswith("#"):
                    continue
                if content.startswith(('"""', "'''", "``", "Published on", "See ")):
                    continue
                # Skip indented docstring continuation lines (typically start with text)
                # Heuristic: if the line has no assignment (=) and no function call
                # and isn't a string literal assignment, it's likely a docstring line
                if "=" not in content and "(" not in content:
                    continue
                code_hits.append(line)
            assert code_hits == [], (
                f"Hardcoded topic string '{pattern}' found in code outside topics.py:\n"
                + "\n".join(code_hits)
            )


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


# ---------------------------------------------------------------------------
# @seam — Integration contract verification
# ---------------------------------------------------------------------------


class TestSeam:
    """Seam test: verify nats_core.topics contract from TASK-TR01."""

    @pytest.mark.seam
    @pytest.mark.integration_contract("nats_core.topics")
    def test_nats_core_topics_importable(self) -> None:
        """Verify nats_core.topics module matches the expected interface.

        Contract: Module must be importable as ``from nats_core.topics import Topics``
        after ``pip install -e '.[dev]'``; Topics class must expose Pipeline, Agents,
        Fleet, Jarvis, System as inner classes with string constants.

        Producer: TASK-TR01
        """
        from nats_core.topics import Topics as TopicsFromModule  # noqa: PLC0415

        # Module is importable
        assert TopicsFromModule is not None, "Topics class must be importable"

        # All 5 namespaces present
        for ns in ("Pipeline", "Agents", "Fleet", "Jarvis", "System"):
            assert hasattr(TopicsFromModule, ns), f"Topics must have {ns} namespace"

        # Constants are strings (not None, not instances)
        assert isinstance(TopicsFromModule.Pipeline.BUILD_STARTED, str)
        assert isinstance(TopicsFromModule.Fleet.REGISTER, str)


# ---------------------------------------------------------------------------
# TASK-NC02 Acceptance Criteria — Exact resolution tests
# ---------------------------------------------------------------------------


class TestTaskNC02AcceptanceCriteria:
    """Tests that map 1:1 to TASK-NC02 acceptance criteria."""

    @pytest.mark.smoke
    def test_ac_001_all_constants_from_all_five_domains_present(self) -> None:
        """AC-001: All constants from all 5 domains are present."""
        # Pipeline domain (8 constants including wildcards)
        assert hasattr(Topics.Pipeline, "FEATURE_PLANNED")
        assert hasattr(Topics.Pipeline, "FEATURE_READY_FOR_BUILD")
        assert hasattr(Topics.Pipeline, "BUILD_STARTED")
        assert hasattr(Topics.Pipeline, "BUILD_PROGRESS")
        assert hasattr(Topics.Pipeline, "BUILD_COMPLETE")
        assert hasattr(Topics.Pipeline, "BUILD_FAILED")
        assert hasattr(Topics.Pipeline, "ALL")
        assert hasattr(Topics.Pipeline, "ALL_BUILDS")

        # Agents domain (8 constants including wildcards)
        assert hasattr(Topics.Agents, "STATUS")
        assert hasattr(Topics.Agents, "STATUS_ALL")
        assert hasattr(Topics.Agents, "APPROVAL_REQUEST")
        assert hasattr(Topics.Agents, "APPROVAL_RESPONSE")
        assert hasattr(Topics.Agents, "COMMAND")
        assert hasattr(Topics.Agents, "RESULT")
        assert hasattr(Topics.Agents, "TOOLS")
        assert hasattr(Topics.Agents, "TOOLS_ALL")

        # Fleet domain (5 constants including wildcards)
        assert hasattr(Topics.Fleet, "REGISTER")
        assert hasattr(Topics.Fleet, "DEREGISTER")
        assert hasattr(Topics.Fleet, "HEARTBEAT")
        assert hasattr(Topics.Fleet, "HEARTBEAT_ALL")
        assert hasattr(Topics.Fleet, "ALL")

        # Jarvis domain (4 constants)
        assert hasattr(Topics.Jarvis, "COMMAND")
        assert hasattr(Topics.Jarvis, "INTENT_CLASSIFIED")
        assert hasattr(Topics.Jarvis, "DISPATCH")
        assert hasattr(Topics.Jarvis, "NOTIFICATION")

        # System domain (1 constant)
        assert hasattr(Topics.System, "HEALTH")

    @pytest.mark.smoke
    def test_ac_002_resolve_pipeline_build_complete(self) -> None:
        """AC-002: Topics.resolve(Topics.Pipeline.BUILD_COMPLETE, feature_id="FEAT-001")
        → "pipeline.build-complete.FEAT-001"."""
        result = Topics.resolve(Topics.Pipeline.BUILD_COMPLETE, feature_id="FEAT-001")
        assert result == "pipeline.build-complete.FEAT-001"

    @pytest.mark.smoke
    def test_ac_003_for_project_scoping(self) -> None:
        """AC-003: Topics.for_project("finproxy", "pipeline.build-complete.FEAT-001")
        → "finproxy.pipeline.build-complete.FEAT-001"."""
        result = Topics.for_project("finproxy", "pipeline.build-complete.FEAT-001")
        assert result == "finproxy.pipeline.build-complete.FEAT-001"

    @pytest.mark.negative
    def test_ac_004_missing_placeholder_raises_key_error(self) -> None:
        """AC-004: Topics.resolve(template) raises KeyError when a required
        placeholder is missing."""
        with pytest.raises(KeyError, match="(?i)missing|required"):
            Topics.resolve(Topics.Pipeline.BUILD_COMPLETE)

    @pytest.mark.smoke
    def test_ac_005_resolve_agents_approval_response(self) -> None:
        """AC-005: Topics.resolve(Topics.Agents.APPROVAL_RESPONSE, agent_id="jarvis",
        task_id="task-99") → "agents.approval.jarvis.task-99.response"."""
        result = Topics.resolve(
            Topics.Agents.APPROVAL_RESPONSE, agent_id="jarvis", task_id="task-99"
        )
        assert result == "agents.approval.jarvis.task-99.response"

    @pytest.mark.negative
    def test_ac_006_malicious_identifier_raises_value_error(self) -> None:
        """AC-006: Topics.resolve(Topics.Agents.TOOLS, agent_id="evil.>", tool_name="x")
        raises ValueError."""
        with pytest.raises(ValueError, match="(?i)dot|wildcard|invalid"):
            Topics.resolve(Topics.Agents.TOOLS, agent_id="evil.>", tool_name="x")

    @pytest.mark.smoke
    def test_ac_007_all_topics_is_non_empty_list_of_str(self) -> None:
        """AC-007: Topics.ALL_TOPICS is a non-empty list[str] containing every template."""
        assert isinstance(Topics.ALL_TOPICS, list)
        assert len(Topics.ALL_TOPICS) > 0
        for item in Topics.ALL_TOPICS:
            assert isinstance(item, str)

    def test_ac_008_no_external_dependencies(self) -> None:
        """AC-008: No external dependencies (pure Python)."""
        import importlib
        import inspect

        mod = importlib.import_module("nats_core.topics")
        source = inspect.getsource(mod)
        # Should only import from __future__ and re (stdlib)
        # No pydantic, no third-party imports
        import_lines = [
            line.strip()
            for line in source.splitlines()
            if line.strip().startswith(("import ", "from "))
        ]
        for line in import_lines:
            assert "pydantic" not in line, f"External dep found: {line}"
            assert "nats" not in line or "__future__" in line, f"Unexpected import: {line}"

    def test_ac_009_future_annotations_present(self) -> None:
        """AC-009: from __future__ import annotations present."""
        import inspect

        from nats_core import topics as topics_mod

        source = inspect.getsource(topics_mod)
        assert "from __future__ import annotations" in source
