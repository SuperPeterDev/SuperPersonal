"""
Orchestrator Agent — coordinates all agents, enforces phase sequence, manages loop limits.

Responsibilities (Playbook §2.2):
- Dispatch stories to agents in the correct phase sequence
- Verify test failure at end of Red phase
- Enforce MAX_RED_GREEN_LOOPS and MAX_REVIEW_CYCLES
- Log all inter-agent messages with correlation IDs
- Track cycle time per story; surface anomalies
- Fire escalation.human when loop limits are reached
"""

from __future__ import annotations

import json
import uuid
import subprocess
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

_ROOT = Path(__file__).resolve().parent.parent
_CONFIG = json.loads((_ROOT / "config" / "playbook.json").read_text())
_LOG_DIR = _ROOT / _CONFIG["paths"]["agent_log_dir"]
_BACKLOG_PATH = _ROOT / _CONFIG["paths"]["backlog"]

MAX_RED_GREEN_LOOPS: int = _CONFIG["loop_limits"]["MAX_RED_GREEN_LOOPS"]
MAX_REVIEW_CYCLES: int = _CONFIG["loop_limits"]["MAX_REVIEW_CYCLES"]


# ---------------------------------------------------------------------------
# Domain types
# ---------------------------------------------------------------------------

class StoryPhase(str, Enum):
    PENDING = "PENDING"
    IN_DOMAIN_MODELLING = "IN_DOMAIN_MODELLING"
    IN_RED_PHASE = "IN_RED_PHASE"
    IN_GREEN_PHASE = "IN_GREEN_PHASE"
    IN_REFACTOR_PHASE = "IN_REFACTOR_PHASE"
    IN_QA_PHASE = "IN_QA_PHASE"
    IN_RECONCILIATION = "IN_RECONCILIATION"
    IN_REVIEW = "IN_REVIEW"
    DONE = "DONE"
    ESCALATED = "ESCALATED"


@dataclass
class StoryState:
    story_id: str
    phase: StoryPhase = StoryPhase.PENDING
    red_green_loop_count: int = 0
    review_cycle_count: int = 0
    phase_entered_at: str = field(default_factory=lambda: _now())
    dispatch_time: str = field(default_factory=lambda: _now())
    done_time: str | None = None
    escalation_reason: str | None = None
    attempt_log: list[dict[str, Any]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Messaging
# ---------------------------------------------------------------------------

class MessageType(str, Enum):
    STORY_DISPATCHED = "story.dispatched"
    DOMAIN_MODELLED = "domain.modelled"
    STORY_CRITERIA_READY = "story.criteria_ready"
    STORY_READY_FOR_DEV = "story.ready_for_dev"
    TEST_RED_COMMITTED = "test.red.committed"
    TEST_RED_CONFIRMED = "test.red.confirmed"
    TEST_RED_REJECTED = "test.red.rejected"
    TEST_GREEN_COMMITTED = "test.green.committed"
    TEST_GREEN_CONFIRMED = "test.green.confirmed"
    REFACTOR_COMMITTED = "refactor.committed"
    QA_COMPLETED = "qa.completed"
    DOMAIN_RECONCILED = "domain.reconciled"
    REVIEW_REQUESTED = "review.requested"
    REVIEW_APPROVED = "review.approved"
    REVIEW_REJECTED = "review.rejected"
    STORY_DONE = "story.done"
    ESCALATION_HUMAN = "escalation.human"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_message(
    sender: str,
    receiver: str,
    msg_type: MessageType,
    story_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    return {
        "messageId": str(uuid.uuid4()),
        "correlationId": f"story-{story_id}",
        "sender": sender,
        "receiver": receiver,
        "type": msg_type.value,
        "payload": payload,
        "timestamp": _now(),
        "retryCount": 0,
        "expiresAt": None,
    }


def _log_message(msg: dict[str, Any]) -> None:
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = _LOG_DIR / f"{msg['correlationId']}.jsonl"
    with log_file.open("a") as f:
        f.write(json.dumps(msg) + "\n")


# ---------------------------------------------------------------------------
# Guardrail checks
# ---------------------------------------------------------------------------

def _check_red_commit_contains_no_production_code(diff: str) -> bool:
    """
    G-01: The [RED] commit diff must contain only test file additions.
    Returns True if the diff is clean (no production code changes).
    """
    import re
    production_patterns = [
        r"^\+\+\+ b/src/(?!.*/tests?).*\.py",
        r"^\+\+\+ b/agents/",
    ]
    for pattern in production_patterns:
        if re.search(pattern, diff, re.MULTILINE):
            return False
    return True


def _run_test_suite() -> dict[str, Any]:
    """Execute pytest and return structured pass/fail result."""
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--tb=short", "-q", "--no-header"],
        capture_output=True,
        text=True,
        cwd=str(_ROOT),
    )
    passed = result.returncode == 0
    return {
        "passed": passed,
        "returncode": result.returncode,
        "stdout": result.stdout[-3000:],
        "stderr": result.stderr[-1000:],
    }


# ---------------------------------------------------------------------------
# Orchestrator core
# ---------------------------------------------------------------------------

class Orchestrator:
    """
    Coordinates the multi-agent TDD+DDD workflow for a single story.
    In a full multi-agent deployment this communicates via a message bus;
    here it drives the pipeline directly for single-process execution.
    """

    AGENT_ID = "orchestrator-001"

    def __init__(self) -> None:
        self._states: dict[str, StoryState] = {}

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def dispatch_story(self, story_id: str) -> StoryState:
        state = StoryState(story_id=story_id)
        self._states[story_id] = state

        msg = _build_message(
            sender=self.AGENT_ID,
            receiver="domain-expert-001",
            msg_type=MessageType.STORY_DISPATCHED,
            story_id=story_id,
            payload={"storyId": story_id},
        )
        _log_message(msg)
        self._advance(state, StoryPhase.IN_DOMAIN_MODELLING)
        return state

    # ------------------------------------------------------------------
    # Phase transitions
    # ------------------------------------------------------------------

    def on_domain_modelled(self, story_id: str, glossary_updates: list, canvas_updates: list) -> None:
        state = self._get(story_id)
        self._log_attempt(state, "domain_modelled", {"glossary_updates": len(glossary_updates)})
        msg = _build_message(
            self.AGENT_ID, "product-owner-001",
            MessageType.DOMAIN_MODELLED, story_id,
            {"storyId": story_id, "glossaryUpdates": glossary_updates, "canvasUpdates": canvas_updates},
        )
        _log_message(msg)
        self._advance(state, StoryPhase.IN_DOMAIN_MODELLING)

    def on_criteria_ready(self, story_id: str, gherkin_criteria: list) -> None:
        state = self._get(story_id)
        self._log_attempt(state, "criteria_ready", {"criteria_count": len(gherkin_criteria)})
        msg = _build_message(
            self.AGENT_ID, "developer-001",
            MessageType.STORY_READY_FOR_DEV, story_id,
            {"storyId": story_id, "gherkinCriteria": gherkin_criteria},
        )
        _log_message(msg)
        self._advance(state, StoryPhase.IN_RED_PHASE)

    def on_red_committed(self, story_id: str, commit_hash: str, test_file_path: str) -> None:
        state = self._get(story_id)

        # G-02: confirm at least one test failure
        suite = _run_test_suite()
        if suite["passed"]:
            # Test passes immediately → story invalid
            self._log_attempt(state, "red_rejected", {"reason": "test_passed_immediately", "commit": commit_hash})
            msg = _build_message(
                self.AGENT_ID, "product-owner-001",
                MessageType.TEST_RED_REJECTED, story_id,
                {"storyId": story_id, "reason": "test.red passed — functionality already exists or story is invalid"},
            )
            _log_message(msg)
            self._advance(state, StoryPhase.IN_DOMAIN_MODELLING)
            return

        self._log_attempt(state, "red_confirmed", {"commit": commit_hash, "test_file": test_file_path})
        msg = _build_message(
            self.AGENT_ID, "developer-001",
            MessageType.TEST_RED_CONFIRMED, story_id,
            {"storyId": story_id, "testResult": "fail_confirmed"},
        )
        _log_message(msg)
        self._advance(state, StoryPhase.IN_GREEN_PHASE)

    def on_green_committed(self, story_id: str, commit_hash: str) -> None:
        state = self._get(story_id)
        state.red_green_loop_count += 1

        suite = _run_test_suite()
        if not suite["passed"]:
            self._log_attempt(state, "green_failed", {"commit": commit_hash, "loop": state.red_green_loop_count})
            if state.red_green_loop_count >= MAX_RED_GREEN_LOOPS:
                self._escalate(state, f"MAX_RED_GREEN_LOOPS ({MAX_RED_GREEN_LOOPS}) reached without green suite", suite)
                return
            # Stay in green phase for another attempt
            return

        self._log_attempt(state, "green_confirmed", {"commit": commit_hash})
        msg = _build_message(
            self.AGENT_ID, "developer-001",
            MessageType.TEST_GREEN_CONFIRMED, story_id,
            {"storyId": story_id},
        )
        _log_message(msg)
        self._advance(state, StoryPhase.IN_REFACTOR_PHASE)

    def on_refactor_committed(self, story_id: str, commit_hash: str) -> None:
        state = self._get(story_id)

        suite = _run_test_suite()
        if not suite["passed"]:
            self._log_attempt(state, "refactor_broke_suite", {"commit": commit_hash})
            # Route back to developer for fix
            self._advance(state, StoryPhase.IN_GREEN_PHASE)
            return

        self._log_attempt(state, "refactor_confirmed", {"commit": commit_hash})
        msg = _build_message(
            self.AGENT_ID, "qa-001",
            MessageType.REFACTOR_COMMITTED, story_id,
            {"storyId": story_id, "commitHash": commit_hash},
        )
        _log_message(msg)
        self._advance(state, StoryPhase.IN_QA_PHASE)

    def on_qa_completed(self, story_id: str, new_test_count: int, coverage_percent: float) -> None:
        state = self._get(story_id)
        floor = _CONFIG["coverage"]["COVERAGE_FLOOR_PERCENT"]

        if coverage_percent < floor:
            self._log_attempt(state, "qa_coverage_below_floor", {
                "coverage": coverage_percent, "floor": floor
            })
            # Blocked: stay in QA until coverage is restored
            return

        suite = _run_test_suite()
        if not suite["passed"]:
            self._log_attempt(state, "qa_introduced_failures", {"new_tests": new_test_count})
            self._advance(state, StoryPhase.IN_GREEN_PHASE)
            return

        self._log_attempt(state, "qa_passed", {"new_test_count": new_test_count, "coverage": coverage_percent})
        self._advance(state, StoryPhase.IN_RECONCILIATION)

    def on_domain_reconciled(self, story_id: str, violations: list) -> None:
        state = self._get(story_id)
        if violations:
            self._log_attempt(state, "reconciliation_violations", {"violations": violations})
            # Route back to refactor after renaming
            self._advance(state, StoryPhase.IN_REFACTOR_PHASE)
            return

        self._log_attempt(state, "domain_approved", {})
        msg = _build_message(
            self.AGENT_ID, "reviewer-001",
            MessageType.REVIEW_REQUESTED, story_id,
            {"storyId": story_id},
        )
        _log_message(msg)
        self._advance(state, StoryPhase.IN_REVIEW)

    def on_review_approved(self, story_id: str) -> None:
        state = self._get(story_id)
        self._log_attempt(state, "review_approved", {})
        state.done_time = _now()

        cycle_minutes = self._cycle_minutes(state)
        msg = _build_message(
            self.AGENT_ID, "broadcast",
            MessageType.STORY_DONE, story_id,
            {"storyId": story_id, "cycleTimeMinutes": cycle_minutes},
        )
        _log_message(msg)
        self._advance(state, StoryPhase.DONE)

    def on_review_rejected(self, story_id: str, feedback_items: list) -> None:
        state = self._get(story_id)
        state.review_cycle_count += 1
        self._log_attempt(state, "review_rejected", {"cycle": state.review_cycle_count, "items": feedback_items})

        if state.review_cycle_count >= MAX_REVIEW_CYCLES:
            self._escalate(state, f"MAX_REVIEW_CYCLES ({MAX_REVIEW_CYCLES}) reached", {"feedback": feedback_items})
            return

        # Route back to refactor for developer to address feedback
        self._advance(state, StoryPhase.IN_REFACTOR_PHASE)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get(self, story_id: str) -> StoryState:
        if story_id not in self._states:
            raise KeyError(f"Unknown story: {story_id}")
        return self._states[story_id]

    def _advance(self, state: StoryState, phase: StoryPhase) -> None:
        state.phase = phase
        state.phase_entered_at = _now()

    def _escalate(self, state: StoryState, reason: str, context: dict[str, Any]) -> None:
        state.escalation_reason = reason
        self._advance(state, StoryPhase.ESCALATED)
        msg = _build_message(
            self.AGENT_ID, "human",
            MessageType.ESCALATION_HUMAN, state.story_id,
            {
                "storyId": state.story_id,
                "reason": reason,
                "context": context,
                "blockedAt": _now(),
                "attemptLog": state.attempt_log,
            },
        )
        _log_message(msg)
        print(f"\n[ESCALATION] Story {state.story_id}: {reason}\nSee logs for full attempt log.")

    def _log_attempt(self, state: StoryState, action: str, detail: dict[str, Any]) -> None:
        state.attempt_log.append({"timestamp": _now(), "action": action, **detail})

    def _cycle_minutes(self, state: StoryState) -> float:
        start = datetime.fromisoformat(state.dispatch_time)
        end = datetime.fromisoformat(state.done_time or _now())
        return round((end - start).total_seconds() / 60, 1)

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def sprint_summary(self) -> dict[str, Any]:
        done = [s for s in self._states.values() if s.phase == StoryPhase.DONE]
        escalated = [s for s in self._states.values() if s.phase == StoryPhase.ESCALATED]
        return {
            "storiesCompleted": len(done),
            "storiesEscalated": len(escalated),
            "averageCycleTimeMinutes": (
                sum(self._cycle_minutes(s) for s in done) / len(done) if done else 0
            ),
            "escalations": [
                {"storyId": s.story_id, "reason": s.escalation_reason}
                for s in escalated
            ],
        }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="SuperPersonal Orchestrator Agent")
    sub = parser.add_subparsers(dest="command")

    dispatch = sub.add_parser("dispatch", help="Dispatch a story by ID")
    dispatch.add_argument("story_id")

    sub.add_parser("summary", help="Print sprint summary")

    args = parser.parse_args()
    orc = Orchestrator()

    if args.command == "dispatch":
        state = orc.dispatch_story(args.story_id)
        print(f"Story {args.story_id} dispatched. Phase: {state.phase.value}")
    elif args.command == "summary":
        print(json.dumps(orc.sprint_summary(), indent=2))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
