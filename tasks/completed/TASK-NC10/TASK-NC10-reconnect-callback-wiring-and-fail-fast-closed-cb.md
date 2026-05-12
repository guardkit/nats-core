---
id: TASK-NC10
title: "Wire reconnect/disconnect/closed callbacks into NATSClient + default fail-fast closed_cb"
status: completed
created: 2026-05-12T00:00:00+00:00
updated: 2026-05-12T12:45:00+00:00
completed: 2026-05-12T12:45:00+00:00
completed_location: tasks/completed/TASK-NC10/
priority: high
task_type: feature
feature_id: FEAT-NCRC
tags:
  - nats-client
  - reliability
  - fleet-hygiene
  - reconnect
  - demo-blocker
complexity: 3
wave: null
implementation_mode: task-work
parent_review: null
dependencies: []
cross_repo_origin:
  triggered_by: jarvis FEAT-JARVIS-006 GB10 verification rerun (2026-05-12)
  pattern_source: jarvis TASK-J006-010 (jarvis bypasses nats_core.NATSClient and built its own callback wiring at jarvis/src/jarvis/infrastructure/nats_client.py)
  evidence: jarvis/docs/runbooks/RESULTS-FEAT-JARVIS-006-serve-nats-first-run-2026-05-12-rerun-post-J006-009-010.md (§"Specialist reconnect gap")
  downstream_consumers:
    - specialist-agent TASK-NATS-009 (depends on this task)
    - study-tutor TASK-NATS-FIX-006 (depends on this task)
---

# Task: Wire reconnect/disconnect/closed callbacks into NATSClient + default fail-fast closed_cb

## Severity / impact

**High — demo-blocker for 2026-05-16 DDD Southwest.**

`nats_core.NATSClient.connect()` calls `await nats.connect(**connect_kwargs)` but never wires
`reconnected_cb`, `disconnected_cb`, or `closed_cb`. Two consequences for every consumer that
uses `NATSClient`:

1. **Silent stale registration after broker bounce.** Consumers may define their own
   `_on_reconnect()` handler (e.g. specialist-agent at
   `src/specialist_agent/adapters/nats_adapter.py:254`) intended to re-publish the agent
   manifest, but there is no API path to register it. After a broker restart, nats-py
   reconnects at the TCP layer but the agent never re-registers in `agent-registry` KV.
   The container stays `Up`; fleet orchestration silently can't reach it.
2. **No observable terminal failure.** With `max_reconnect_attempts=60` and
   `reconnect_time_wait=2.0` (the `NATSConfig` defaults at `src/nats_core/config.py:45-49`),
   nats-py gives up after ~120 s of reconnect attempts and enters a fully-closed state with
   no signal. The container keeps running but is dead from a fleet perspective.

This is the root cause of the symptom captured in jarvis's 2026-05-12 GB10 rerun:
`architect-agent` and `product-owner-agent` containers `Up 20 hours`, absent from
`agent-registry` KV, recovering only via manual `docker restart`.

## Evidence

See `jarvis/docs/runbooks/RESULTS-FEAT-JARVIS-006-serve-nats-first-run-2026-05-12-rerun-post-J006-009-010.md`
→ §"Other findings" → "Specialist reconnect gap" and §"Session housekeeping".

Reproduction (against any nats_core.NATSClient-using consumer):
1. Start the consumer; verify it appears in `nats kv ls agent-registry`.
2. `docker stop ships-computer-nats && sleep 15 && docker start ships-computer-nats`.
3. Wait ~5 s; check `nats kv ls agent-registry`. The consumer is absent.
4. Container logs show ConnectionRefusedError x N then silence; no recovery without restart.

## Root cause

`nats_core/client.py:60-75` (`NATSClient.connect`):

```python
async def connect(self) -> None:
    if self._nc is not None:
        raise RuntimeError("client is already connected")
    connect_kwargs = self._config.to_connect_kwargs()
    self._nc = await nats.connect(**connect_kwargs)
```

And `NATSConfig.to_connect_kwargs()` at `nats_core/config.py:157-182` builds the kwargs from
`servers`, `connect_timeout`, `reconnect_time_wait`, `max_reconnect_attempts`, `name`, and
auth — **no callback fields**. Consumers therefore have no way to react to reconnect,
disconnect, or terminal close events.

## Recommended fix

### 1. Add callback parameters to `NATSClient` constructor

```python
class NATSClient:
    def __init__(
        self,
        config: NATSConfig,
        source_id: str | None = None,
        *,
        reconnected_cb: Callable[[], Awaitable[None]] | None = None,
        disconnected_cb: Callable[[], Awaitable[None]] | None = None,
        closed_cb: Callable[[], Awaitable[None]] | None = None,
        error_cb: Callable[[Exception], Awaitable[None]] | None = None,
    ) -> None:
        ...
        self._reconnected_cb = reconnected_cb
        self._disconnected_cb = disconnected_cb
        self._closed_cb = closed_cb or self._default_closed_cb
        self._error_cb = error_cb
        self._terminally_closed = asyncio.Event()
```

All four callback params default to `None` so existing call sites (`specialist-agent`,
`study-tutor`) keep compiling.

### 2. Pass callbacks through `to_connect_kwargs()` consumer

In `NATSClient.connect()`, merge the callbacks into the kwargs dict before the
`nats.connect(...)` call:

```python
connect_kwargs = self._config.to_connect_kwargs()
if self._reconnected_cb is not None:
    connect_kwargs["reconnected_cb"] = self._reconnected_cb
if self._disconnected_cb is not None:
    connect_kwargs["disconnected_cb"] = self._disconnected_cb
connect_kwargs["closed_cb"] = self._closed_cb  # always set (default exists)
if self._error_cb is not None:
    connect_kwargs["error_cb"] = self._error_cb
self._nc = await nats.connect(**connect_kwargs)
```

Do **not** push callbacks into `NATSConfig` itself — pydantic-settings does not model
`Callable` cleanly and callbacks are runtime behaviour, not env-loaded configuration.

### 3. Default `closed_cb` that surfaces terminal failure

```python
async def _default_closed_cb(self) -> None:
    logger.error(
        "nats_terminally_closed",
        extra={
            "nats_url": self._config.url,  # nats:// scheme, no creds in URL
            "source_id": self._source_id,
            "max_reconnect_attempts": self._config.max_reconnect_attempts,
            "reconnect_time_wait": self._config.reconnect_time_wait,
        },
    )
    self._terminally_closed.set()
```

Expose `terminally_closed: asyncio.Event` as a public read-only attribute. Consumers can
`await client.terminally_closed.wait()` in a supervisor task to drive process exit. They
can also pass a custom `closed_cb=` to override the default entirely.

### 4. Public attribute for consumer supervisors

```python
@property
def terminally_closed(self) -> asyncio.Event:
    """Event set when the NATS connection has reached terminal-closed state.

    Set automatically by the default ``closed_cb``. Consumers may ``await`` this
    in a supervisor task to drive their own fail-fast / process-exit behaviour.
    """
    return self._terminally_closed
```

## Acceptance criteria

| AC | Description |
|---|---|
| AC-NC10-01 | `NATSClient.__init__` accepts `reconnected_cb`, `disconnected_cb`, `closed_cb`, `error_cb` as optional keyword-only params. Existing call sites in this repo's test suite continue to construct `NATSClient(config, source_id=...)` without changes. |
| AC-NC10-02 | When provided, callbacks are passed through to `nats.connect(...)` via `connect_kwargs`. Verify with a unit test that mocks `nats.connect` and asserts the kwargs received. |
| AC-NC10-03 | Default `closed_cb` (used when caller passes `closed_cb=None`) logs structured `nats_terminally_closed` ERROR with `nats_url`, `source_id`, `max_reconnect_attempts`, `reconnect_time_wait` fields. |
| AC-NC10-04 | Default `closed_cb` sets `client.terminally_closed: asyncio.Event`. The event is exposed as a read-only property. Unit test asserts `is_set()` is `False` before triggering the cb and `True` after. |
| AC-NC10-05 | Caller-provided `closed_cb=` replaces the default entirely (caller is responsible for setting any event of their own if they want it). Unit test asserts the custom callback is invoked and the default's log line is NOT emitted. |
| AC-NC10-06 | Integration test (against a live broker or testcontainers NATS): start `NATSClient` with all four callbacks wired to mocks, stop the broker, wait `max_reconnect_attempts * reconnect_time_wait + 2s`, assert `disconnected_cb` invoked ≥1x and `closed_cb` invoked exactly once. |
| AC-NC10-07 | No regression in existing tests (`tests/test_client.py`, `tests/test_client_integration.py`, `tests/fleet_registration/`). |

## Out of scope

- Lifting `max_reconnect_attempts` from 60 to infinite. The 60×2 s envelope is enough for a
  short broker bounce; for longer broker outages we *want* the terminal-closed signal so
  supervisors can exit non-zero and be restarted by Docker / systemd.
- Adding a higher-level `AgentLifecycle` helper that owns connect+register+heartbeat. That
  is the right post-demo refactor (see Option 2 in the design discussion in
  specialist-agent TASK-NATS-009) but out of scope here.
- Changing `NATSConfig` field defaults or env-var names.
- Changing the `connect()` is-already-connected check or any other state-machine logic.

## Related work

- `jarvis/src/jarvis/infrastructure/nats_client.py` — jarvis bypassed nats_core and wired
  its own `reconnected_cb` / `disconnected_cb` / `closed_cb` directly into `nats.connect()`.
  That implementation is the reference for the cb signatures and the structured-logging
  approach. nats-core should adopt the same shape so jarvis can eventually migrate back to
  using `nats_core.NATSClient` instead of maintaining its own copy.
- `specialist-agent/tasks/backlog/TASK-NATS-009-...md` — consumer task: wires existing
  `NATSAdapter._on_reconnect` as `reconnected_cb` and adds `_on_closed` for fail-fast.
- `study-tutor/tasks/backlog/TASK-NATS-FIX-006-...md` — consumer task: study-tutor's
  adapter currently has no reconnect handling at all; this task adds it and wires through.

## Demo-day note (2026-05-16 DDD Southwest)

This task blocks both consumer tasks. Land order:

1. This task (TASK-NC10) — nats-core API change, backwards-compatible default.
2. specialist-agent TASK-NATS-009 — uses the new API; mechanical (handler already exists).
3. study-tutor TASK-NATS-FIX-006 — uses the new API; needs to design `_on_reconnect` from
   scratch since study-tutor's adapter doesn't have one.

If TASK-NC10 slips past 2026-05-15, the fallback for demo is the operator workaround
described in specialist-agent TASK-NATS-009 (manually check `nats kv ls agent-registry`
shortly before the demo).
