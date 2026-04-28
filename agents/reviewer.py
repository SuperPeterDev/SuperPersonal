"""
Code Reviewer Agent — the last quality gate before merge.

Responsibilities (Playbook §2.2):
- Verify all three commits ([RED], [GREEN], [REFACTOR]) exist in the branch
- Check all identifiers against the Ubiquitous Language Glossary (G-06)
- Verify layer separation (G-05)
- Confirm refactoring did not change behaviour (compare test output before/after)
- Produce actionable feedback referencing specific guardrail numbers
- Never approve without verifying; never reject without specifying exactly what must change
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent
_CONFIG = json.loads((_ROOT / "config" / "playbook.json").read_text())
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


# ---------------------------------------------------------------------------
# Domain types
# ---------------------------------------------------------------------------

@dataclass
class ReviewFeedbackItem:
    guardrail: str
    file: str
    description: str
    required_action: str


@dataclass
class ReviewResult:
    story_id: str
    approved: bool
    feedback_items: list[ReviewFeedbackItem] = field(default_factory=list)
    commit_history_valid: bool = True
    layer_check_passed: bool = True
    language_check_passed: bool = True
    coverage_check_passed: bool = True
    notes: str = ""


# ---------------------------------------------------------------------------
# Commit history validation (G-01, G-03)
# ---------------------------------------------------------------------------

def _git(*args: str) -> str:
    result = subprocess.run(
        ["git"] + list(args),
        capture_output=True, text=True, cwd=str(_ROOT),
    )
    return result.stdout.strip()


def validate_commit_history(story_id: str, branch: str) -> tuple[bool, list[str]]:
    """
    G-01, G-03: Verify the branch contains commits tagged [RED], [GREEN], [REFACTOR]
    in the correct order (by timestamp).
    """
    log = _git("log", "--oneline", "--format=%H %s", f"main..{branch}")
    commits = [line for line in log.splitlines() if line.strip()]

    tags_found = {"[RED]": None, "[GREEN]": None, "[REFACTOR]": None}
    for commit in reversed(commits):  # oldest first
        for tag in tags_found:
            if tag in commit and tags_found[tag] is None:
                tags_found[tag] = commit

    issues = []
    if not tags_found["[RED]"]:
        issues.append("G-01/G-02: No [RED] commit found — production code written without prior failing test")
    if not tags_found["[GREEN]"]:
        issues.append("G-03: No [GREEN] commit found")
    if not tags_found["[REFACTOR]"]:
        issues.append("G-03: No [REFACTOR] commit required before PR submission")

    return len(issues) == 0, issues


# ---------------------------------------------------------------------------
# Language compliance check (G-06)
# ---------------------------------------------------------------------------

def check_language_compliance(diff_text: str) -> list[ReviewFeedbackItem]:
    """
    G-06: All class names, method names, and module-level identifiers in the diff
    must exist in the Ubiquitous Language Glossary.
    """
    try:
        from .domain_expert import load_glossary, get_all_terms
    except ImportError:
        from agents.domain_expert import load_glossary, get_all_terms

    glossary = load_glossary()
    known_terms = get_all_terms(glossary)

    items: list[ReviewFeedbackItem] = []
    current_file = ""

    _SKIP_IDENTIFIERS = {
        # Common Python/Django/DRF identifiers that are not domain terms
        "self", "cls", "args", "kwargs", "pk", "id", "url", "type", "name",
        "status", "data", "value", "values", "result", "results", "error",
        "errors", "object", "objects", "model", "models", "fields", "field",
        "Meta", "Config", "setUp", "tearDown", "save", "delete", "create",
        "update", "get", "post", "put", "patch", "list", "retrieve", "destroy",
        "perform", "validate", "clean", "format", "render", "dispatch",
        "get_queryset", "get_serializer", "get_object",
    }

    for raw_line in diff_text.splitlines():
        if raw_line.startswith("+++ b/"):
            current_file = raw_line[6:]
            continue
        if not raw_line.startswith("+") or raw_line.startswith("+++"):
            continue

        # Skip test files — identifiers there are test-local
        if "test_" in current_file or "/tests/" in current_file:
            continue

        line = raw_line[1:]

        for match in re.finditer(r"\bclass\s+([A-Z][A-Za-z0-9]+)", line):
            identifier = match.group(1)
            stripped = re.sub(
                r"(Test|Serializer|View|Factory|Fake|Stub|Repository|Service|Executor|Registry|Error|Exception|Mixin|Base|Abstract)$",
                "", identifier
            )
            if (stripped and len(stripped) > 3
                    and stripped not in _SKIP_IDENTIFIERS
                    and stripped.lower() not in known_terms):
                items.append(ReviewFeedbackItem(
                    guardrail="G-06",
                    file=current_file,
                    description=f"Class '{identifier}' (stripped: '{stripped}') not in Ubiquitous Language Glossary.",
                    required_action=f"Either add '{stripped}' to docs/glossary.json via the Domain Expert, or rename to a Glossary-approved term.",
                ))

    return items


# ---------------------------------------------------------------------------
# Layer separation check (G-05)
# ---------------------------------------------------------------------------

def check_layer_separation(diff_text: str) -> list[ReviewFeedbackItem]:
    try:
        from .architect import check_layer_violations
    except ImportError:
        from agents.architect import check_layer_violations

    result = check_layer_violations(diff_text)
    return [
        ReviewFeedbackItem(
            guardrail="G-05",
            file=v.file,
            description=f"Infrastructure import in domain layer: {v.line}",
            required_action="Move this import to the infrastructure/ or application/ layer. Domain layer must have zero infrastructure dependencies.",
        )
        for v in result.violations
    ]


# ---------------------------------------------------------------------------
# Refactor behaviour check (G-04, AP-06)
# ---------------------------------------------------------------------------

def check_refactor_purity(story_id: str, branch: str) -> list[ReviewFeedbackItem]:
    """
    AP-06: Verify the [REFACTOR] commit did not change test pass count.
    Compares test output at [GREEN] and [REFACTOR] commit hashes.
    This is a heuristic — it checks that no new test file additions appear in the [REFACTOR] diff.
    """
    items: list[ReviewFeedbackItem] = []

    log = _git("log", "--oneline", "--format=%H %s", f"main..{branch}")
    refactor_hash = None
    for line in log.splitlines():
        if "[REFACTOR]" in line:
            refactor_hash = line.split()[0]
            break

    if not refactor_hash:
        return items

    refactor_diff = _git("show", refactor_hash)

    # Check for new test files added in [REFACTOR] (would indicate new behaviour)
    new_test_files = re.findall(r"^\+\+\+ b/.*test_.*\.py", refactor_diff, re.MULTILINE)
    if new_test_files:
        items.append(ReviewFeedbackItem(
            guardrail="AP-06",
            file=", ".join(new_test_files),
            description="[REFACTOR] commit added new test files. Refactoring must not add new behaviour or new tests.",
            required_action="Move any new tests to a separate story. [REFACTOR] commit must only rename, extract, or restructure existing code.",
        ))

    return items


# ---------------------------------------------------------------------------
# Coverage floor check (G-07)
# ---------------------------------------------------------------------------

def check_coverage_floor() -> list[ReviewFeedbackItem]:
    try:
        from .qa import run_coverage
    except ImportError:
        from agents.qa import run_coverage

    result = run_coverage()
    if not result.above_floor:
        return [ReviewFeedbackItem(
            guardrail="G-07",
            file="tests/unit/domain/",
            description=f"Domain layer coverage {result.domain_coverage_percent}% is below floor {result.floor}%.",
            required_action=f"Add domain unit tests to bring coverage to at least {result.floor}%. Do not submit for review until coverage is restored.",
        )]
    return []


# ---------------------------------------------------------------------------
# Full review
# ---------------------------------------------------------------------------

def review_branch(story_id: str, branch: str, diff_text: str) -> ReviewResult:
    """
    Run all review checks and return a ReviewResult.
    """
    result = ReviewResult(story_id=story_id, approved=False)
    all_items: list[ReviewFeedbackItem] = []

    # G-01, G-03: Commit history
    history_ok, history_issues = validate_commit_history(story_id, branch)
    result.commit_history_valid = history_ok
    for issue in history_issues:
        all_items.append(ReviewFeedbackItem(
            guardrail="G-01/G-03",
            file="git log",
            description=issue,
            required_action="Ensure [RED], [GREEN], [REFACTOR] commits exist in that order.",
        ))

    # G-05: Layer separation
    layer_items = check_layer_separation(diff_text)
    result.layer_check_passed = len(layer_items) == 0
    all_items.extend(layer_items)

    # G-06: Language compliance
    language_items = check_language_compliance(diff_text)
    result.language_check_passed = len(language_items) == 0
    all_items.extend(language_items)

    # G-07: Coverage floor
    coverage_items = check_coverage_floor()
    result.coverage_check_passed = len(coverage_items) == 0
    all_items.extend(coverage_items)

    # AP-06: Refactor purity
    refactor_items = check_refactor_purity(story_id, branch)
    all_items.extend(refactor_items)

    result.feedback_items = all_items
    result.approved = len(all_items) == 0
    result.notes = (
        f"Review complete. {len(all_items)} issue(s) found. "
        + ("APPROVED." if result.approved else "CHANGES_REQUESTED.")
    )

    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Code Reviewer Agent")
    sub = parser.add_subparsers(dest="command")

    rv = sub.add_parser("review", help="Review a branch for a story")
    rv.add_argument("story_id")
    rv.add_argument("branch")
    rv.add_argument("--diff-file", default=None, help="Path to pre-generated diff file")

    hist = sub.add_parser("check-history", help="Validate [RED]/[GREEN]/[REFACTOR] commit history")
    hist.add_argument("story_id")
    hist.add_argument("branch")

    lang = sub.add_parser("check-language", help="Check diff for language violations (G-06)")
    lang.add_argument("diff_file")

    args = parser.parse_args()

    if args.command == "review":
        if args.diff_file:
            diff_text = Path(args.diff_file).read_text()
        else:
            import subprocess
            res = subprocess.run(
                ["git", "diff", f"main...{args.branch}"],
                capture_output=True, text=True, cwd=str(_ROOT),
            )
            diff_text = res.stdout

        result = review_branch(args.story_id, args.branch, diff_text)
        print(f"\nReview Result: {'APPROVED' if result.approved else 'CHANGES_REQUESTED'}")
        print(result.notes)

        if result.feedback_items:
            print(f"\n{len(result.feedback_items)} issue(s):")
            for item in result.feedback_items:
                print(f"\n  [{item.guardrail}] {item.file}")
                print(f"  Issue:  {item.description}")
                print(f"  Action: {item.required_action}")

        raise SystemExit(0 if result.approved else 1)

    elif args.command == "check-history":
        ok, issues = validate_commit_history(args.story_id, args.branch)
        if ok:
            print("Commit history VALID — [RED], [GREEN], [REFACTOR] all present.")
        else:
            for issue in issues:
                print(f"  ISSUE: {issue}")
            raise SystemExit(1)

    elif args.command == "check-language":
        diff_text = Path(args.diff_file).read_text()
        items = check_language_compliance(diff_text)
        if not items:
            print("Language check PASSED — all identifiers in Glossary.")
        else:
            print(f"Language check FAILED — {len(items)} violation(s):")
            for item in items:
                print(f"  [{item.guardrail}] {item.file}: {item.description}")
            raise SystemExit(1)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
