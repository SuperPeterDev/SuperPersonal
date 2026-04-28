# ADR-001: Bounded Context Definitions

**Status:** Accepted
**Date:** 2026-04-27
**Deciders:** Architect Agent, Domain Expert Agent
**Playbook Reference:** §4 (DDD Tactical Pattern Reference), §3 Phase 1

---

## Context

SuperPersonal consists of a Django web server, a Python client agent running on the target PC, and shared domain concepts (Command, CommandPayload). Without explicit bounded context boundaries, domain concepts leak between subsystems, producing the God Aggregate anti-pattern (AP-02) and Shared Database anti-pattern (AP-07).

## Decision

Five bounded contexts are defined. Each owns its own data models and repositories. No cross-context direct database access is permitted.

| Context | Responsibility | Primary Aggregate |
|---|---|---|
| **DeviceManagement** | Device registration, identity, online/offline status | `Device` |
| **CommandDispatch** | Command lifecycle: issuance → dispatch → completion | `Command` |
| **CommandExecution** | Client-side execution routing and OS-level action | Domain Services only (no aggregate) |
| **PresetManagement** | User-defined URL shortcuts | `Preset` |
| **Monitoring** | Real-time hardware metrics, smart suggestions | Domain Services only (no aggregate) |

## Integration Patterns Selected

| From | To | Pattern | Rationale |
|---|---|---|---|
| DeviceManagement | CommandDispatch | Published Language (domain events) | DeviceRegistered event carries DeviceID without tight coupling |
| CommandDispatch | CommandExecution (client) | Published Language (polling / WebSocket) | Client polls `/commands/pending` or receives WebSocket push; ACL translates JSON to domain objects |
| CommandDispatch | PresetManagement | Customer/Supplier | CommandDispatch (downstream) requests Preset URL when resolving CMD_OPEN_PRESET |
| Monitoring | CommandDispatch | Published Language | ThresholdExceeded event may trigger automated command issuance |

## Consequences

**Positive:**
- Each context can evolve independently; Django app modules map 1:1 to contexts (`api/`, `ws/`, `core/`)
- Client-side code (CommandExecution) has zero Django ORM imports — fully portable

**Negative:**
- Integration via events adds latency vs. direct DB join
- The shared `src/shared/schemas.py` is a Shared Kernel; changes require coordinated update across both contexts

## Guardrails Enforced

- G-05: Domain logic stays in the Domain Layer of its bounded context
- G-06: All identifiers derive from the Ubiquitous Language Glossary
- AP-07: No cross-context table reads — integration via Published Language events only
