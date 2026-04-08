---
id: TASK-NC01
title: NATSConfig + AgentConfig declarative models
status: in_review
created: 2026-04-08 00:00:00+00:00
updated: 2026-04-08 00:00:00+00:00
priority: high
task_type: declarative
tags:
- nats-client
- config
- pydantic-settings
complexity: 2
wave: 1
implementation_mode: direct
parent_review: TASK-1T1W
feature_id: FEAT-1T1W
dependencies:
- TASK-ME01
test_results:
  status: pending
  coverage: null
  last_run: null
autobuild_state:
  current_turn: 1
  max_turns: 30
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/nats-core/.guardkit/worktrees/FEAT-3845
  base_branch: main
  started_at: '2026-04-08T21:43:50.112031'
  last_updated: '2026-04-08T21:51:19.039502'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-04-08T21:43:50.112031'
    player_summary: 'Created src/nats_core/agent_config.py with three pydantic models:
      ModelConfig (nested BaseModel for LLM endpoints, reasoning_model required),
      GraphitiConfig (nested BaseModel for knowledge graph settings with defaults),
      and AgentConfig (BaseSettings with env_prefix=''AGENT_'' and env_nested_delimiter=''__'').
      AgentConfig requires ''models'' field (no default), nests NATSConfig with default_factory,
      includes heartbeat/timeout fields with ge=1 constraints, API keys as SecretStr
      for masking, and a model_'
    player_success: true
    coach_success: true
---

# Task: NATSConfig + AgentConfig declarative models

## Description

Implement `src/nats_core/config.py` and `src/nats_core/agent_config.py` — the two
pydantic-settings configuration models that serve as the foundation for all client
construction and agent runtime configuration.

## Scope

### `config.py` — NATSConfig

`BaseSettings` with `env_prefix="NATS_"`. Fields:

| Field | Type | Default | Env Var |
|-------|------|---------|---------|
| `url` | `str` | `"nats://localhost:4222"` | `NATS_URL` |
| `connect_timeout` | `float` | `5.0` | `NATS_CONNECT_TIMEOUT` |
| `reconnect_time_wait` | `float` | `2.0` | `NATS_RECONNECT_TIME_WAIT` |
| `max_reconnect_attempts` | `int` | `60` | `NATS_MAX_RECONNECT_ATTEMPTS` |
| `name` | `str` | `"nats-core-client"` | `NATS_NAME` |
| `user` | `str \| None` | `None` | `NATS_USER` |
| `password` | `str \| None` | `None` | `NATS_PASSWORD` |
| `creds_file` | `str \| None` | `None` | `NATS_CREDS_FILE` |

### `agent_config.py` — AgentConfig, ModelConfig, GraphitiConfig

`BaseSettings` with `env_prefix="AGENT_"`, `env_nested_delimiter="__"`.

**ModelConfig** (nested):

| Field | Type | Default |
|-------|------|---------|
| `reasoning_model` | `str` | required |
| `reasoning_endpoint` | `str` | `""` |
| `implementation_model` | `str \| None` | `None` |
| `implementation_endpoint` | `str \| None` | `None` |
| `embedding_model` | `str \| None` | `None` |
| `embedding_endpoint` | `str \| None` | `None` |

**GraphitiConfig** (nested, optional):

| Field | Type | Default |
|-------|------|---------|
| `endpoint` | `str` | `"bolt://localhost:7687"` |
| `default_group_ids` | `list[str]` | `["appmilla-fleet"]` |

**AgentConfig** (root):

| Field | Type | Default | Env Pattern |
|-------|------|---------|-------------|
| `models` | `ModelConfig` | required | `AGENT_MODELS__*` |
| `graphiti` | `GraphitiConfig \| None` | `None` | `AGENT_GRAPHITI__*` |
| `nats` | `NATSConfig` | default | `AGENT_NATS__*` |
| `langsmith_project` | `str \| None` | `None` | `AGENT_LANGSMITH_PROJECT` |
| `langsmith_api_key` | `str \| None` | `None` | `AGENT_LANGSMITH_API_KEY` |
| `heartbeat_interval_seconds` | `int` | `30` | `AGENT_HEARTBEAT_INTERVAL_SECONDS` |
| `heartbeat_timeout_seconds` | `int` | `90` | `AGENT_HEARTBEAT_TIMEOUT_SECONDS` |
| `max_task_timeout_seconds` | `int` | `600` | `AGENT_MAX_TASK_TIMEOUT_SECONDS` |
| `gemini_api_key` | `str \| None` | `None` | `AGENT_GEMINI_API_KEY` |
| `anthropic_api_key` | `str \| None` | `None` | `AGENT_ANTHROPIC_API_KEY` |
| `openai_api_key` | `str \| None` | `None` | `AGENT_OPENAI_API_KEY` |

**Invariant:** `AgentConfig` is LOCAL to each agent — never published to `fleet.register`.

## Acceptance Criteria

- [ ] `NATSConfig()` instantiates with all defaults without any env vars set
- [ ] `NATSConfig(url="nats://remote:4222")` overrides correctly
- [ ] `NATSConfig` reads from `NATS_URL` and other env vars
- [ ] `AgentConfig` requires `models` to be provided (no default)
- [ ] `AgentConfig.nats` is a valid `NATSConfig` (can be standalone or nested)
- [ ] `heartbeat_timeout_seconds` > `heartbeat_interval_seconds` is invariant (validate via `model_validator`)
- [ ] Both modules have `from __future__ import annotations`
- [ ] All fields have `Field(description=...)`
- [ ] `py.typed` exists in `src/nats_core/`
- [ ] All modified files pass project-configured lint/format checks with zero errors

## Implementation Notes

- Use `pydantic_settings.BaseSettings` (not plain `BaseModel`) for both
- `NATSConfig` can be imported standalone OR nested inside `AgentConfig`
- API keys in `AgentConfig` must come from environment only — never committed
- Add `model_validator(mode="after")` to `AgentConfig` to assert heartbeat invariant

## Coach Validation Commands

```bash
python -c "from nats_core.config import NATSConfig; c = NATSConfig(); print(c.url)"
python -c "from nats_core.agent_config import AgentConfig, ModelConfig; a = AgentConfig(models=ModelConfig(reasoning_model='gpt-4')); print(a.heartbeat_interval_seconds)"
ruff check src/nats_core/config.py src/nats_core/agent_config.py
mypy src/nats_core/config.py src/nats_core/agent_config.py
```
