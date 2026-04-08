---
id: TASK-NC08
title: "Unit tests (config, topics, events, manifest, agent_config)"
status: pending
created: 2026-04-08T00:00:00Z
updated: 2026-04-08T00:00:00Z
priority: high
task_type: testing
tags: [nats-client, unit-tests, pytest, declarative-modules]
complexity: 4
wave: 6
implementation_mode: direct
parent_review: TASK-1T1W
feature_id: FEAT-1T1W
dependencies: [TASK-NC01, TASK-NC02, TASK-NC03, TASK-NC04]
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Unit tests (config, topics, events, manifest, agent_config)

## Description

Write the unit test suite for all declarative modules: `config.py`, `topics.py`,
`events/`, `manifest.py`, and `agent_config.py`. These tests run without a NATS
server. Integration tests (with a live server) are in TASK-NC09.

## Scope

### Test files

```
tests/
    conftest.py              (factory functions — extend existing or create)
    test_config.py           (NATSConfig, AgentConfig)
    test_topics.py           (Topics.resolve, for_project, ALL_TOPICS, validation)
    test_events.py           (all 13 payload models)
    test_manifest.py         (AgentManifest, ManifestRegistry ABC, InMemoryManifestRegistry)
    test_agent_config.py     (AgentConfig, ModelConfig, GraphitiConfig)
```

### conftest.py — factory functions

```python
from dataclasses import dataclass, field
from nats_core.manifest import AgentManifest, IntentCapability, ToolCapability
from nats_core.config import NATSConfig

@dataclass
class MockAgent:
    agent_id: str = "test-agent"
    name: str = "Test Agent"
    template: str = "basic"

def make_agent(**overrides) -> MockAgent:
    defaults = {"agent_id": "test-agent", "name": "Test Agent", "template": "basic"}
    defaults.update(overrides)
    return MockAgent(**defaults)

def make_agent_manifest(**overrides) -> AgentManifest:
    defaults = {"agent_id": "test-agent", "name": "Test Agent", "template": "basic"}
    defaults.update(overrides)
    return AgentManifest(**defaults)

def make_nats_config(**overrides) -> NATSConfig:
    defaults = {}
    defaults.update(overrides)
    return NATSConfig(**defaults)
```

### Key test scenarios by module

**test_config.py:**
- `NATSConfig()` uses all defaults
- `NATSConfig(url="nats://remote:4222")` overrides url
- Field types are correct (`connect_timeout` is float, `max_reconnect_attempts` is int)
- `NATSConfig` reads `NATS_URL` env var (use `monkeypatch.setenv`)

**test_topics.py:**
- `Topics.resolve(Topics.Pipeline.BUILD_COMPLETE, feature_id="FEAT-001")` → correct string
- `Topics.for_project("finproxy", "pipeline.x")` → `"finproxy.pipeline.x"`
- `Topics.resolve()` raises `KeyError` on missing placeholder
- `Topics.resolve()` raises `ValueError` on wildcard chars in values (`"evil.>"`, `"FEAT.*"`)
- Deeply nested template: `agents.approval.{agent_id}.{task_id}.response`
- `Topics.ALL_TOPICS` contains all expected templates
- Wildcard topic constants (`pipeline.>`, `fleet.>`) are present unchanged

**test_events.py:**
- All 13 payload models instantiate with required fields
- `ConfigDict(extra="ignore")` — unknown fields are silently dropped
- `AgentHeartbeatPayload(agent_id="x")` has `metadata == {}` (mutable default factory, not shared)
- `AgentHeartbeatPayload` instances don't share metadata dict (no mutable default aliasing)
- `BuildCompletePayload` serialises to JSON and round-trips cleanly

**test_manifest.py:**
- `AgentManifest` instantiates with all defaults
- `IntentCapability.confidence=1.1` raises `ValidationError`
- `ManifestRegistry()` raises `TypeError` (abstract)
- `InMemoryManifestRegistry.register()` stores; `get()` retrieves
- `InMemoryManifestRegistry.deregister("unknown")` does not raise
- `InMemoryManifestRegistry.find_by_intent("software.build")` finds correct agents
- `InMemoryManifestRegistry.find_by_tool("lint")` finds agents with that tool
- `AgentManifest` does NOT import from `nats_core.events` (circular dep check)

**test_agent_config.py:**
- `AgentConfig(models=ModelConfig(reasoning_model="gpt-4"))` instantiates
- `AgentConfig` without `models` raises `ValidationError`
- Heartbeat invariant: `heartbeat_timeout_seconds > heartbeat_interval_seconds` — invalid config raises `ValidationError`
- `AgentConfig.nats` is a valid `NATSConfig` instance by default

### Markers

Apply `@pytest.mark.unit` to all tests in this task. These tests must pass with no NATS server.

## Acceptance Criteria

- [ ] All tests pass with `pytest tests/ -m unit -v`
- [ ] No tests use `pytest.fixture` with mutable state — use factory functions from `conftest.py`
- [ ] `test_events.py` verifies mutable default isolation for `AgentHeartbeatPayload.metadata`
- [ ] `test_manifest.py` verifies abstract base raises `TypeError`
- [ ] `test_topics.py` covers wildcard rejection scenarios from BDD spec
- [ ] `test_config.py` uses `monkeypatch.setenv` for env var tests
- [ ] Coverage for declarative modules >= 90% (enforce with `--cov-fail-under=90`)

## Implementation Notes

- Use `pytest.mark.asyncio` (or `asyncio_mode = "auto"` from pyproject.toml) for `InMemoryManifestRegistry` async method tests
- Do NOT mock nats-py — these are unit tests for pure declarative models, no mocking needed
- `conftest.py` factory functions should live in `tests/conftest.py` (shared)

## Coach Validation Commands

```bash
pytest tests/test_config.py tests/test_topics.py tests/test_events.py tests/test_manifest.py tests/test_agent_config.py -v -m unit
pytest tests/ -m unit --cov=src/nats_core --cov-report=term-missing --cov-fail-under=90
```
