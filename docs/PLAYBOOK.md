# Multi-Agent TDD + DDD Playbook — SuperPersonal Project

**Version:** 2.0  
**Status:** Active  
**Last Updated:** 2026-04-27  
**Reference:** See root directory [`PLAYBOOK.md`](../PLAYBOOK.md) for the authoritative playbook specification.

---

## Artifacts in This Directory

This directory contains all living documents that form the persistent state of the multi-agent TDD+DDD system.

### Core Artifacts

| File | Owner | Purpose |
|---|---|---|
| **glossary.json** | Domain Expert Agent | Ubiquitous Language Glossary — the canonical authority for all domain terms used in production code. Updated whenever a new domain concept is discovered. |
| **domain_model.yaml** | Domain Expert + Architect | Domain Model Canvas — defines bounded contexts, aggregates, entities, value objects, domain events, and integration patterns. |
| **backlog.json** | Product Owner Agent | User Story Backlog — all stories with acceptance criteria in Gherkin format, prioritised by business/domain value. |
| **adr/** | Architect Agent | Architecture Decision Records — all structural decisions affecting layers, bounded contexts, or patterns. Immutable once written. |
| **retrospectives/** | Orchestrator Agent | Sprint retrospective summaries — metrics, escalations, process improvements, guardrail calibrations. One file per sprint. |

### Why These Matter

1. **Glossary** — The single source of truth for domain language. All production code identifiers must derive from this glossary. Violations (G-06) block code review.

2. **Domain Model Canvas** — Defines the boundaries and relationships between bounded contexts. New stories are assigned to a context in Phase 1; the canvas guides the Architect's package skeleton design.

3. **Backlog** — Drives the entire workflow. Stories are prioritised, tagged with Gherkin acceptance criteria, and marked with required glossary terms. A story may not enter development until its acceptance criteria are unambiguous.

4. **ADRs** — Document every architectural decision that affects multiple stories or contexts. Used by Code Reviewer to reference guardrails. Consulted by Architect when reviewing new structures.

5. **Retrospectives** — Accountability and continuous improvement. Each sprint is measured against defined metrics (cycle time, escalation rate, coverage). Guardrail parameters are tuned based on sprint data, not intuition.

---

## Quick Start: Using the Playbook on This Project

### 1. Read These First

1. **PLAYBOOK.md** (root) — The full 16-section playbook describing all roles, phases, guardrails, and communication protocols.
2. **glossary.json** — Understand the domain: Device, Command, CommandStatus, CommandExecutor, Preset, etc.
3. **domain_model.yaml** — Visualise the five bounded contexts: DeviceManagement, CommandDispatch, CommandExecution, PresetManagement, Monitoring.
4. **adr/ADR-001**, **ADR-002**, **ADR-003** — Understand the structural decisions that guide all code changes.

### 2. Pick a Story

```bash
python agents/product_owner.py next
```

This shows the highest-priority PENDING story from the backlog. Example output:

```
US-2: Take a screenshot of a device
```

### 3. Validate Its Acceptance Criteria

```bash
python agents/product_owner.py validate US-2
```

If the validation fails (vague language, missing Given/When/Then), the story returns to the Product Owner for refinement.

### 4. Start Phase 1: Domain Modelling

**Participants:** Domain Expert, Product Owner, Architect

- Read the story narrative and acceptance criteria.
- Domain Expert checks that all terms in the story exist in **glossary.json**. Missing terms → add them via:
  ```bash
  python agents/domain_expert.py add-term "TermName" "Definition" "BoundedContext" "Entity|ValueObject|Aggregate|DomainService" "US-2"
  ```
- Product Owner confirms acceptance criteria are concrete (no placeholders).
- Architect assigns the story to a bounded context and checks whether new packages are needed.

### 5. Start Phase 2: RED (Failing Test)

**Participant:** Developer

- Create a feature branch:
  ```bash
  git checkout -b feature/US-2
  ```
- Print the RED phase checklist:
  ```bash
  python agents/developer.py checklist US-2
  ```
- Write a single failing test that will pass only when the acceptance criterion is satisfied. Use Glossary terms as identifiers.
- Commit:
  ```bash
  git commit -m "test: [RED] US-2 — take screenshot from device detail page"
  ```
- Verify the test actually fails:
  ```bash
  python agents/developer.py report US-2 red
  ```

### 6. Phase 3: GREEN (Minimal Implementation)

- Write the minimal production code to make the failing test pass. No extra features.
- Commit:
  ```bash
  git commit -m "feat: [GREEN] US-2 — implement screenshot command executor"
  ```
- Run full suite:
  ```bash
  python agents/developer.py run-tests
  ```

If tests don't pass after **MAX_RED_GREEN_LOOPS** (default 3) attempts, the Orchestrator escalates to human.

### 7. Phase 4: REFACTOR (Structure & Naming)

- Improve the code: extract methods, rename variables to Glossary terms, remove duplication.
- Run tests after every significant change.
- Commit:
  ```bash
  git commit -m "refactor: [REFACTOR] US-2 — extract screenshot logic to domain service"
  ```

### 8. Phase 5: QA (Integration & Edge Cases)

**Participant:** QA Agent

- Print QA checklist:
  ```bash
  python agents/qa.py checklist US-2
  ```
- Write integration tests crossing module boundaries.
- Write property tests for domain invariants.
- Run coverage:
  ```bash
  python agents/qa.py coverage
  ```

If domain layer coverage drops below **COVERAGE_FLOOR_PERCENT** (default 80%), the story is blocked.

### 9. Phase 6: Domain Reconciliation

**Participant:** Domain Expert

- Reconcile the production code diff against the Glossary:
  ```bash
  git diff main HEAD > /tmp/diff.txt
  python agents/domain_expert.py reconcile US-2 /tmp/diff.txt
  ```

Any language violations → Developer renames and refactors.

### 10. Phase 7: Code Review & Merge

**Participant:** Code Reviewer

- Request review:
  ```bash
  python agents/reviewer.py review US-2 feature/US-2
  ```

The reviewer checks:
- ✓ All three commits ([RED], [GREEN], [REFACTOR]) exist
- ✓ No layer violations (G-05)
- ✓ All identifiers in Glossary (G-06)
- ✓ Coverage above floor (G-07)
- ✓ Refactor didn't add new tests (AP-06)

If approved, merge to main:

```bash
git checkout main
git merge feature/US-2
```

---

## Enforced Guardrails

| # | Rule | Enforced By | Violation = Blocked |
|---|---|---|---|
| G-01 | No production code before [RED] commit | Orchestrator (git history check) | PR halted |
| G-02 | [RED] test must actually fail | Orchestrator (test runner) | Story bounced to Phase 1 |
| G-03 | [REFACTOR] commit required | Code Reviewer (commit history) | Code Review blocked |
| G-04 | Full suite green at [GREEN] and [REFACTOR] | Orchestrator (CI) | Commit flagged |
| G-05 | Domain logic in Domain Layer only | Architect (diff scan) | PR rejected |
| G-06 | All identifiers in Ubiquitous Language Glossary | Code Reviewer (diff scan) | PR rejected |
| G-07 | Domain layer coverage ≥ 80% | Orchestrator (coverage report) | Story blocked |
| G-08 | No mocking domain objects in domain tests | Code Reviewer (visual inspection) | Test must be rewritten |
| G-09 | No story stuck in phase > sprint duration | Orchestrator (metrics) | Story escalated |
| G-10 | No unreachable code in [GREEN] | Code Reviewer (diff analysis) | PR rejected |

---

## Anti-Patterns We Actively Prevent

| Code | Pattern | What It Looks Like | Prevention |
|---|---|---|---|
| AP-01 | "Test Last" disguised as "Test First" | [RED] commit has production code files | G-01 enforced |
| AP-02 | God Aggregate | Single Aggregate Root with 20+ methods from multiple subdomains | Architect reviews bounded context assignment |
| AP-03 | Anemic Domain Model | Domain classes with only getters/setters | Code Reviewer requires ≥1 method enforcing invariants per Aggregate/Entity |
| AP-04 | Test That Tests the Framework | Tests verify SQLAlchemy insert, not domain rules | Domain unit tests isolated from infrastructure |
| AP-05 | Glossary Drift | Code uses different terms than Glossary; Glossary is "updated" to match | G-06: code is corrected, not Glossary |
| AP-06 | Refactoring That Adds Features | [REFACTOR] commit has new test files | Code Reviewer rejects |
| AP-07 | Shared Database Between Contexts | Two contexts read/write same tables | Integration via Published Language events only |
| AP-08 | Oversized Stories | One story spans multiple aggregates/contexts | Product Owner splits during Phase 1 |

---

## Metrics & Health

Each sprint is measured:

- **Cycle Time per Story** — from dispatch to done. Target ≤ 8h; alert if > 24h.
- **Red-Green Loop Count** — attempts to green. Target 1; alert if ≥ 3.
- **Review Rejection Rate** — rejections / total reviews. Target < 20%; alert if > 40%.
- **Language Violation Rate** — violations found in Phase 6 / stories done. Target 0%; alert if > 10%.
- **Domain Layer Coverage** — target ≥ 80%; alert if < 70%.
- **Escalation Rate** — human escalations / stories done. Target < 5%; alert if > 15%.
- **Glossary Growth** — new terms per sprint. Target > 0 (stagnation is a signal).

See `config/playbook.json` for thresholds; calibrate after first two sprints based on your team's velocity.

---

## Process Parameters (Tunable)

Edit `config/playbook.json`:

```json
{
  "loop_limits": {
    "MAX_RED_GREEN_LOOPS": 3,
    "MAX_REVIEW_CYCLES": 2
  },
  "coverage": {
    "COVERAGE_FLOOR_PERCENT": 80
  }
}
```

These are defaults. Adjust based on team context and sprint retrospectives.

---

## For Human Project Lead / Scrum Master

### Orchestrator Role (Automated)

The Orchestrator Agent (`agents/orchestrator.py`) automates:
- Story dispatch and phase sequencing
- Loop limit enforcement (escalation.human fired at limits)
- Cycle time tracking
- Sprint metrics collection

Run manually:

```bash
python agents/orchestrator.py dispatch US-2        # Dispatch a story
python agents/orchestrator.py summary               # Print sprint summary
```

### Escalations

When a story reaches **MAX_RED_GREEN_LOOPS** or **MAX_REVIEW_CYCLES**, the Orchestrator logs an `escalation.human` message to `logs/agent/story-{id}.jsonl`. Review the attempt log and decide:

- **Too large?** Split the story.
- **Acceptance criteria ambiguous?** Return to Product Owner.
- **Architectural blocker?** Engage Architect.
- **Design disagreement?** Make a binding call; update relevant ADR.

### Sprint Retrospective

At the end of each sprint:

```bash
python agents/orchestrator.py summary > /tmp/sprint_summary.json
```

Review:
- Cycle time trend
- Escalation count and reasons
- Glossary growth (zero = domain exploration stagnation)
- Coverage trend

Produce `docs/retrospectives/sprint-{N}.md` with findings, action items, and guardrail adjustments for the next sprint.

---

## Diagram: Phase Sequence

```
Story enters backlog
        ↓
    [Phase 1: Domain Modelling]
        Domain Expert validates terms
        Product Owner writes Gherkin
        Architect assigns context
        ↓
    [Phase 2: RED]
        Developer writes failing test
        Orchestrator confirms failure
        ↓
    [Phase 3: GREEN]
        Developer writes minimal code
        Orchestrator confirms all tests green
        (Loop back if not green; escalate if > MAX_RED_GREEN_LOOPS)
        ↓
    [Phase 4: REFACTOR]
        Developer improves structure/naming
        Orchestrator confirms tests still green
        ↓
    [Phase 5: QA]
        QA writes integration/edge/property tests
        Orchestrator confirms coverage ≥ floor
        ↓
    [Phase 6: Domain Reconciliation]
        Domain Expert reconciles diff vs Glossary
        (If violations, back to Refactor)
        ↓
    [Phase 7: Code Review]
        Code Reviewer validates all guardrails
        (If rejected, back to Refactor; if > MAX_REVIEW_CYCLES, escalate)
        ↓
    [Merge & Done]
        Orchestrator records final metrics
        Story marked DONE
```

---

## Next Steps

1. **Assign the first story** — Pick US-1 or US-2 from the backlog.
2. **Walk through Phase 1** — Validate that domain terms are in the Glossary.
3. **Assign developers** — Dispatch to the Developer Agent for Red-Green-Refactor.
4. **Monitor escalations** — Review `logs/agent/*.jsonl` for any loop-limit breaches.
5. **Run first retrospective** — After 3-5 stories, collect metrics and calibrate guardrails.

---

**Questions?** Refer to the root `PLAYBOOK.md` or ask the Architect or Orchestrator agents for clarification on any phase or guardrail.
