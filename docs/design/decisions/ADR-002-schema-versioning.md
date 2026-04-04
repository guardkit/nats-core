# ADR-002: Schema Versioning Strategy

**Date:** February 2026
**Status:** Accepted (inherited from Dev Pipeline System Spec XC-schema-versioning)

## Context

nats-core defines the message schemas used by every agent and adapter in the fleet.
Schema changes must be coordinated — a breaking change in an envelope field can break
every consumer simultaneously.

## Decision

1. MessageEnvelope includes a `version` field (currently "1.0")
2. nats-core package versioned with semver
3. Breaking schema changes bump major version
4. Consumers MUST tolerate unknown fields (`model_config = ConfigDict(extra="ignore")`)
5. New fields MUST be optional with defaults
6. Never remove or rename a published field without major version bump
7. Topic structure changes are breaking and require coordinated rollout

## Consequences

- Forward compatibility: old consumers work with new messages (unknown fields ignored)
- Backward compatibility: new consumers work with old messages (new fields have defaults)
- Major version bumps require coordinated fleet upgrade
- The `version` field allows routing to appropriate deserialisers in future
