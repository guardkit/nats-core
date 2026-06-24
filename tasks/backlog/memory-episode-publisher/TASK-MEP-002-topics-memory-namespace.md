---
id: TASK-MEP-002
title: Topics.Memory namespace (EPISODE + ALL) wired into ALL_TOPICS
status: backlog
created: 2026-06-24 00:00:00+00:00
updated: '2026-06-24T00:00:00+00:00'
priority: high
task_type: feature
tags:
- memory-publisher
- topics
- registry
complexity: 4
wave: 1
implementation_mode: task-work
parent_review: TASK-REV-MEP1
feature_id: FEAT-MEP1
dependencies: []
---

# Task: Topics.Memory namespace (EPISODE + ALL) wired into ALL_TOPICS

## Description

Add a new `Topics.Memory` namespace carrying the resolvable episode subject
template and the `memory.episode.>` wildcard, and wire it into the `ALL_TOPICS`
enumeration. This satisfies the seed AC "`memory.episode.>` present in the Topics
registry and validated by topic tests".

⚠️ **Silent-drop trap:** `ALL_TOPICS` is built by iterating a hard-coded 5-class
tuple `(Pipeline, Agents, Fleet, Jarvis, System)` at `topics.py:134`. If `Memory`
is **not** appended to that tuple, `Topics.Memory.EPISODE` is silently excluded
and **no existing test fails** (the count test would still read 27 and pass). The
fix and an explicit membership assertion are both required.

## Scope

### `src/nats_core/topics.py`

```python
class Memory(metaclass=_ImmutableNamespaceMeta):
    """Memory domain topics (post-Graphiti memory write path)."""

    EPISODE: str = "memory.episode.{project_id}.{episode_type}"
    ALL: str = "memory.episode.>"
```

- Add the `Memory` class after `System` (inside `Topics`).
- Append `Memory` to the `ALL_TOPICS` source tuple:
  `for cls in (Pipeline, Agents, Fleet, Jarvis, System, Memory)`.
- `EPISODE` is non-wildcard → **included** in `ALL_TOPICS` (count `27 → 28`).
- `ALL` contains `>` → **excluded** by the existing `">" not in v` filter (count unchanged).
- **Defer DLQ** (`memory.dlq.{project_id}`) to P2/P3 — reject-only P1 never publishes to it;
  a dead constant now would be wrong.

### `tests/test_topics.py`

- Update `test_all_topics_count`: `27 → 28`, and edit the adjacent count comment
  block (≈ lines 430–436) to add `Memory: 1 (excl ALL)` and revise `Total: 27` → `28`.
- Update module/class docstrings that say "five namespaces" → "six" (or extend to name `Memory`).
- Add `'memory.episode.'` to the patterns list in
  `test_no_hardcoded_topic_strings_outside_registry` (≈ line 355).
- New `TestTaskMemoryTopics` class (see Acceptance Criteria for the assertions).
- Add a `test_memory_constants` to `TestAllConstantsExist`.

## Acceptance Criteria

- [ ] `Topics.Memory.EPISODE == "memory.episode.{project_id}.{episode_type}"` and
      `Topics.Memory.ALL == "memory.episode.>"`; `Memory` uses `_ImmutableNamespaceMeta`
      (reassigning a constant raises `AttributeError`).
- [ ] `Memory` is appended to the `ALL_TOPICS` tuple; `Topics.Memory.EPISODE in Topics.ALL_TOPICS`
      is `True` and `Topics.Memory.ALL in Topics.ALL_TOPICS` is `False` — both asserted explicitly
      in `TestTaskMemoryTopics`.
- [ ] `Topics.resolve(Topics.Memory.EPISODE, project_id="finproxy", episode_type="feature_outcome")
      == "memory.episode.finproxy.feature_outcome"`; `episode_type="structured_json"` also resolves;
      `episode_type="evil.>"` raises `ValueError`.
- [ ] `tests/test_topics.py::test_all_topics_count` asserts `== 28` with the comment block updated to match.
- [ ] `'memory.episode.'` is added to the hardcoded-string patterns list so stray memory literals
      outside `topics.py` are caught.
- [ ] All modified files pass project-configured lint/format checks (ruff + mypy strict) with zero errors.

## Implementation Notes

- `Topics.resolve` already runs `_validate_identifier` on each kwarg — underscores
  pass, dots/spaces/wildcards reject — so `EPISODE` resolution needs no new validation code.
- Do **not** use `Topics.for_project` for memory subjects: `project_id` is already the
  first template segment, so prefixing would double it.

## Coach Validation Commands

```bash
python -c "from nats_core import Topics; print(Topics.resolve(Topics.Memory.EPISODE, project_id='finproxy', episode_type='feature_outcome'))"
python -c "from nats_core import Topics; print(Topics.Memory.ALL, Topics.Memory.EPISODE in Topics.ALL_TOPICS, Topics.Memory.ALL in Topics.ALL_TOPICS)"
python -c "from nats_core import Topics; print(len(Topics.ALL_TOPICS))"  # expect 28
pytest tests/test_topics.py -q
ruff check src/nats_core/topics.py tests/test_topics.py
mypy src/nats_core/topics.py
```
