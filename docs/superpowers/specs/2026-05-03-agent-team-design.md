# Agentic System for Claude Code — Design Spec

**Version:** 1.0
**Date:** 2026-05-03
**Based on:** Multi-Agent TDD + DDD Development Playbook v3.0

## Overview

A global agentic system installed at `C:\Users\coopt\.claude\agents\` that extends Claude Code with 7 specialized agent roles, automatic context-based routing, full 7-phase orchestration, a communication message bus, memory architecture, and a self-evaluation harness.

Two modes: **automatic routing** (Claude detects context and adopts role) and **full orchestration** (`/orchestrator` command runs the 7-phase TDD-DDD workflow).

## Architecture

```
~/.claude/
├── CLAUDE.md                          # Auto-routing rules + agentic mode
├── settings.json                      # Hooks (none needed initially)
│
├── agents/
│   ├── roles/                         # EXECUTION PLANE
│   │   ├── domain-expert.md
│   │   ├── product-owner.md
│   │   ├── architect.md
│   │   ├── test-first-developer.md
│   │   ├── tester-qa.md
│   │   ├── code-reviewer.md
│   │   └── orchestrator.md
│   │
│   ├── comm/                          # INFRASTRUCTURE PLANE
│   │   ├── message-bus.jsonl
│   │   └── message-types.md
│   │
│   ├── memory/                        # MEMORY PLANE
│   │   ├── episodic/
│   │   ├── semantic/
│   │   └── procedural/
│   │       └── process-rules.md
│   │
│   └── harness/                       # EVALUATION PLANE
│       ├── smoke-tests.md
│       ├── standard-tests.md
│       ├── drift-thresholds.md
│       └── eval-results.jsonl
```

## Agent Roles

Seven core roles, each defined in a self-contained markdown file:

| Agent | Responsibility | Reasoning | Lane Boundaries |
|---|---|---|---|
| Domain Expert | Custodian of domain model; maintains Glossary | ToT / CoT | Cannot write code; CAN modify glossary only |
| Product Owner | Translate domain to stories with Gherkin criteria | Plan-and-Solve / ReAct | Cannot implement; CAN write stories/criteria |
| Architect | Enforce DDD patterns; bounded context placement | ToT / Debate | Cannot write production code; CAN produce ADRs |
| Test-First Developer | Execute Red-Green-Refactor cycle | ReAct / Reflection | Cannot modify glossary, approve own PR, merge to main |
| QA/Tester | Broaden coverage: integration, edge, property-based | Plan-and-Solve / Debate | Cannot write production code; CAN write test code |
| Code Reviewer | Last quality gate before merge | Reflection / Debate | Cannot write code; CAN approve or reject |
| Orchestrator | Coordinate agents, enforce process, run harness | CoT / ReAct | Cannot write code; CAN dispatch agents, merge to main |

**Conflict of interest rule:** A single session may play multiple roles but never two roles in the same story phase.

## Automatic Routing Rules

Detected from user intent and context cues in CLAUDE.md:

| Context Cue | Agent Activated |
|---|---|
| Domain concepts, glossary, bounded contexts, "what is an X?" | Domain Expert |
| Stories, acceptance criteria, Gherkin, "write a story for" | Product Owner |
| Package structure, layers, ADRs, "where should X go?" | Architect |
| Writing tests or implementing features | Test-First Developer |
| Integration/edge/property tests, "test the edge cases" | QA/Tester |
| Code review, PR feedback, "review this diff" | Code Reviewer |
| Full workflow, "/orchestrator <story>", phase validation | Orchestrator |

When ambiguous, Claude asks one clarifying question.

## Orchestration — 7-Phase Workflow

```
Phase 1: Domain Modelling    → Domain Expert + Product Owner + Architect
Phase 2: RED                 → Developer writes failing test, commits [RED]
Phase 3: GREEN               → Developer writes minimal impl, commits [GREEN]
Phase 4: REFACTOR            → Developer improves structure, commits [REFACTOR]
Phase 5: QA                  → QA writes integration + edge tests
Phase 6: Reconciliation      → Domain Expert checks language compliance
Phase 7: Review + Merge      → Code Reviewer approves + Orchestrator merges
```

**Loop limits:** MAX_RED_GREEN_LOOPS=3, MAX_REVIEW_CYCLES=2. Exceeding triggers human escalation.

Each phase dispatch uses the `Agent` tool with the role prompt + story context. The Orchestrator validates phase output before advancing.

## Communication Bus

Append-only JSONL at `agents/comm/message-bus.jsonl`. Standard envelope:

```json
{"messageId":"uuid","correlationId":"story-<id>","sender":"agent-id","receiver":"agent-id","type":"event-type","payload":{},"reasoning_trace_ref":null,"timestamp":"ISO8601","retryCount":0,"expiresAt":null}
```

27 message types from the playbook. Grep by correlationId to replay a story.

## Memory Architecture

| Type | Location | Lifetime | Owner |
|---|---|---|---|
| Working | Sub-agent context | Single task | Active agent |
| Episodic | `memory/episodic/story-<id>.md` | Sealed at story DONE | Orchestrator |
| Semantic | Existing memory system + `memory/semantic/` | Project lifetime | Domain Expert (Glossary), Architect (ADRs) |
| Procedural | `memory/procedural/` | Project lifetime | Orchestrator |

## Harness & Evaluation

- **Smoke tests:** Each agent must produce valid output on trivial tasks. 100% pass required. Run on agent registration.
- **Standard tests:** Correct output on representative stories. 95% target. Run weekly.
- **Drift detector:** Compares current metrics to baseline after every story. Alerts on breach.

## Build Plan — 4 Phases

### P1 — Agent Roles + Orchestration
- 7 role definition files in `agents/roles/`
- Orchestrator role with dispatch logic for all 7 phases
- CLAUDE.md updated with routing rules and agentic mode section
- End state: automatic routing active; `/orchestrator` functional

### P2 — Communication Bus
- `agents/comm/message-bus.jsonl` created
- `agents/comm/message-types.md` with 27-type registry
- Orchestrator writes dispatch events; sub-agents write completion events
- End state: all agent interactions logged and replayable

### P3 — Memory Architecture
- Episodic memory per story
- Semantic memory (Glossary, ADRs) structure
- Procedural memory for process rules
- End state: agents have continuity across sessions

### P4 — Harness
- Smoke test definitions per role
- Standard test scenarios
- Drift threshold configuration
- End state: system self-evaluates and alerts on regression

## Integration with Existing Setup

- Extends existing CLAUDE.md (adds `## Agentic Mode` section, does not replace)
- Extends existing memory system (adds episodic/procedural directories, does not replace)
- No new dependencies — uses Claude Code's native Skill and Agent tools
- No settings.json hooks required initially
- Compatible with all existing skills and MCP servers
