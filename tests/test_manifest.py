"""Tests for AgentManifest, capability models, and ManifestRegistry."""

from __future__ import annotations

import ast
import inspect
from typing import Any

import pytest
from pydantic import ValidationError

from nats_core.manifest import (
    AgentManifest,
    InMemoryManifestRegistry,
    IntentCapability,
    ManifestRegistry,
    ToolCapability,
)

pytestmark = pytest.mark.unit

# ---------------------------------------------------------------------------
# Local helpers (thin wrappers matching conftest factory signatures)
# ---------------------------------------------------------------------------


def _make_intent(**overrides: Any) -> IntentCapability:
    defaults: dict[str, Any] = {
        "pattern": "software.*",
        "description": "Handles software-related intents",
    }
    defaults.update(overrides)
    return IntentCapability(**defaults)


def _make_tool(**overrides: Any) -> ToolCapability:
    defaults: dict[str, Any] = {
        "name": "lint",
        "description": "Run code linting",
        "parameters": {"type": "object"},
        "returns": "Lint report",
    }
    defaults.update(overrides)
    return ToolCapability(**defaults)


def _make_manifest(**overrides: Any) -> AgentManifest:
    defaults: dict[str, Any] = {
        "agent_id": "test-agent",
        "name": "Test Agent",
        "template": "basic",
    }
    defaults.update(overrides)
    return AgentManifest(**defaults)


def _make_registry() -> InMemoryManifestRegistry:
    return InMemoryManifestRegistry()


# ===========================================================================
# AC-001: AgentManifest instantiation with defaults
# ===========================================================================


class TestAgentManifestInstantiation:
    """AC-001: AgentManifest(agent_id="x", name="X Agent", template="basic") instantiates."""

    @pytest.mark.smoke
    def test_minimal_instantiation(self) -> None:
        """AgentManifest can be created with only required fields."""
        m = AgentManifest(agent_id="x", name="X Agent", template="basic")
        assert m.agent_id == "x"
        assert m.name == "X Agent"
        assert m.template == "basic"

    @pytest.mark.smoke
    def test_defaults_applied(self) -> None:
        """Default values are applied for optional fields."""
        m = AgentManifest(agent_id="x", name="X Agent", template="basic")
        assert m.version == "0.1.0"
        assert m.intents == []
        assert m.tools == []
        assert m.max_concurrent == 1
        assert m.status == "ready"
        assert m.trust_tier == "specialist"
        assert m.required_permissions == []
        assert m.container_id is None
        assert m.metadata == {}

    @pytest.mark.smoke
    def test_factory_function_defaults(self) -> None:
        """Factory function produces a valid manifest with sensible defaults."""
        m = _make_manifest()
        assert m.agent_id == "test-agent"
        assert m.name == "Test Agent"
        assert m.template == "basic"

    @pytest.mark.key_example
    def test_factory_overrides(self) -> None:
        """Factory function accepts overrides for all fields."""
        m = _make_manifest(agent_id="my-agent", name="My Agent", version="1.0.0")
        assert m.agent_id == "my-agent"
        assert m.name == "My Agent"
        assert m.version == "1.0.0"

    @pytest.mark.negative
    def test_invalid_agent_id_uppercase(self) -> None:
        """agent_id must be kebab-case — uppercase is rejected."""
        with pytest.raises(ValidationError):
            AgentManifest(agent_id="INVALID", name="Bad", template="basic")

    @pytest.mark.negative
    def test_invalid_agent_id_starts_with_number(self) -> None:
        """agent_id must start with a lowercase letter."""
        with pytest.raises(ValidationError):
            AgentManifest(agent_id="123-agent", name="Bad", template="basic")

    @pytest.mark.boundary
    def test_single_char_agent_id(self) -> None:
        """Single lowercase letter is a valid agent_id."""
        m = AgentManifest(agent_id="x", name="X", template="t")
        assert m.agent_id == "x"


# ===========================================================================
# AC-002: IntentCapability.confidence validated ge=0.0, le=1.0
# ===========================================================================


class TestIntentCapabilityConfidence:
    """AC-002: IntentCapability.confidence is validated ge=0.0, le=1.0."""

    @pytest.mark.smoke
    def test_default_confidence(self) -> None:
        """Default confidence is 1.0."""
        ic = _make_intent()
        assert ic.confidence == 1.0

    @pytest.mark.boundary
    def test_confidence_at_zero(self) -> None:
        """Confidence of 0.0 is accepted (lower bound)."""
        ic = _make_intent(confidence=0.0)
        assert ic.confidence == 0.0

    @pytest.mark.boundary
    def test_confidence_at_one(self) -> None:
        """Confidence of 1.0 is accepted (upper bound)."""
        ic = _make_intent(confidence=1.0)
        assert ic.confidence == 1.0

    @pytest.mark.boundary
    def test_confidence_midpoint(self) -> None:
        """Confidence of 0.5 is accepted."""
        ic = _make_intent(confidence=0.5)
        assert ic.confidence == 0.5

    @pytest.mark.negative
    def test_confidence_below_zero_rejected(self) -> None:
        """Confidence below 0.0 is rejected."""
        with pytest.raises(ValidationError):
            _make_intent(confidence=-0.1)

    @pytest.mark.negative
    def test_confidence_above_one_rejected(self) -> None:
        """Confidence above 1.0 is rejected."""
        with pytest.raises(ValidationError):
            _make_intent(confidence=1.1)

    @pytest.mark.negative
    def test_confidence_far_above_one_rejected(self) -> None:
        """Confidence of 5.0 is rejected."""
        with pytest.raises(ValidationError):
            _make_intent(confidence=5.0)


# ===========================================================================
# AC-003: ManifestRegistry is abstract
# ===========================================================================


class TestManifestRegistryAbstract:
    """AC-003: ManifestRegistry is abstract — instantiating it directly raises TypeError."""

    @pytest.mark.smoke
    def test_cannot_instantiate_directly(self) -> None:
        """Instantiating ManifestRegistry directly raises TypeError."""
        with pytest.raises(TypeError):
            ManifestRegistry()  # type: ignore[abstract]

    @pytest.mark.key_example
    def test_has_abstract_methods(self) -> None:
        """ManifestRegistry defines the expected abstract methods."""
        abstract_methods = getattr(ManifestRegistry, "__abstractmethods__", set())
        assert "register" in abstract_methods
        assert "deregister" in abstract_methods
        assert "get" in abstract_methods
        assert "find_by_intent" in abstract_methods
        assert "find_by_tool" in abstract_methods

    @pytest.mark.key_example
    def test_in_memory_is_subclass(self) -> None:
        """InMemoryManifestRegistry is a subclass of ManifestRegistry."""
        assert issubclass(InMemoryManifestRegistry, ManifestRegistry)


# ===========================================================================
# AC-004: InMemoryManifestRegistry.register() stores manifest by agent_id
# ===========================================================================


class TestRegistryRegister:
    """AC-004: register() stores manifest keyed by agent_id."""

    @pytest.mark.smoke
    def test_register_and_get(self) -> None:
        """Registered manifest is retrievable via get()."""
        reg = _make_registry()
        m = _make_manifest(agent_id="build-agent")
        reg.register(m)
        result = reg.get("build-agent")
        assert result is not None
        assert result.agent_id == "build-agent"

    @pytest.mark.key_example
    def test_register_multiple(self) -> None:
        """Multiple manifests can be registered and retrieved independently."""
        reg = _make_registry()
        m1 = _make_manifest(agent_id="agent-a", name="Agent A")
        m2 = _make_manifest(agent_id="agent-b", name="Agent B")
        reg.register(m1)
        reg.register(m2)
        assert reg.get("agent-a") is not None
        assert reg.get("agent-b") is not None
        assert reg.get("agent-a") is not reg.get("agent-b")

    @pytest.mark.edge_case
    def test_register_overwrites_existing(self) -> None:
        """Re-registering with same agent_id overwrites the previous manifest."""
        reg = _make_registry()
        m1 = _make_manifest(agent_id="agent-a", name="Version 1")
        m2 = _make_manifest(agent_id="agent-a", name="Version 2")
        reg.register(m1)
        reg.register(m2)
        result = reg.get("agent-a")
        assert result is not None
        assert result.name == "Version 2"

    @pytest.mark.boundary
    def test_get_unknown_returns_none(self) -> None:
        """get() returns None for an unregistered agent_id."""
        reg = _make_registry()
        assert reg.get("nonexistent") is None


# ===========================================================================
# AC-005: InMemoryManifestRegistry.deregister("unknown") does not raise
# ===========================================================================


class TestRegistryDeregister:
    """AC-005: deregister("unknown") does not raise."""

    @pytest.mark.smoke
    def test_deregister_unknown_no_raise(self) -> None:
        """Deregistering an unknown agent_id is a silent no-op."""
        reg = _make_registry()
        reg.deregister("unknown")  # Should not raise

    @pytest.mark.key_example
    def test_deregister_existing(self) -> None:
        """Deregistering a known agent_id removes it from the registry."""
        reg = _make_registry()
        m = _make_manifest(agent_id="temp-agent")
        reg.register(m)
        assert reg.get("temp-agent") is not None
        reg.deregister("temp-agent")
        assert reg.get("temp-agent") is None

    @pytest.mark.edge_case
    def test_deregister_twice_no_raise(self) -> None:
        """Deregistering the same agent_id twice does not raise."""
        reg = _make_registry()
        m = _make_manifest(agent_id="temp-agent")
        reg.register(m)
        reg.deregister("temp-agent")
        reg.deregister("temp-agent")  # Should not raise


# ===========================================================================
# AC-006: find_by_intent("software.build") returns agents with matching pattern
# ===========================================================================


class TestRegistryFindByIntent:
    """AC-006: find_by_intent() returns agents with matching intent pattern."""

    @pytest.mark.smoke
    def test_find_by_intent_exact_match(self) -> None:
        """Exact intent pattern match returns the agent."""
        reg = _make_registry()
        m = _make_manifest(
            agent_id="builder",
            intents=[_make_intent(pattern="software.build")],
        )
        reg.register(m)
        results = reg.find_by_intent("software.build")
        assert len(results) == 1
        assert results[0].agent_id == "builder"

    @pytest.mark.key_example
    def test_find_by_intent_glob_match(self) -> None:
        """Glob pattern software.* matches software.build."""
        reg = _make_registry()
        m = _make_manifest(
            agent_id="builder",
            intents=[_make_intent(pattern="software.*")],
        )
        reg.register(m)
        results = reg.find_by_intent("software.build")
        assert len(results) == 1
        assert results[0].agent_id == "builder"

    @pytest.mark.key_example
    def test_find_by_intent_no_match(self) -> None:
        """Non-matching intent returns empty list."""
        reg = _make_registry()
        m = _make_manifest(
            agent_id="builder",
            intents=[_make_intent(pattern="devops.*")],
        )
        reg.register(m)
        results = reg.find_by_intent("software.build")
        assert results == []

    @pytest.mark.boundary
    def test_find_by_intent_multiple_agents(self) -> None:
        """Multiple agents matching the same intent are all returned."""
        reg = _make_registry()
        m1 = _make_manifest(
            agent_id="builder-a",
            intents=[_make_intent(pattern="software.*")],
        )
        m2 = _make_manifest(
            agent_id="builder-b",
            intents=[_make_intent(pattern="software.build")],
        )
        m3 = _make_manifest(
            agent_id="unrelated",
            intents=[_make_intent(pattern="devops.*")],
        )
        reg.register(m1)
        reg.register(m2)
        reg.register(m3)
        results = reg.find_by_intent("software.build")
        ids = {r.agent_id for r in results}
        assert ids == {"builder-a", "builder-b"}

    @pytest.mark.boundary
    def test_find_by_intent_empty_registry(self) -> None:
        """Empty registry returns empty list."""
        reg = _make_registry()
        assert reg.find_by_intent("software.build") == []

    @pytest.mark.edge_case
    def test_find_by_intent_agent_with_multiple_intents(self) -> None:
        """Agent with multiple intents appears only once if multiple match."""
        reg = _make_registry()
        m = _make_manifest(
            agent_id="multi-intent",
            intents=[
                _make_intent(pattern="software.*"),
                _make_intent(pattern="software.build"),
            ],
        )
        reg.register(m)
        results = reg.find_by_intent("software.build")
        assert len(results) == 1
        assert results[0].agent_id == "multi-intent"


# ===========================================================================
# AC-007: find_by_tool("lint") returns agents with that tool
# ===========================================================================


class TestRegistryFindByTool:
    """AC-007: find_by_tool() returns agents with the named tool."""

    @pytest.mark.smoke
    def test_find_by_tool_match(self) -> None:
        """Agent with a 'lint' tool is returned by find_by_tool('lint')."""
        reg = _make_registry()
        m = _make_manifest(
            agent_id="linter",
            tools=[_make_tool(name="lint")],
        )
        reg.register(m)
        results = reg.find_by_tool("lint")
        assert len(results) == 1
        assert results[0].agent_id == "linter"

    @pytest.mark.key_example
    def test_find_by_tool_no_match(self) -> None:
        """Agent without the named tool is not returned."""
        reg = _make_registry()
        m = _make_manifest(
            agent_id="builder",
            tools=[_make_tool(name="compile")],
        )
        reg.register(m)
        results = reg.find_by_tool("lint")
        assert results == []

    @pytest.mark.boundary
    def test_find_by_tool_multiple_agents(self) -> None:
        """Multiple agents with the same tool are all returned."""
        reg = _make_registry()
        m1 = _make_manifest(
            agent_id="linter-a",
            tools=[_make_tool(name="lint")],
        )
        m2 = _make_manifest(
            agent_id="linter-b",
            tools=[_make_tool(name="lint")],
        )
        m3 = _make_manifest(
            agent_id="other",
            tools=[_make_tool(name="test")],
        )
        reg.register(m1)
        reg.register(m2)
        reg.register(m3)
        results = reg.find_by_tool("lint")
        ids = {r.agent_id for r in results}
        assert ids == {"linter-a", "linter-b"}

    @pytest.mark.boundary
    def test_find_by_tool_empty_registry(self) -> None:
        """Empty registry returns empty list."""
        reg = _make_registry()
        assert reg.find_by_tool("lint") == []

    @pytest.mark.edge_case
    def test_find_by_tool_agent_with_multiple_tools(self) -> None:
        """Agent with multiple tools appears once if it has the named tool."""
        reg = _make_registry()
        m = _make_manifest(
            agent_id="multi-tool",
            tools=[
                _make_tool(name="lint"),
                _make_tool(name="test"),
            ],
        )
        reg.register(m)
        results = reg.find_by_tool("lint")
        assert len(results) == 1
        assert results[0].agent_id == "multi-tool"


# ===========================================================================
# AC-008: All models use ConfigDict(extra="ignore")
# ===========================================================================


class TestConfigDictExtraIgnore:
    """AC-008: All models use ConfigDict(extra='ignore')."""

    @pytest.mark.smoke
    def test_agent_manifest_ignores_extra(self) -> None:
        """AgentManifest ignores extra fields."""
        m = AgentManifest(
            agent_id="x",
            name="X",
            template="basic",
            unknown_field="ignored",  # type: ignore[call-arg]
        )
        assert not hasattr(m, "unknown_field")

    @pytest.mark.smoke
    def test_intent_capability_ignores_extra(self) -> None:
        """IntentCapability ignores extra fields."""
        ic = IntentCapability(
            pattern="test.*",
            description="Test",
            unknown_field="ignored",  # type: ignore[call-arg]
        )
        assert not hasattr(ic, "unknown_field")

    @pytest.mark.smoke
    def test_tool_capability_ignores_extra(self) -> None:
        """ToolCapability ignores extra fields."""
        tc = ToolCapability(
            name="tool",
            description="Test",
            parameters={},
            returns="result",
            unknown_field="ignored",  # type: ignore[call-arg]
        )
        assert not hasattr(tc, "unknown_field")

    @pytest.mark.integration_contract
    def test_all_models_have_extra_ignore_config(self) -> None:
        """All three models have model_config with extra='ignore'."""
        for cls in (IntentCapability, ToolCapability, AgentManifest):
            config = cls.model_config
            assert config.get("extra") == "ignore", (
                f"{cls.__name__} does not have extra='ignore'"
            )


# ===========================================================================
# AC-009: All models use from __future__ import annotations
# ===========================================================================


class TestFutureAnnotations:
    """AC-009: All models use from __future__ import annotations."""

    @pytest.mark.smoke
    def test_manifest_module_has_future_annotations(self) -> None:
        """manifest.py has 'from __future__ import annotations'."""
        source = inspect.getsource(AgentManifest)  # noqa: F841
        # We need to check the module, not the class source
        import nats_core.manifest as manifest_module

        source_file = inspect.getfile(manifest_module)
        with open(source_file) as f:
            tree = ast.parse(f.read())
        has_future = any(
            isinstance(node, ast.ImportFrom)
            and node.module == "__future__"
            and any(alias.name == "annotations" for alias in node.names)
            for node in ast.walk(tree)
        )
        assert has_future, "manifest.py does not have 'from __future__ import annotations'"


# ===========================================================================
# AC-010: manifest.py does NOT import from nats_core.events
# ===========================================================================


class TestNoCircularImport:
    """AC-010: manifest.py does NOT import from nats_core.events."""

    @pytest.mark.smoke
    def test_no_events_import(self) -> None:
        """manifest.py does not import from nats_core.events."""
        import nats_core.manifest as manifest_module

        source_file = inspect.getfile(manifest_module)
        with open(source_file) as f:
            tree = ast.parse(f.read())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module is not None:
                assert not node.module.startswith("nats_core.events"), (
                    f"manifest.py imports from {node.module} — circular dependency!"
                )
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith("nats_core.events"), (
                        f"manifest.py imports {alias.name} — circular dependency!"
                    )
