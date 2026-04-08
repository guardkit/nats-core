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
# AC-FR003-001: ManifestRegistry is abstract — cannot be instantiated
# ===========================================================================


class TestManifestRegistryAbstract:
    """ManifestRegistry is abstract — instantiating it directly raises TypeError."""

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
        assert "list_all" in abstract_methods
        assert "find_by_intent" in abstract_methods
        assert "find_by_tool" in abstract_methods

    @pytest.mark.key_example
    def test_in_memory_is_subclass(self) -> None:
        """InMemoryManifestRegistry is a subclass of ManifestRegistry."""
        assert issubclass(InMemoryManifestRegistry, ManifestRegistry)


# ===========================================================================
# AC-FR003-002: register() upserts — re-registration replaces previous entry
# ===========================================================================


class TestRegistryRegister:
    """register() stores manifest keyed by agent_id; re-registration replaces."""

    @pytest.mark.smoke
    async def test_register_and_get(self) -> None:
        """Registered manifest is retrievable via get()."""
        reg = _make_registry()
        m = _make_manifest(
            agent_id="build-agent",
            intents=[_make_intent(pattern="build.run")],
        )
        await reg.register(m)
        result = await reg.get("build-agent")
        assert result is not None
        assert result.agent_id == "build-agent"

    @pytest.mark.key_example
    async def test_register_multiple(self) -> None:
        """Multiple manifests can be registered and retrieved independently."""
        reg = _make_registry()
        m1 = _make_manifest(
            agent_id="agent-a",
            name="Agent A",
            intents=[_make_intent(pattern="a.intent")],
        )
        m2 = _make_manifest(
            agent_id="agent-b",
            name="Agent B",
            intents=[_make_intent(pattern="b.intent")],
        )
        await reg.register(m1)
        await reg.register(m2)
        assert await reg.get("agent-a") is not None
        assert await reg.get("agent-b") is not None

    @pytest.mark.edge_case
    async def test_register_overwrites_existing(self) -> None:
        """Re-registering with same agent_id overwrites the previous manifest (upsert)."""
        reg = _make_registry()
        m1 = _make_manifest(
            agent_id="agent-a",
            name="Version 1",
            intents=[_make_intent(pattern="a.intent")],
        )
        m2 = _make_manifest(
            agent_id="agent-a",
            name="Version 2",
            intents=[_make_intent(pattern="a.intent")],
        )
        await reg.register(m1)
        await reg.register(m2)
        result = await reg.get("agent-a")
        assert result is not None
        assert result.name == "Version 2"

    @pytest.mark.boundary
    async def test_get_unknown_returns_none(self) -> None:
        """get() returns None for an unregistered agent_id."""
        reg = _make_registry()
        assert await reg.get("nonexistent") is None


# ===========================================================================
# AC-FR003-003: register() raises ValueError if intents is empty
# ===========================================================================


class TestRegistryRegisterValidation:
    """register() raises ValueError if manifest.intents is empty."""

    @pytest.mark.negative
    async def test_register_empty_intents_raises(self) -> None:
        """Registering a manifest with no intents raises ValueError."""
        reg = _make_registry()
        m = _make_manifest(agent_id="no-intents", intents=[])
        with pytest.raises(ValueError, match="at least one intent"):
            await reg.register(m)

    @pytest.mark.smoke
    async def test_register_with_intents_succeeds(self) -> None:
        """Registering a manifest with intents succeeds."""
        reg = _make_registry()
        m = _make_manifest(
            agent_id="has-intents",
            intents=[_make_intent(pattern="test.intent")],
        )
        await reg.register(m)
        result = await reg.get("has-intents")
        assert result is not None


# ===========================================================================
# AC-FR003-004: deregister() is idempotent — no error if unknown
# ===========================================================================


class TestRegistryDeregister:
    """deregister() is idempotent — no error if agent_id unknown."""

    @pytest.mark.smoke
    async def test_deregister_unknown_no_raise(self) -> None:
        """Deregistering an unknown agent_id is a silent no-op."""
        reg = _make_registry()
        await reg.deregister("unknown")  # Should not raise

    @pytest.mark.key_example
    async def test_deregister_existing(self) -> None:
        """Deregistering a known agent_id removes it from the registry."""
        reg = _make_registry()
        m = _make_manifest(
            agent_id="temp-agent",
            intents=[_make_intent(pattern="temp.intent")],
        )
        await reg.register(m)
        assert await reg.get("temp-agent") is not None
        await reg.deregister("temp-agent")
        assert await reg.get("temp-agent") is None

    @pytest.mark.edge_case
    async def test_deregister_twice_no_raise(self) -> None:
        """Deregistering the same agent_id twice does not raise."""
        reg = _make_registry()
        m = _make_manifest(
            agent_id="temp-agent",
            intents=[_make_intent(pattern="temp.intent")],
        )
        await reg.register(m)
        await reg.deregister("temp-agent")
        await reg.deregister("temp-agent")  # Should not raise


# ===========================================================================
# AC-FR003-005: get() returns None for unknown agent_id
# ===========================================================================
# (Covered in TestRegistryRegister.test_get_unknown_returns_none)


# ===========================================================================
# AC-FR003-006: find_by_intent() matches on IntentCapability.pattern (exact)
# ===========================================================================


class TestRegistryFindByIntent:
    """find_by_intent() returns agents with matching intent pattern (exact match)."""

    @pytest.mark.smoke
    async def test_find_by_intent_exact_match(self) -> None:
        """Exact intent pattern match returns the agent."""
        reg = _make_registry()
        m = _make_manifest(
            agent_id="builder",
            intents=[_make_intent(pattern="software.build")],
        )
        await reg.register(m)
        results = await reg.find_by_intent("software.build")
        assert len(results) == 1
        assert results[0].agent_id == "builder"

    @pytest.mark.key_example
    async def test_find_by_intent_no_match(self) -> None:
        """Non-matching intent returns empty list."""
        reg = _make_registry()
        m = _make_manifest(
            agent_id="builder",
            intents=[_make_intent(pattern="devops.deploy")],
        )
        await reg.register(m)
        results = await reg.find_by_intent("software.build")
        assert results == []

    @pytest.mark.key_example
    async def test_find_by_intent_exact_not_glob(self) -> None:
        """Pattern 'software.*' does NOT glob-match 'software.build' — exact match only."""
        reg = _make_registry()
        m = _make_manifest(
            agent_id="glob-agent",
            intents=[_make_intent(pattern="software.*")],
        )
        await reg.register(m)
        # The pattern "software.*" should NOT match "software.build" with exact matching
        results = await reg.find_by_intent("software.build")
        assert results == []
        # But it SHOULD match "software.*" exactly
        results = await reg.find_by_intent("software.*")
        assert len(results) == 1

    @pytest.mark.boundary
    async def test_find_by_intent_multiple_agents(self) -> None:
        """Multiple agents with the same exact pattern are all returned."""
        reg = _make_registry()
        m1 = _make_manifest(
            agent_id="builder-a",
            intents=[_make_intent(pattern="software.build")],
        )
        m2 = _make_manifest(
            agent_id="builder-b",
            intents=[_make_intent(pattern="software.build")],
        )
        m3 = _make_manifest(
            agent_id="unrelated",
            intents=[_make_intent(pattern="devops.deploy")],
        )
        await reg.register(m1)
        await reg.register(m2)
        await reg.register(m3)
        results = await reg.find_by_intent("software.build")
        ids = {r.agent_id for r in results}
        assert ids == {"builder-a", "builder-b"}

    @pytest.mark.boundary
    async def test_find_by_intent_empty_registry(self) -> None:
        """Empty registry returns empty list."""
        reg = _make_registry()
        assert await reg.find_by_intent("software.build") == []

    @pytest.mark.edge_case
    async def test_find_by_intent_agent_with_multiple_intents(self) -> None:
        """Agent with multiple intents appears only once if one matches."""
        reg = _make_registry()
        m = _make_manifest(
            agent_id="multi-intent",
            intents=[
                _make_intent(pattern="software.build"),
                _make_intent(pattern="software.test"),
            ],
        )
        await reg.register(m)
        results = await reg.find_by_intent("software.build")
        assert len(results) == 1
        assert results[0].agent_id == "multi-intent"


# ===========================================================================
# AC-FR003-007: find_by_tool() matches on ToolCapability.name (exact match)
# ===========================================================================


class TestRegistryFindByTool:
    """find_by_tool() returns agents with the named tool (exact match)."""

    @pytest.mark.smoke
    async def test_find_by_tool_match(self) -> None:
        """Agent with a 'lint' tool is returned by find_by_tool('lint')."""
        reg = _make_registry()
        m = _make_manifest(
            agent_id="linter",
            intents=[_make_intent(pattern="lint.run")],
            tools=[_make_tool(name="lint")],
        )
        await reg.register(m)
        results = await reg.find_by_tool("lint")
        assert len(results) == 1
        assert results[0].agent_id == "linter"

    @pytest.mark.key_example
    async def test_find_by_tool_no_match(self) -> None:
        """Agent without the named tool is not returned."""
        reg = _make_registry()
        m = _make_manifest(
            agent_id="builder",
            intents=[_make_intent(pattern="build.run")],
            tools=[_make_tool(name="compile")],
        )
        await reg.register(m)
        results = await reg.find_by_tool("lint")
        assert results == []

    @pytest.mark.boundary
    async def test_find_by_tool_multiple_agents(self) -> None:
        """Multiple agents with the same tool are all returned."""
        reg = _make_registry()
        m1 = _make_manifest(
            agent_id="linter-a",
            intents=[_make_intent(pattern="lint.a")],
            tools=[_make_tool(name="lint")],
        )
        m2 = _make_manifest(
            agent_id="linter-b",
            intents=[_make_intent(pattern="lint.b")],
            tools=[_make_tool(name="lint")],
        )
        m3 = _make_manifest(
            agent_id="other",
            intents=[_make_intent(pattern="other.run")],
            tools=[_make_tool(name="test")],
        )
        await reg.register(m1)
        await reg.register(m2)
        await reg.register(m3)
        results = await reg.find_by_tool("lint")
        ids = {r.agent_id for r in results}
        assert ids == {"linter-a", "linter-b"}

    @pytest.mark.boundary
    async def test_find_by_tool_empty_registry(self) -> None:
        """Empty registry returns empty list."""
        reg = _make_registry()
        assert await reg.find_by_tool("lint") == []

    @pytest.mark.edge_case
    async def test_find_by_tool_agent_with_multiple_tools(self) -> None:
        """Agent with multiple tools appears once if it has the named tool."""
        reg = _make_registry()
        m = _make_manifest(
            agent_id="multi-tool",
            intents=[_make_intent(pattern="multi.run")],
            tools=[
                _make_tool(name="lint"),
                _make_tool(name="test"),
            ],
        )
        await reg.register(m)
        results = await reg.find_by_tool("lint")
        assert len(results) == 1
        assert results[0].agent_id == "multi-tool"


# ===========================================================================
# AC-FR003-008: All methods are async — awaitable even without I/O
# ===========================================================================


class TestRegistryMethodsAreAsync:
    """All ManifestRegistry methods are async — must be awaitable."""

    @pytest.mark.smoke
    async def test_register_is_awaitable(self) -> None:
        """register() returns a coroutine that can be awaited."""
        reg = _make_registry()
        m = _make_manifest(
            agent_id="async-agent",
            intents=[_make_intent(pattern="async.test")],
        )
        coro = reg.register(m)
        # Must be a coroutine (awaitable)
        assert inspect.iscoroutine(coro)
        await coro

    @pytest.mark.smoke
    async def test_deregister_is_awaitable(self) -> None:
        """deregister() returns a coroutine that can be awaited."""
        reg = _make_registry()
        coro = reg.deregister("any-id")
        assert inspect.iscoroutine(coro)
        await coro

    @pytest.mark.smoke
    async def test_get_is_awaitable(self) -> None:
        """get() returns a coroutine that can be awaited."""
        reg = _make_registry()
        coro = reg.get("any-id")
        assert inspect.iscoroutine(coro)
        await coro

    @pytest.mark.smoke
    async def test_list_all_is_awaitable(self) -> None:
        """list_all() returns a coroutine that can be awaited."""
        reg = _make_registry()
        coro = reg.list_all()
        assert inspect.iscoroutine(coro)
        await coro

    @pytest.mark.smoke
    async def test_find_by_intent_is_awaitable(self) -> None:
        """find_by_intent() returns a coroutine that can be awaited."""
        reg = _make_registry()
        coro = reg.find_by_intent("test")
        assert inspect.iscoroutine(coro)
        await coro

    @pytest.mark.smoke
    async def test_find_by_tool_is_awaitable(self) -> None:
        """find_by_tool() returns a coroutine that can be awaited."""
        reg = _make_registry()
        coro = reg.find_by_tool("test")
        assert inspect.iscoroutine(coro)
        await coro


# ===========================================================================
# list_all() tests
# ===========================================================================


class TestRegistryListAll:
    """list_all() returns all registered manifests."""

    @pytest.mark.smoke
    async def test_list_all_empty(self) -> None:
        """Empty registry returns empty list."""
        reg = _make_registry()
        assert await reg.list_all() == []

    @pytest.mark.key_example
    async def test_list_all_returns_all(self) -> None:
        """list_all() returns all registered manifests."""
        reg = _make_registry()
        m1 = _make_manifest(
            agent_id="agent-a",
            intents=[_make_intent(pattern="a.intent")],
        )
        m2 = _make_manifest(
            agent_id="agent-b",
            intents=[_make_intent(pattern="b.intent")],
        )
        await reg.register(m1)
        await reg.register(m2)
        results = await reg.list_all()
        ids = {r.agent_id for r in results}
        assert ids == {"agent-a", "agent-b"}

    @pytest.mark.edge_case
    async def test_list_all_after_deregister(self) -> None:
        """list_all() reflects deregistration."""
        reg = _make_registry()
        m = _make_manifest(
            agent_id="temp",
            intents=[_make_intent(pattern="temp.intent")],
        )
        await reg.register(m)
        await reg.deregister("temp")
        assert await reg.list_all() == []


# ===========================================================================
# AC-FR002-005: metadata validator rejects payloads > 64KB
# ===========================================================================


class TestMetadataValidator:
    """AC-FR002-005: metadata validator rejects payloads > 64KB with descriptive error."""

    @pytest.mark.smoke
    def test_small_metadata_accepted(self) -> None:
        """Small metadata dict is accepted."""
        m = _make_manifest(metadata={"key": "value"})
        assert m.metadata == {"key": "value"}

    @pytest.mark.smoke
    def test_empty_metadata_accepted(self) -> None:
        """Empty metadata dict is accepted."""
        m = _make_manifest(metadata={})
        assert m.metadata == {}

    @pytest.mark.boundary
    def test_metadata_just_under_64kb_accepted(self) -> None:
        """Metadata payload just under 64KB is accepted."""
        import json

        # Build a dict that serialises to just under 64KB
        # We need the JSON-encoded bytes to be <= 65536
        base = {"k": "x" * 60000}
        # Verify it's under 64KB
        assert len(json.dumps(base).encode()) <= 65536
        m = _make_manifest(metadata=base)
        assert m.metadata == base

    @pytest.mark.negative
    def test_metadata_over_64kb_rejected(self) -> None:
        """Metadata payload over 64KB is rejected with ValidationError."""
        import json

        # Build a dict that serialises to more than 64KB
        big = {"data": "x" * 70000}
        assert len(json.dumps(big).encode()) > 65536
        with pytest.raises(ValidationError, match="64KB"):
            _make_manifest(metadata=big)

    @pytest.mark.negative
    def test_metadata_exactly_at_boundary_accepted(self) -> None:
        """Metadata payload exactly at 64KB boundary is accepted."""
        import json

        # Build payload that is exactly 65536 bytes when JSON-encoded
        # {"k": "xxx..."} -> we need to find the right padding
        prefix = '{"k": "'
        suffix = '"}'
        overhead = len(prefix.encode()) + len(suffix.encode())
        padding = 65536 - overhead
        payload = {"k": "x" * padding}
        assert len(json.dumps(payload).encode()) == 65536
        m = _make_manifest(metadata=payload)
        assert m.metadata == payload

    @pytest.mark.negative
    def test_metadata_one_byte_over_rejected(self) -> None:
        """Metadata payload one byte over 64KB is rejected."""
        import json

        prefix = '{"k": "'
        suffix = '"}'
        overhead = len(prefix.encode()) + len(suffix.encode())
        padding = 65536 - overhead + 1
        payload = {"k": "x" * padding}
        assert len(json.dumps(payload).encode()) == 65537
        with pytest.raises(ValidationError, match="64KB"):
            _make_manifest(metadata=payload)

    @pytest.mark.key_example
    def test_metadata_error_message_is_descriptive(self) -> None:
        """Error message mentions the 64KB size limit."""
        import json

        big = {"data": "x" * 70000}
        assert len(json.dumps(big).encode()) > 65536
        with pytest.raises(ValidationError, match="64KB"):
            _make_manifest(metadata=big)


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


# ===========================================================================
# Seam Test: AgentManifest contract from TASK-FR-002
# ===========================================================================


@pytest.mark.seam
@pytest.mark.integration_contract
async def test_agent_manifest_storable_in_registry() -> None:
    """Verify AgentManifest produced by TASK-FR-002 is accepted by ManifestRegistry.

    Contract: AgentManifest from nats_core.manifest, pydantic BaseModel
    Producer: TASK-FR-002
    """
    from nats_core.manifest import AgentManifest, InMemoryManifestRegistry, IntentCapability

    manifest = AgentManifest(
        agent_id="test-agent",
        name="Test Agent",
        template="base",
        intents=[IntentCapability(pattern="test.intent", confidence=0.9, description="test")],
    )

    registry = InMemoryManifestRegistry()
    await registry.register(manifest)

    result = await registry.get("test-agent")
    assert result is not None
    assert result.agent_id == "test-agent"
