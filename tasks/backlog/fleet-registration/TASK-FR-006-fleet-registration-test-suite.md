---
id: TASK-FR-006
title: Fleet Registration test suite (28 BDD scenarios)
status: backlog
task_type: testing
priority: high
created: 2026-04-08T00:00:00Z
updated: 2026-04-08T00:00:00Z
complexity: 4
parent_review: TASK-B5F3
feature_id: FEAT-FR01
wave: 5
implementation_mode: task-work
dependencies:
  - TASK-FR-004
  - TASK-FR-005
---

# TASK-FR-006: Fleet Registration test suite (28 BDD scenarios)

## Description

Implement the full test suite for the Fleet Registration feature, covering all 28 BDD
scenarios from `features/fleet-registration/fleet-registration.feature`.

All unit tests must run without a live NATS server. Use `InMemoryManifestRegistry` for
registry tests. Mock `KeyValue` for `NATSKVManifestRegistry` tests.

## Test Structure

```
tests/
└── fleet_registration/
    ├── conftest.py           # Factory functions (not fixtures)
    ├── test_models.py        # AgentManifest, IntentCapability, ToolCapability,
    │                         # AgentHeartbeatPayload, AgentDeregistrationPayload
    ├── test_registry.py      # ManifestRegistry ABC, InMemoryManifestRegistry
    ├── test_kv_registry.py   # NATSKVManifestRegistry (mocked KV)
    └── test_routing.py       # select_agent, record_heartbeat, check_timeouts
```

## Marker Configuration

Tests must use these markers (defined in `pyproject.toml`):

```ini
[tool.pytest.ini_options]
markers = [
    "smoke: critical path tests",
    "key_example: key BDD examples",
    "boundary: boundary condition tests",
    "negative: negative/rejection tests",
    "edge_case: edge case tests",
    "seam: integration contract boundary tests",
    "security: security-related tests",
    "concurrency: concurrency tests",
    "integration: tests requiring external services",
]
asyncio_mode = "auto"
```

## Factory Functions (conftest.py)

```python
# tests/fleet_registration/conftest.py
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class MockIntent:
    pattern: str = "software.build"
    signals: list[str] = field(default_factory=lambda: ["build", "compile"])
    confidence: float = 0.9
    description: str = "Build software"


@dataclass
class MockManifest:
    agent_id: str = "guardkit-factory"
    name: str = "GuardKit Factory"
    template: str = "factory"
    intents: list = field(default_factory=list)
    max_concurrent: int = 2


def make_intent(**overrides) -> dict:
    defaults = {"pattern": "software.build", "signals": ["build"], "confidence": 0.9, "description": "Build"}
    defaults.update(overrides)
    return defaults


def make_manifest(**overrides) -> dict:
    defaults = {
        "agent_id": "guardkit-factory",
        "name": "GuardKit Factory",
        "template": "factory",
        "intents": [make_intent()],
        "max_concurrent": 2,
    }
    defaults.update(overrides)
    return defaults
```

## BDD Scenario Coverage Map

### Smoke / Key-Example Tests (`test_registry.py`, `test_routing.py`)

| BDD Scenario | Test | Marker |
|---|---|---|
| Agent registers on startup | `test_agent_registers_appears_in_registry` | `@smoke @key_example` |
| Registration includes signal words | `test_registration_includes_signal_words` | `@key_example` |
| Agent begins heartbeating after registration | `test_heartbeat_record_created_on_registration` | `@smoke @key_example` |
| Graceful deregistration removes agent | `test_deregistration_removes_from_registry` | `@smoke @key_example` |
| New agent auto-discovered without router changes | `test_new_agent_discovered_via_find_by_intent` | `@key_example` |
| Registration survives router restart via KV | `test_kv_registry_persists_across_reconnect` | `@key_example` |

### Boundary Tests (`test_models.py`, `test_routing.py`)

| BDD Scenario | Test | Marker |
|---|---|---|
| Confidence 0.0 accepted | `test_confidence_boundary_zero_accepted` | `@boundary` |
| Confidence 0.5 accepted | `test_confidence_boundary_mid_accepted` | `@boundary` |
| Confidence 1.0 accepted | `test_confidence_boundary_one_accepted` | `@boundary` |
| Confidence -0.1 rejected | `test_confidence_below_zero_rejected` | `@boundary @negative` |
| Confidence 1.1 rejected | `test_confidence_above_one_rejected` | `@boundary @negative` |
| max_concurrent 1 accepted | `test_max_concurrent_one_accepted` | `@boundary` |
| max_concurrent 0 rejected | `test_max_concurrent_zero_rejected` | `@boundary @negative` |
| Heartbeat at 89s does not timeout | `test_heartbeat_89s_still_available` | `@boundary` |
| Heartbeat at 90s triggers timeout | `test_heartbeat_90s_triggers_timeout` | `@boundary` |
| Empty intents rejected | `test_empty_intents_registration_rejected` | `@boundary @negative` |
| Heartbeat queue_depth 0 valid | `test_heartbeat_queue_depth_zero_valid` | `@boundary` |

### Negative Tests (`test_models.py`, `test_registry.py`, `test_routing.py`)

| BDD Scenario | Test | Marker |
|---|---|---|
| Missing agent_id rejected | `test_missing_agent_id_rejected` | `@negative` |
| Missing name rejected | `test_missing_name_rejected` | `@negative` |
| Missing template rejected | `test_missing_template_rejected` | `@negative` |
| Re-registration updates existing entry | `test_reregistration_upserts_not_duplicates` | `@negative` |
| Deregistration of unknown agent ignored | `test_deregistration_unknown_agent_ignored` | `@negative` |
| Heartbeat from unregistered agent ignored | `test_heartbeat_unregistered_agent_ignored` | `@negative` |
| No matching agent not dispatched | `test_no_matching_intent_returns_none` | `@negative` |

### Edge Case Tests (`test_routing.py`, `test_kv_registry.py`)

| BDD Scenario | Test | Marker |
|---|---|---|
| Confidence-based routing selects best agent | `test_routing_selects_highest_confidence` | `@edge_case` |
| Queue-depth tiebreak | `test_routing_tiebreak_by_queue_depth` | `@edge_case` |
| max_concurrent capacity skips agent | `test_routing_skips_at_capacity_agent` | `@edge_case` |
| Heartbeat timeout marks unavailable | `test_timeout_marks_agent_unavailable` | `@edge_case` |
| Agent recovers by resuming heartbeats | `test_agent_recovers_after_timeout` | `@edge_case` |
| Re-registration overwrites capabilities | `test_reregistration_overwrites_capabilities` | `@edge_case @security` |
| Metadata > 64KB rejected | `test_metadata_exceeds_64kb_rejected` | `@edge_case @security` |
| Concurrent same-agent registrations: last-write-wins | `test_concurrent_registration_last_write_wins` | `@edge_case @concurrency` |
| Deregistration takes precedence over concurrent heartbeat | `test_deregistration_over_concurrent_heartbeat` | `@edge_case @concurrency` |
| KV unavailable fails gracefully | `test_kv_unavailable_graceful_failure` | `@edge_case @integration` |
| Empty fleet returns no capable agent | `test_empty_fleet_no_dispatch` | `@edge_case @integration` |

## Acceptance Criteria

- [ ] All 28 BDD scenarios have a corresponding test function
- [ ] All tests are `async` and use `asyncio_mode = "auto"`
- [ ] All unit tests pass without a live NATS server
- [ ] `NATSKVManifestRegistry` tests mock `KeyValue` via `unittest.mock`
- [ ] `conftest.py` uses factory functions (not stateful fixtures)
- [ ] All markers from the BDD scenario map are applied correctly
- [ ] Coverage for `manifest.py`, `_routing.py`, `events/fleet.py`, and `client.py` (fleet parts) >= 90%
- [ ] `@smoke` tests are the minimal runnable set (3 tests) — verify with `pytest -m smoke`

## Implementation Notes

- Use `from nats_core.manifest import AgentManifest, IntentCapability, ...` — always import from public API
- For `NATSKVManifestRegistry`, mock `entry.value` to return `manifest.model_dump_json().encode()`
- Time-based tests (`check_timeouts`) inject `time.monotonic` via monkeypatching or by setting `last_seen` directly on `HeartbeatRecord`
- Concurrent tests use `asyncio.gather()` to simulate simultaneous calls
