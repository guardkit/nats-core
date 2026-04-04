# nats-core — Shared Contract Layer

The single source of truth for message schemas, topic constants, and NATS client
abstractions used by every agent, adapter, and service in the Ship's Computer fleet.

## Status: Pre-Implementation

System spec with BDD acceptance criteria ready at `docs/design/specs/nats-core-system-spec.md`.
Waiting on `python-library` template creation, then: `guardkit init python-library` → `/feature-spec` → `/feature-plan` → `autobuild`.

## What's In The Box

- **Message envelope** — Pydantic `MessageEnvelope` with versioning, correlation IDs, project scoping
- **Event schemas** — Typed payloads for pipeline (build started/progress/complete/failed), agent (status/approval/command/result), and Jarvis (intent/dispatch/notification) events
- **Topic registry** — `Topics.Pipeline.BUILD_STARTED`, `Topics.Agents.STATUS`, `Topics.Jarvis.DISPATCH` etc. No magic strings.
- **NATS client** — Thin typed wrapper around nats-py with convenience publish/subscribe per event type
- **Config** — pydantic-settings for NATS connection (`NATS_URL`, creds, timeouts)

## Install

```bash
pip install git+ssh://git@github.com/guardkit/nats-core.git
```

## Usage

```python
from nats_core import NATSClient, Topics, BuildCompletePayload

client = NATSClient()
await client.connect()

await client.publish_build_complete(BuildCompletePayload(
    feature_id="FEAT-AC1A",
    build_id="build-FEAT-AC1A-20260401120000",
    repo="guardkit/guardkitfactory",
    branch="feature/FEAT-AC1A",
    duration_seconds=1234,
    tasks_completed=6,
    tasks_failed=0,
    tasks_total=6,
    summary="All 6 tasks complete across 3 waves"
))
```

## Docs

- `docs/design/specs/nats-core-system-spec.md` — Full spec with BDD acceptance criteria (5 features)
- `docs/design/decisions/ADR-001-nats-as-event-bus.md` — Why NATS over Kafka/Redis
- `docs/design/decisions/ADR-002-schema-versioning.md` — Forward/backward compatibility strategy
- `docs/design/decisions/ADR-003-nats-py-vs-faststream.md` — nats-py for library, FastStream for services

## Part of the Jarvis Fleet

Every agent and adapter `pip install`s this. Schema changes require semver coordination.
This is the lowest-velocity, highest-impact package in the ecosystem.
