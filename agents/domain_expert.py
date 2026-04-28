"""
Domain Expert Agent — custodian of the Ubiquitous Language Glossary and Domain Model Canvas.

Responsibilities (Playbook §2.2):
- Validate that all terms used in a story exist in the Glossary
- Add new terms before development starts on a story
- Reconcile production code identifiers against the Glossary after Refactor phase (Phase 6)
- Update the Domain Model Canvas when implementation reveals new domain understanding
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
_GLOSSARY_PATH = _ROOT / _CONFIG["paths"]["glossary"]


# ---------------------------------------------------------------------------
# Glossary access
# ---------------------------------------------------------------------------

def load_glossary() -> dict[str, Any]:
    return json.loads(_GLOSSARY_PATH.read_text())


def save_glossary(glossary: dict[str, Any]) -> None:
    glossary["_meta"]["last_updated"] = datetime.now(timezone.utc).date().isoformat()
    _GLOSSARY_PATH.write_text(json.dumps(glossary, indent=2))


def get_all_terms(glossary: dict[str, Any]) -> set[str]:
    terms = set()
    for entry in glossary["terms"]:
        terms.add(entry["term"].lower())
        for syn in entry.get("synonyms", []):
            terms.add(syn.lower())
    return terms


# ---------------------------------------------------------------------------
# Story validation (Phase 1)
# ---------------------------------------------------------------------------

@dataclass
class DomainModellingResult:
    story_id: str
    all_terms_found: bool
    missing_terms: list[str]
    glossary_updates: list[str]
    canvas_updates: list[str]
    notes: str


def validate_story_terms(story_id: str, story_text: str, gherkin: list[str]) -> DomainModellingResult:
    """
    Phase 1: Check that every domain term referenced in the story and acceptance criteria
    exists in the Glossary. Returns a list of missing terms that must be added before
    development begins.
    """
    glossary = load_glossary()
    known_terms = get_all_terms(glossary)

    # Extract candidate terms: capitalised words or snake_case identifiers
    combined_text = story_text + " " + " ".join(gherkin)
    candidates = set(re.findall(r"\b[A-Z][a-zA-Z]+\b", combined_text))
    candidates |= set(re.findall(r"\b[a-z]+_[a-z_]+\b", combined_text))

    # Filter to domain-looking terms (exclude common English words)
    skip = {"Given", "When", "Then", "And", "The", "A", "An", "I", "It", "In", "Is",
            "To", "For", "Of", "On", "At", "By", "If", "Or", "Not", "Be", "As", "So",
            "That", "This", "My", "All", "Any", "Each", "No", "Can", "Do", "Has", "Have"}
    candidates -= skip

    missing = [t for t in sorted(candidates) if t.lower() not in known_terms]

    return DomainModellingResult(
        story_id=story_id,
        all_terms_found=len(missing) == 0,
        missing_terms=missing,
        glossary_updates=[],
        canvas_updates=[],
        notes=f"Checked {len(candidates)} candidate terms; {len(missing)} missing from Glossary.",
    )


# ---------------------------------------------------------------------------
# Glossary mutation
# ---------------------------------------------------------------------------

def add_term(
    term: str,
    definition: str,
    bounded_context: str,
    term_type: str,
    story_id: str,
    synonyms: list[str] | None = None,
) -> None:
    """Add a new term to the Glossary. Raises ValueError if term already exists."""
    glossary = load_glossary()
    existing = {e["term"].lower() for e in glossary["terms"]}
    if term.lower() in existing:
        raise ValueError(f"Term '{term}' already exists in Glossary.")

    entry = {
        "term": term,
        "definition": definition,
        "synonyms": synonyms or [],
        "not_to_be_confused_with": [],
        "bounded_context": bounded_context,
        "type": term_type,
        "examples": [],
        "added_in_story": story_id,
        "last_updated": datetime.now(timezone.utc).date().isoformat(),
    }
    glossary["terms"].append(entry)
    save_glossary(glossary)


# ---------------------------------------------------------------------------
# Domain reconciliation (Phase 6)
# ---------------------------------------------------------------------------

@dataclass
class ReconciliationResult:
    story_id: str
    violations: list[dict[str, str]]
    approved: bool


def reconcile_diff(story_id: str, diff_text: str) -> ReconciliationResult:
    """
    Phase 6: Scan a git diff for Python identifiers (class names, method names,
    variable names) that do not exist in the Glossary.

    Returns a ReconciliationResult with a list of violations. Each violation
    contains the offending identifier and the file/line context.

    Only additions (+lines) are scanned. Removed lines are ignored.
    """
    glossary = load_glossary()
    known_terms = get_all_terms(glossary)

    violations: list[dict[str, str]] = []
    current_file = ""

    for raw_line in diff_text.splitlines():
        if raw_line.startswith("+++ b/"):
            current_file = raw_line[6:]
            continue
        if not raw_line.startswith("+"):
            continue
        line = raw_line[1:]

        # Extract class and function definitions
        class_match = re.search(r"class\s+([A-Z][a-zA-Z0-9]+)", line)
        func_match = re.search(r"def\s+([a-z][a-z0-9_]+)", line)

        for match in filter(None, [class_match, func_match]):
            identifier = match.group(1)
            # Strip common suffixes that aren't domain terms
            stripped = re.sub(r"(Test|Serializer|View|Factory|Fake|Stub|Repository|Service)$", "", identifier)
            if stripped and stripped.lower() not in known_terms and len(stripped) > 3:
                violations.append({
                    "file": current_file,
                    "identifier": identifier,
                    "suggestion": "Add to Glossary or rename to a Glossary-approved term",
                })

    return ReconciliationResult(
        story_id=story_id,
        violations=violations,
        approved=len(violations) == 0,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Domain Expert Agent")
    sub = parser.add_subparsers(dest="command")

    val = sub.add_parser("validate", help="Validate story terms against Glossary")
    val.add_argument("story_id")
    val.add_argument("story_text")

    add = sub.add_parser("add-term", help="Add a new term to the Glossary")
    add.add_argument("term")
    add.add_argument("definition")
    add.add_argument("bounded_context")
    add.add_argument("type")
    add.add_argument("story_id")

    recon = sub.add_parser("reconcile", help="Reconcile a git diff against the Glossary")
    recon.add_argument("story_id")
    recon.add_argument("diff_file", help="Path to a file containing the git diff")

    sub.add_parser("list-terms", help="Print all Glossary terms")

    args = parser.parse_args()

    if args.command == "validate":
        result = validate_story_terms(args.story_id, args.story_text, [])
        print(json.dumps(result.__dict__, indent=2))

    elif args.command == "add-term":
        add_term(args.term, args.definition, args.bounded_context, args.type, args.story_id)
        print(f"Term '{args.term}' added to Glossary.")

    elif args.command == "reconcile":
        diff_text = Path(args.diff_file).read_text()
        result = reconcile_diff(args.story_id, diff_text)
        print(json.dumps(result.__dict__, indent=2))

    elif args.command == "list-terms":
        glossary = load_glossary()
        for entry in glossary["terms"]:
            print(f"  {entry['term']:30s} [{entry['type']:15s}] ({entry['bounded_context']})")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
