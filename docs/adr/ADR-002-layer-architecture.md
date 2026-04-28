# ADR-002: Layer Architecture for Django DDD

**Status:** Accepted
**Date:** 2026-04-27
**Deciders:** Architect Agent
**Playbook Reference:** §4.2 (Layer Dependency Rules), §7 G-05

---

## Context

Django's default project structure (models → views → urls) does not enforce DDD layering. Without explicit layer boundaries, Application Services accumulate business logic (AP-03: Anemic Domain Model) and Infrastructure concerns leak into the Domain Layer (G-05 violation).

## Decision

Apply explicit DDD layering within each bounded context's Django app:

```
src/server/<context>/
  domain/          ← pure Python; zero Django/infrastructure imports
    models.py      ← Entities, Value Objects, Aggregates (dataclasses or plain classes)
    services.py    ← Domain Services (stateless)
    events.py      ← Domain Event definitions
  application/
    services.py    ← Application Services: thin orchestrators, no business logic
    commands.py    ← Command objects (DTOs into the application layer)
  infrastructure/
    repositories.py ← Django ORM implementations of Repository interfaces
    serializers.py  ← DRF serializers (infrastructure concern)
  api/             ← HTTP entry points (views, urls)
```

The existing `src/shared/` acts as a **Shared Kernel** for `CommandPayload`, `CommandResult`, `CommandType`, `CommandStatus` — shared between server CommandDispatch and client CommandExecution.

## Layer Dependency Rule

```
Infrastructure  →  Application  →  Domain  →  (nothing)
```

- `domain/` files may import only: stdlib, other `domain/` files, and `src/shared/`
- `application/` files may import: `domain/`, `src/shared/`, stdlib
- `infrastructure/` files may import: `application/`, `domain/`, Django ORM, DRF
- `api/` files may import: `application/`, `infrastructure/`, DRF

## Enforcement

- Architect Agent scans all PR diffs for infrastructure imports in `domain/` files (G-05)
- CI linter rule: `domain/` directories are forbidden from importing `django.db`, `requests`, `redis`, or any external I/O library

## Migration Path

The current codebase has Django models (`Tbl_Device`, `Tbl_Command`, `Tbl_Preset`) that serve as both Domain and Infrastructure objects. Migration plan:

1. New stories introduce pure domain classes in `domain/`
2. Existing ORM models are refactored to the `infrastructure/` layer as Repository implementations
3. No "big bang" rewrite — each story migrates only what it touches

## Consequences

**Positive:**
- Domain layer is fully testable without Django test runner (plain pytest, no DB required)
- Infrastructure can be swapped (SQLite → PostgreSQL) without touching domain logic

**Negative:**
- Two model representations per entity (domain class + ORM model) during migration
- Developers must learn the distinction; Code Reviewer enforces it per story

## Guardrails Enforced

- G-05: Domain logic in Domain Layer only
- G-07: Domain layer coverage ≥ 80%
- G-08: No mocking of domain objects in domain unit tests
- AP-03: Domain classes must have methods enforcing invariants, not just getters/setters
