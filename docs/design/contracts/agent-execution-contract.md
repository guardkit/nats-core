# Agent Command/Result Execution Contract of Record

**Bounded Context:** Message Contracts (envelope.py, events/_agent.py, topics.py)
**Protocols:** NATS Events, Python Public API
**Version:** 1.0.0
**Date:** 2026-07-11
**Provenance:** Mode-P execution-contract fix (DISPATCHFMT), mismatch ids M1–M7 + M10

---

## Purpose

This document is the **single, authoritative wire contract** for how a dispatcher
(forge) commands a specialist agent (specialist-agent) and how that agent replies.
It exists because forge and specialist-agent independently drifted from the shared
`nats-core` shapes — forge published a bare `dict` command, subscribed on the wrong
result subject, and required correlation/identity in NATS headers, while the deployed
specialist parses a strict `MessageEnvelope`, routes a static verb set, and replies
fire-and-forget with the correlation in the message **body**. Every load-bearing
mismatch is enumerated below.

> **Contract home rule.** Both forge and specialist-agent **MUST import these shapes
> from `nats-core`** (`MessageEnvelope`, `EventType`, `CommandPayload`, `ResultPayload`,
> `Topics`). Neither side may keep a local copy or re-declaration of the envelope or
> payload models. Local envelope copies are exactly how this contract drifted; a
> single imported source of truth is the only supported configuration.

---

## Command (dispatcher → agent)

| Field | Value |
|-------|-------|
| Subject | `Topics.Agents.COMMAND` → `agents.command.{agent_id}` (3-token) |
| Wire body | `MessageEnvelope` (JSON, `model_dump_json`) |
| `envelope.source_id` | dispatcher identity, e.g. `"forge"` (min_length=1) |
| `envelope.event_type` | `EventType.COMMAND` |
| `envelope.correlation_id` | the dispatch correlation key (echoed in the body) |
| `envelope.payload` | a `CommandPayload` as a plain dict |

`CommandPayload` (`nats_core.events.CommandPayload`):

| Field | Value |
|-------|-------|
| `command` | a **deployed verb** from the target agent's `command_map` (min_length=1) |
| `args` | `dict` carrying **every required arg** that verb's handler reads |
| `correlation_id` | same value as `envelope.correlation_id` |

**Deployed verb set (static, verified in-container against the 13-day image / nats-core 0.4.0):**
`{idea, extract, greenfield, evolve, impact, scope}` for the product-owner agent.
The dispatcher resolves the Mode-P stage to a verb per contract decision **D1**:

- **product-owner (product_docs stage)** → `greenfield`; routes to `_handle_po_greenfield`;
  required arg `problem_statement` carries the planning request's real text.
- **architect (architecture stage)** → `greenfield`; routes to `_handle_greenfield`;
  required args `docs_path` + `scope`. `greenfield` is the architect's from-scratch
  analog — its other verbs (`align`/`explore`/`feasibility`) are revise/inspect/quick-check
  modes. The `agents.command.{agent_id}` subject disambiguates which handler runs; the
  two containers **overload** the same verb name onto different handlers.

**Routing gates the command must pass in the deployed router (`command_router.py`):**

1. `envelope.event_type == EventType.COMMAND` (step-1 gate; anything else is not routed).
2. `command_map.get(command)` must hit (an unknown verb → `"Command not supported"`).
3. `_check_required_args`: every required key for that verb must be present in `args`.

**Correlation source (D2):** the router reads correlation from the **body only** —
`cmd_payload.correlation_id` first, `envelope.correlation_id` as fallback
(`command_router.py:376`). It never reads NATS headers. Headers **MAY** be retained
for tracing but **nothing may depend on them**.

**Forward-context / flag parameters (D3):** dropped from the wire `args` unless a
deployed handler is verified (via `docker exec cat`) to read them, in which case they
map into `args["context"]`. No `greenfield` handler reads a generic `context`/`parameters`
arg, so those are not serialised — sensitive parameter values never reach the broker.

---

## Result (agent → dispatcher)

The dispatcher publishes **fire-and-forget** (no `reply_to`), so the deployed agent
takes the fire-and-forget branch of `command_router._publish_result`: it envelope-wraps
a `ResultPayload` and publishes it with **no headers**.

| Field | Value |
|-------|-------|
| Subject | `Topics.Agents.RESULT` → `agents.result.{agent_id}` (3-token, **no** correlation suffix) |
| Wire body | `MessageEnvelope` (JSON, no headers) |
| `envelope.source_id` | the replying agent id (this is the reply's identity — **not** a header) |
| `envelope.event_type` | `EventType.RESULT` |
| `envelope.correlation_id` | the request correlation, echoed in the body |
| `envelope.payload` | a `ResultPayload` as a plain dict |

`ResultPayload` (`nats_core.events.ResultPayload`):

| Field | Value |
|-------|-------|
| `command` | the verb that was executed |
| `result` | `dict` of result data (see result-dict convention below) |
| `correlation_id` | echoes the request correlation |
| `success` | `bool` |

**Reply transport (D2):** the dispatcher subscribes on the **3-token** `agents.result.{agent_id}`
(one shared subscription per agent) and **demuxes replies by the BODY correlation** —
`ResultPayload.correlation_id`, falling back to `envelope.correlation_id`. It does **not**
use request/reply inboxes and does **not** append a `.{correlation}` subject segment
(that 4-token subject never matched the agent's 3-token publish). Reply source identity
comes from `envelope.source_id`. The **wrong-correlation-drop invariant** is preserved on
the body value: a reply whose correlation matches no in-flight binding is dropped, never
crashes.

**Failure semantics:** `success=False` with `result={"error": <message>}`. The dispatcher
branches on `success` and surfaces the error as a dispatch failure.

**Result-dict convention** (the deployed `adapters/result_wrapper.wrap_role_output` shape,
verified in-container — copy verbatim, never hand-invent):

```jsonc
{
  "role_id": "product-owner",
  "coach_score": 0.82,
  "criterion_breakdown": [
    // criterion_breakdown is a LIST of these objects (NOT a dict):
    {"criterion": "clarity", "score": 0.9, "weight": 0.5, "rationale": "clear"},
    {"criterion": "completeness", "score": 0.74, "weight": 0.5, "rationale": "mostly complete"}
  ],
  "detection_findings": [
    {"pattern": "vague-scope", "severity": "low", "description": "...", "location": "problem_statement"}
  ],
  "role_output": {
    // role_output is the REAL role document — this is what becomes product_docs,
    // NOT coach_score / criterion_breakdown (those are coach evidence only).
    "title": "...",
    "problem_statement": "...",
    "user_stories": [ /* ... */ ]
  }
}
```

`coach_score` and `criterion_breakdown` are **coach evidence**; the deliverable document
is `role_output`.

---

## Mismatch register (provenance)

The mismatches this contract closes, discovered by the DISPATCHFMT discovery pass and
fixed forge-side (nats-core needed no code change — decision **D4**):

| Id | Mismatch | Resolution |
|----|----------|------------|
| M1 | forge published a bare `dict`; deployed inbound parse (`MessageEnvelope.model_validate_json` in `subscribe_with_reply`, **before** the router callback) raised `3 validation errors: source_id / event_type / payload` and silently **dropped** the message. | Publish a canonical `MessageEnvelope`. |
| M2 | `CommandPayload.command` was a non-routing placeholder, not a deployed verb → `command_map.get` miss → `"Command not supported"`. | Resolve a real deployed verb (`greenfield`). |
| M3 | `args` was a `{"parameters": [...]}` blob no handler reads; the verb's required keys were absent → `_check_required_args` rejected. | Send a `dict` carrying every required arg. |
| M4 | forge subscribed on the 4-token `agents.result.{agent_id}.{correlation}`; the deployed agent publishes on 3-token `agents.result.{agent_id}` → NATS token-prefix mismatch, reply never delivered. | Subscribe on the 3-token `Topics.Agents.RESULT`. |
| M5 | correlation/source were expected in NATS **headers**; the command must carry correlation in the envelope body and the deployed reply carries correlation in the **body** and **no headers**. | Correlation on the envelope + `CommandPayload`/`ResultPayload` body; demux by body value. |
| M6 | forge's reply envelope required a top-level `agent_id`; the deployed reply carries none (identity is `envelope.source_id`). | Read source from `envelope.source_id`; drop the `agent_id` requirement. |
| M7 | `criterion_breakdown` was expected as a `dict`; the deployed agent emits a **LIST** of `{criterion, score, weight, rationale}`. | Accept the list shape. |
| M10 | the real deliverable lives under `result.role_output`, not `coach_score`/`criterion_breakdown`; forge was not extracting it into `product_docs`. | Source `product_docs` from `result.role_output`. |

---

## Parse target of record

The contract binds to the **deployed specialist image** (13 days old, `nats-core` 0.4.0).
Discovery proved the load-bearing `nats-core` surfaces are byte-identical between 0.4.0
and repo tip (0.7.0): `MessageEnvelope` requires exactly `source_id` (min_length=1),
`event_type` (`EventType`), and `payload` (`dict`), with `extra="ignore"`;
`CommandPayload{command, args, correlation_id}`; `ResultPayload{command, result,
correlation_id, success}`; `Topics.Agents.COMMAND = "agents.command.{agent_id}"`;
`Topics.Agents.RESULT = "agents.result.{agent_id}"`. Any `EventType` member used must
exist in 0.4.0 (`COMMAND` and `RESULT` both do).
