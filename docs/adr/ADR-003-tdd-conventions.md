# ADR-003: TDD Conventions and Test Organisation

**Status:** Accepted
**Date:** 2026-04-27
**Deciders:** Architect Agent, Test-First Developer Agent
**Playbook Reference:** §3 (End-to-End Workflow), §6.3 (Git Branching Convention), §7 Guardrails

---

## Context

The playbook mandates three commits per story ([RED], [GREEN], [REFACTOR]) and distinguishes domain unit tests, integration tests, and property-based tests. Without a defined test directory convention, tests accumulate in Django's default `tests.py`, making coverage analysis and QA phase extension difficult.

## Decision

### Directory Structure

```
tests/
  unit/
    domain/          ← Pure domain logic; zero infrastructure deps; plain pytest
    client/          ← Client-side executor logic; mock OS calls only
  integration/       ← Django test client; requests-mock; real DB (SQLite in CI)
  property/          ← Hypothesis-based property tests for domain invariants
```

Server-side Django tests remain in `src/server/tests/` for framework integration (conftest, Django settings). New domain unit tests go in `tests/unit/domain/`.

### Commit Naming (mandatory)

```
test: [RED] <story-id> — <one-line description>
feat: [GREEN] <story-id> — <one-line description>
refactor: [REFACTOR] <story-id> — <one-line description>
test: [QA] <story-id> — <description>
```

### Test Naming Convention

- Unit test files: `test_<aggregate_or_service>.py`
- Integration test files: `test_<flow_name>_integration.py`
- Property test files: `test_<invariant>_property.py`

### Coverage Requirements

- Domain layer (`tests/unit/domain/`) must maintain ≥ 80% coverage (G-07)
- Coverage measured via `pytest --cov=src --cov-report=json`
- CI fails if domain layer coverage drops below 80%

### Domain Unit Test Rules

- Zero imports from `django.db`, `requests`, or any I/O library
- No mocking of domain objects (G-08) — use real domain classes with in-memory state
- Infrastructure objects (repositories, HTTP clients) must be replaced with fakes (stub implementations), not mocks

### Hypothesis Property Tests

Used for invariants with many possible inputs:
- `CommandStatus` transition validity (all invalid paths must raise)
- `CommandPayload` field range enforcement (level 0–100; seconds > 0)
- `DeviceStatus` derivation from any `last_seen` timestamp

## Consequences

**Positive:**
- Domain tests run in milliseconds (no Django setup, no DB)
- Property tests catch edge cases the Developer did not enumerate

**Negative:**
- Maintaining fake repositories alongside real ORM repositories adds code surface
- Hypothesis tests can be slow on first run (database phase); set `max_examples=50` in CI

## Guardrails Enforced

- G-01: [RED] commit contains only test file changes
- G-02: [RED] test must actually fail (syntax error ≠ valid Red state)
- G-03: [REFACTOR] commit required before PR
- G-04: Full suite green at every [GREEN] and [REFACTOR] commit
- G-07: Domain layer coverage ≥ 80%
- G-08: No domain object mocking in domain unit tests
- AP-04: Domain tests must not test framework behaviour
