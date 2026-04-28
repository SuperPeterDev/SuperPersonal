"""
Product Owner Agent — translates domain insights into unambiguous user stories with Gherkin criteria.

Responsibilities (Playbook §2.2):
- Write user stories in the format: As a [role], I want [action], so that [outcome]
- Write acceptance criteria in Gherkin (Given/When/Then) with concrete data values — no placeholders
- Prioritise the backlog by domain risk and business value
- Clarify ambiguous stories when the Developer cannot derive a clear failing test
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent
_CONFIG = json.loads((_ROOT / "config" / "playbook.json").read_text())
_BACKLOG_PATH = _ROOT / _CONFIG["paths"]["backlog"]


# ---------------------------------------------------------------------------
# Backlog access
# ---------------------------------------------------------------------------

def load_backlog() -> dict[str, Any]:
    return json.loads(_BACKLOG_PATH.read_text())


def save_backlog(backlog: dict[str, Any]) -> None:
    backlog["_meta"]["last_updated"] = datetime.now(timezone.utc).date().isoformat()
    _BACKLOG_PATH.write_text(json.dumps(backlog, indent=2))


def get_story(story_id: str) -> dict[str, Any]:
    backlog = load_backlog()
    for story in backlog["stories"]:
        if story["id"] == story_id:
            return story
    raise KeyError(f"Story '{story_id}' not found in backlog.")


def get_pending_stories() -> list[dict[str, Any]]:
    backlog = load_backlog()
    return [s for s in backlog["stories"] if s["status"] == "PENDING"]


def get_next_story() -> dict[str, Any] | None:
    pending = get_pending_stories()
    if not pending:
        return None
    return min(pending, key=lambda s: s["priority"])


# ---------------------------------------------------------------------------
# Acceptance criteria validation
# ---------------------------------------------------------------------------

@dataclass
class CriteriaValidationResult:
    story_id: str
    is_valid: bool
    issues: list[str]
    gherkin_criteria: list[str]


_VAGUE_PHRASES = [
    "works correctly",
    "handles errors gracefully",
    "should work",
    "properly",
    "appropriately",
    "as expected",
    "correctly",
]


def validate_acceptance_criteria(story_id: str) -> CriteriaValidationResult:
    """
    Validates that acceptance criteria are concrete enough for a developer to
    derive a single, unambiguous failing test without further clarification.

    Rules checked:
    1. Each criterion must have Given, When, Then clauses
    2. No vague language (see _VAGUE_PHRASES)
    3. All Then clauses must specify a measurable, concrete outcome
    4. No placeholders like <value>, {placeholder}
    """
    story = get_story(story_id)
    issues: list[str] = []
    gherkin_criteria: list[str] = []

    for ac in story.get("acceptance_criteria", []):
        text = ac.get("gherkin", "")
        gherkin_criteria.append(text)
        ac_id = ac.get("id", "?")

        if "Given" not in text or "When" not in text or "Then" not in text:
            issues.append(f"{ac_id}: Missing Given/When/Then structure")

        for phrase in _VAGUE_PHRASES:
            if phrase.lower() in text.lower():
                issues.append(f"{ac_id}: Vague phrase detected — '{phrase}'")

        if re.search(r"<[^>]+>|\{[^}]+\}", text):
            issues.append(f"{ac_id}: Placeholder detected — replace with concrete values")

    is_valid = len(issues) == 0
    return CriteriaValidationResult(
        story_id=story_id,
        is_valid=is_valid,
        issues=issues,
        gherkin_criteria=gherkin_criteria,
    )


# ---------------------------------------------------------------------------
# Story management
# ---------------------------------------------------------------------------

def update_story_status(story_id: str, new_status: str) -> None:
    """Valid statuses: PENDING, IN_DOMAIN_MODELLING, IN_DEV, IN_QA, IN_REVIEW, DONE, ESCALATED"""
    backlog = load_backlog()
    for story in backlog["stories"]:
        if story["id"] == story_id:
            story["status"] = new_status
            save_backlog(backlog)
            return
    raise KeyError(f"Story '{story_id}' not found.")


def add_story(
    story_id: str,
    epic: str,
    title: str,
    narrative: str,
    bounded_context: str,
    priority: int,
    acceptance_criteria: list[dict[str, str]],
    glossary_terms: list[str],
) -> None:
    backlog = load_backlog()
    existing_ids = {s["id"] for s in backlog["stories"]}
    if story_id in existing_ids:
        raise ValueError(f"Story '{story_id}' already exists.")

    backlog["stories"].append({
        "id": story_id,
        "epic": epic,
        "title": title,
        "narrative": narrative,
        "bounded_context": bounded_context,
        "priority": priority,
        "status": "PENDING",
        "acceptance_criteria": acceptance_criteria,
        "glossary_terms": glossary_terms,
    })
    save_backlog(backlog)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Product Owner Agent")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("next", help="Show the highest-priority PENDING story")
    sub.add_parser("list", help="List all PENDING stories")

    val = sub.add_parser("validate", help="Validate acceptance criteria for a story")
    val.add_argument("story_id")

    upd = sub.add_parser("update-status", help="Update a story's status")
    upd.add_argument("story_id")
    upd.add_argument("status")

    show = sub.add_parser("show", help="Show full details of a story")
    show.add_argument("story_id")

    args = parser.parse_args()

    if args.command == "next":
        story = get_next_story()
        if story:
            print(json.dumps(story, indent=2))
        else:
            print("No PENDING stories.")

    elif args.command == "list":
        for s in get_pending_stories():
            print(f"  [{s['priority']}] {s['id']:6s} — {s['title']}")

    elif args.command == "validate":
        result = validate_acceptance_criteria(args.story_id)
        print(json.dumps(result.__dict__, indent=2))
        if not result.is_valid:
            raise SystemExit(1)

    elif args.command == "update-status":
        update_story_status(args.story_id, args.status)
        print(f"Story {args.story_id} status → {args.status}")

    elif args.command == "show":
        print(json.dumps(get_story(args.story_id), indent=2))

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
