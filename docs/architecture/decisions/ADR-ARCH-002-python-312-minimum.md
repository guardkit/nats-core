# ADR-ARCH-002: Python 3.12+ Minimum Version

**Date:** 2026-04-07
**Status:** Accepted

## Status

Accepted

## Context

The project template defaults to Python >=3.10, but all agents and services in the
Ship's Computer fleet target Python 3.12+. Supporting older Python versions adds
testing matrix complexity without benefiting any consumer.

## Decision

Set the minimum Python version to **>=3.12**, matching the fleet minimum.

## Alternatives Considered

| Alternative | Why Rejected |
|-------------|-------------|
| Python >=3.10 | No fleet consumer uses 3.10/3.11 -- unnecessary compat burden |
| Python >=3.13 | Too aggressive -- 3.13 is recent and may not be available in all CI/container images |

## Consequences

- Can use 3.12+ features: improved error messages, `type` statement, performance improvements
- Simpler CI matrix (single Python version)
- Must update if any fleet consumer needs an older Python version (unlikely)
