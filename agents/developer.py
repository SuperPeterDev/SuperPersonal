"""
Test-First Developer Agent — executes the Red-Green-Refactor cycle.

Responsibilities (Playbook §2.2):
- Read the story and acceptance criteria before writing any production code
- Write the minimal failing test capturing the acceptance criteria (Red)
- Write the minimal production code to make that test pass — nothing more (Green)
- Refactor: improve structure and naming without changing behaviour (Refactor)
- Run the full test suite after every commit

Commit naming (enforced by Orchestrator):
  test: [RED] <story-id> — <description>
  feat: [GREEN] <story-id> — <description>
  refactor: [REFACTOR] <story-id> — <description>
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent
_CONFIG = json.loads((_ROOT / "config" / "playbook.json").read_text())


# ---------------------------------------------------------------------------
# Test runner
# ---------------------------------------------------------------------------

@dataclass
class TestRunResult:
    passed: bool
    failure_count: int
    pass_count: int
    stdout: str
    returncode: int


def run_tests(path_filter: str | None = None) -> TestRunResult:
    """
    Run the test suite. Optionally filter to a specific path or test file.
    Returns structured pass/fail result.
    """
    cmd = [sys.executable, "-m", "pytest", "--tb=short", "-q", "--no-header"]
    if path_filter:
        cmd.append(path_filter)

    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(_ROOT))

    stdout = result.stdout + result.stderr
    passed = result.returncode == 0

    # Parse counts from pytest output
    failure_count = 0
    pass_count = 0
    for line in stdout.splitlines():
        import re
        m = re.search(r"(\d+) passed", line)
        if m:
            pass_count = int(m.group(1))
        m = re.search(r"(\d+) failed", line)
        if m:
            failure_count = int(m.group(1))

    return TestRunResult(
        passed=passed,
        failure_count=failure_count,
        pass_count=pass_count,
        stdout=stdout[-4000:],
        returncode=result.returncode,
    )


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------

def git(*args: str) -> tuple[int, str]:
    result = subprocess.run(
        ["git"] + list(args),
        capture_output=True,
        text=True,
        cwd=str(_ROOT),
    )
    return result.returncode, (result.stdout + result.stderr).strip()


def current_branch() -> str:
    _, branch = git("rev-parse", "--abbrev-ref", "HEAD")
    return branch.strip()


def stage_file(path: str) -> None:
    git("add", path)


def commit(message: str) -> tuple[bool, str]:
    rc, output = git("commit", "-m", message)
    return rc == 0, output


def get_diff(base: str = "HEAD~1") -> str:
    _, diff = git("diff", base)
    return diff


# ---------------------------------------------------------------------------
# Commit validation (Guardrails)
# ---------------------------------------------------------------------------

def validate_red_commit(diff_text: str) -> tuple[bool, str]:
    """
    G-01: The [RED] commit must contain only test file changes.
    No production code files (src/**/*.py excluding tests) should be added.
    """
    import re
    production_added = re.findall(r"^\+\+\+ b/(src/(?!.*/tests?).*\.py)", diff_text, re.MULTILINE)
    # Allow shared schemas if needed, but not models, views, executors
    actual_violations = [
        f for f in production_added
        if not any(t in f for t in ["tests", "test_", "conftest"])
    ]
    if actual_violations:
        return False, f"G-01 violation: [RED] commit modified production files: {actual_violations}"
    return True, "ok"


def validate_commit_tag(message: str, expected_tag: str) -> tuple[bool, str]:
    if expected_tag not in message:
        return False, f"Commit message must contain '{expected_tag}'. Got: '{message}'"
    return True, "ok"


# ---------------------------------------------------------------------------
# Developer workflow helpers
# ---------------------------------------------------------------------------

def create_feature_branch(story_id: str) -> str:
    branch = f"feature/{story_id}"
    rc, _ = git("checkout", "-b", branch)
    if rc != 0:
        git("checkout", branch)
    return branch


def red_phase_checklist(story_id: str) -> dict[str, Any]:
    """
    Pre-flight checklist before writing the Red test.
    Returns a dict the Developer must verify before writing any code.
    """
    from .product_owner import get_story, validate_acceptance_criteria
    from .domain_expert import load_glossary

    story = get_story(story_id)
    criteria_result = validate_acceptance_criteria(story_id)
    glossary = load_glossary()
    known_terms = {e["term"] for e in glossary["terms"]}

    return {
        "story_id": story_id,
        "narrative": story["narrative"],
        "acceptance_criteria": story["acceptance_criteria"],
        "criteria_valid": criteria_result.is_valid,
        "criteria_issues": criteria_result.issues,
        "glossary_terms_available": sorted(known_terms),
        "bounded_context": story["bounded_context"],
        "instruction": (
            "1. Read narrative and acceptance criteria carefully.\n"
            "2. Identify the single behaviour to test (one AC at a time).\n"
            "3. Write the test using only Glossary-approved identifiers.\n"
            "4. Do NOT open any existing production code files.\n"
            "5. Commit with: test: [RED] {story_id} — <description>"
        ).format(story_id=story_id),
    }


def run_and_report(story_id: str, phase: str) -> None:
    """Run full test suite and print a phase report."""
    result = run_tests()
    tag = {"red": "[RED]", "green": "[GREEN]", "refactor": "[REFACTOR]"}.get(phase, phase)
    status = "PASS" if result.passed else "FAIL"
    print(f"\n{'='*60}")
    print(f"Phase: {tag}  Story: {story_id}  Suite: {status}")
    print(f"Passed: {result.pass_count}  Failed: {result.failure_count}")
    if not result.passed:
        print("\n--- Output ---")
        print(result.stdout)
    print("=" * 60)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Test-First Developer Agent")
    sub = parser.add_subparsers(dest="command")

    cl = sub.add_parser("checklist", help="Print Red phase checklist for a story")
    cl.add_argument("story_id")

    rt = sub.add_parser("run-tests", help="Run the full test suite")
    rt.add_argument("--filter", default=None)

    vrc = sub.add_parser("validate-red", help="Validate that a commit qualifies as a [RED] commit")
    vrc.add_argument("--base", default="HEAD~1")

    rp = sub.add_parser("report", help="Run tests and print phase report")
    rp.add_argument("story_id")
    rp.add_argument("phase", choices=["red", "green", "refactor"])

    sub.add_parser("branch", help="Show current git branch")

    args = parser.parse_args()

    if args.command == "checklist":
        result = red_phase_checklist(args.story_id)
        print(json.dumps(result, indent=2, default=str))

    elif args.command == "run-tests":
        result = run_tests(args.filter)
        print(f"{'PASS' if result.passed else 'FAIL'}  passed={result.pass_count}  failed={result.failure_count}")
        if not result.passed:
            print(result.stdout)
            raise SystemExit(1)

    elif args.command == "validate-red":
        diff = get_diff(args.base)
        ok, msg = validate_red_commit(diff)
        print(f"{'PASS' if ok else 'FAIL'}: {msg}")
        if not ok:
            raise SystemExit(1)

    elif args.command == "report":
        run_and_report(args.story_id, args.phase)

    elif args.command == "branch":
        print(current_branch())

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
