---
complexity: 4
consumer_context:
- consumes: NATSClient
  driver: nats-py
  format_note: call_agent_tool() is added to NATSClient class; uses nats-py request/reply
    via _nc.request(topic, payload_bytes, timeout=timeout); topic pattern is agents.{agent_id}.tools.{tool_name}
    (from Topics.Agents.TOOLS)
  framework: nats_core.client.NATSClient
  task: TASK-NC05
created: 2026-04-08 00:00:00+00:00
dependencies:
- TASK-NC05
feature_id: FEAT-1T1W
id: TASK-NC07
implementation_mode: task-work
parent_review: TASK-1T1W
priority: high
status: design_approved
tags:
- nats-client
- request-reply
- agent-tools
- rpc
task_type: feature
test_results:
  coverage: null
  last_run: null
  status: pending
title: call_agent_tool (request-reply)
updated: 2026-04-08 00:00:00+00:00
wave: 5
---

# Task: call_agent_tool (request-reply)

## Description

Extend `NATSClient` in `src/nats_core/client.py` with `call_agent_tool()` — the
agent-to-agent remote tool invocation method using NATS request/reply.

## Scope

### Method signature

```python
async def call_agent_tool(
    self,
    agent_id: str,
    tool_name: str,
    params: dict[str, Any],
    timeout: float = 30.0,
) -> Any:
    """Invoke a tool on a remote agent via NATS request-reply.

    Publishes to agents.{agent_id}.tools.{tool_name} and awaits response.

    Args:
        agent_id: Target agent identifier
        tool_name: Tool name from the agent's manifest
        params: Tool parameters matching the tool's JSON Schema
        timeout: Request timeout in seconds (default: 30.0)

    Returns:
        Deserialised response from the target agent (JSON-decoded)

    Raises:
        RuntimeError: If client is not connected
        TimeoutError: If the agent does not respond within timeout
    """
```

### Implementation steps

1. Raise `RuntimeError("client is not connected")` if `_nc is None`
2. Validate `agent_id` and `tool_name` — reject wildcards (`>`, `*`, `.`)
   with `ValueError`
3. Build topic: `Topics.resolve(Topics.Agents.TOOLS, agent_id=agent_id, tool_name=tool_name)`
4. Serialise request: `json.dumps(params).encode()`
5. Call `await _nc.request(topic, payload, timeout=timeout)`
6. On `nats.errors.NoRespondersError` or timeout: raise `TimeoutError` with message
   `"agent '{agent_id}' did not respond to tool '{tool_name}' within {timeout}s"`
7. Decode response: `json.loads(msg.data)` and return

## Acceptance Criteria

- [ ] `call_agent_tool()` before `connect()` raises `RuntimeError` with "not connected"
- [ ] `call_agent_tool("guardkit-factory", "lint", {})` publishes to `"agents.guardkit-factory.tools.lint"`
- [ ] Response from target agent is JSON-decoded and returned
- [ ] No response within `timeout` raises `TimeoutError` with agent_id and tool_name in message
- [ ] `agent_id="evil.>"` raises `ValueError` (wildcard rejection)
- [ ] `timeout` parameter is forwarded to `_nc.request()`
- [ ] All modified files pass project-configured lint/format checks with zero errors

## Seam Tests

```python
"""Seam test: verify NATSClient._nc.request() contract for call_agent_tool."""
import pytest


@pytest.mark.seam
@pytest.mark.integration_contract("NATSClient")
def test_call_agent_tool_topic_matches_agents_tools_template():
    """Verify call_agent_tool builds topic matching Topics.Agents.TOOLS pattern.

    Contract: call_agent_tool uses _nc.request() on agents.{agent_id}.tools.{tool_name};
    topic must exactly match Topics.Agents.TOOLS template resolution.
    Producer: TASK-NC05
    """
    from nats_core.topics import Topics

    topic = Topics.resolve(
        Topics.Agents.TOOLS, agent_id="guardkit-factory", tool_name="lint"
    )
    assert topic == "agents.guardkit-factory.tools.lint"
    assert "." in topic
    assert ">" not in topic
    assert "*" not in topic
```

## Implementation Notes

- Import `nats.errors` for `NoRespondersError` and timeout exceptions
- `params` serialisation: `json.dumps(params).encode()` — plain JSON, not `MessageEnvelope`
- Response is plain JSON (not envelope-wrapped) — the responding agent controls the format
- The `timeout` kwarg maps directly to nats-py `request(timeout=timeout)`
- nats-py raises `nats.errors.TimeoutError` on timeout — catch and re-raise as `TimeoutError`

## Coach Validation Commands

```bash
python -c "from nats_core.client import NATSClient; import inspect; assert 'call_agent_tool' in dir(NATSClient); print('OK')"
python -c "from nats_core.topics import Topics; print(Topics.resolve(Topics.Agents.TOOLS, agent_id='x', tool_name='y'))"
ruff check src/nats_core/client.py
mypy src/nats_core/client.py
```