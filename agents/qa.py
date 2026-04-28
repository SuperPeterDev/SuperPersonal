"""
QA / Tester Agent — extends coverage beyond the Developer's happy-path tests.

Responsibilities (Playbook §2.2):
- Write integration tests crossing module/service boundaries
- Write property-based tests for core domain invariants
- Write edge-case tests: null inputs, zero quantities, boundary values
- Write regression tests for any fixed bug (test must fail without fix, pass with it)
- Find failure modes — NOT confirm that success cases work
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
_COVERAGE_FLOOR = _CONFIG["coverage"]["COVERAGE_FLOOR_PERCENT"]
_INTEGRATION_DIR = _ROOT / _CONFIG["paths"]["tests_integration"]
_PROPERTY_DIR = _ROOT / _CONFIG["paths"]["tests_property"]
_DOMAIN_TEST_DIR = _ROOT / _CONFIG["paths"]["tests_unit_domain"]


# ---------------------------------------------------------------------------
# Coverage
# ---------------------------------------------------------------------------

@dataclass
class CoverageResult:
    domain_coverage_percent: float
    above_floor: bool
    floor: int
    raw_report: dict[str, Any]


def run_coverage() -> CoverageResult:
    """
    Run pytest with coverage on domain layer only.
    Returns the coverage percentage for the domain layer.
    """
    result = subprocess.run(
        [
            sys.executable, "-m", "pytest",
            "--cov=src",
            "--cov-report=json",
            "--cov-report=term-missing",
            "-q", "--no-header",
        ],
        capture_output=True,
        text=True,
        cwd=str(_ROOT),
    )

    coverage_json = _ROOT / "coverage.json"
    raw = {}
    domain_percent = 0.0

    if coverage_json.exists():
        raw = json.loads(coverage_json.read_text())
        # Compute domain-only coverage
        domain_files = {
            k: v for k, v in raw.get("files", {}).items()
            if "domain" in k or "shared" in k
        }
        if domain_files:
            total_lines = sum(v["summary"]["num_statements"] for v in domain_files.values())
            covered_lines = sum(v["summary"]["covered_lines"] for v in domain_files.values())
            domain_percent = round((covered_lines / total_lines * 100) if total_lines else 0, 1)

    return CoverageResult(
        domain_coverage_percent=domain_percent,
        above_floor=domain_percent >= _COVERAGE_FLOOR,
        floor=_COVERAGE_FLOOR,
        raw_report=raw,
    )


# ---------------------------------------------------------------------------
# QA checklist for a story
# ---------------------------------------------------------------------------

@dataclass
class QAChecklist:
    story_id: str
    edge_cases: list[str]
    integration_scenarios: list[str]
    property_invariants: list[str]
    regression_notes: str


def build_qa_checklist(story_id: str) -> QAChecklist:
    """
    Build a QA checklist from the story's acceptance criteria.
    Returns edge cases, integration scenarios, and invariants to test.
    """
    from .product_owner import get_story

    story = get_story(story_id)
    criteria_text = "\n".join(
        ac.get("gherkin", "") for ac in story.get("acceptance_criteria", [])
    )

    # Domain-invariant edge cases common to all Command stories
    edge_cases: list[str] = []
    integration_scenarios: list[str] = []
    property_invariants: list[str] = []

    bc = story.get("bounded_context", "")

    if bc == "CommandDispatch":
        edge_cases += [
            "Command issued to a Device that was deleted mid-flight",
            "Concurrent CancelCommand and CompleteCommand for the same Command ID",
            "CMD_SCHEDULED_SHUTDOWN with seconds=0 (boundary: must be > 0)",
            "CMD_SET_VOLUME with level=0 (boundary: valid minimum)",
            "CMD_SET_VOLUME with level=100 (boundary: valid maximum)",
            "CMD_SET_VOLUME with level=101 (must reject)",
            "Command status transition from SUCCESS → CANCELLED (must reject: terminal state)",
            "Command status transition from FAILED → RUNNING (must reject: terminal state)",
        ]
        integration_scenarios += [
            "Full flow: POST /commands → GET /commands/pending → POST /commands/{id}/result",
            "CommandQueue drains in FIFO order when device reconnects",
        ]
        property_invariants += [
            "For any CommandStatus in terminal states {SUCCESS, FAILED}, all transition attempts raise",
            "For any CMD_SET_VOLUME command, level outside [0, 100] is always rejected",
        ]

    if bc == "DeviceManagement":
        edge_cases += [
            "Register same HardwareID twice (must update, not create duplicate)",
            "Device.last_seen at exactly 60 seconds ago (boundary: ONLINE vs OFFLINE)",
            "Device with empty hostname string",
        ]
        integration_scenarios += [
            "POST /devices/register → GET /devices → verify device appears",
            "Device online/offline status updates with time passage",
        ]
        property_invariants += [
            "DeviceStatus is always ONLINE iff last_seen < 60s ago, for any datetime input",
        ]

    if bc == "PresetManagement":
        edge_cases += [
            "Create Preset with URL that is 1024 characters (boundary: max length)",
            "Create Preset with empty name (must reject)",
            "Create Preset with URL missing scheme (e.g., 'youtube.com' without https://)",
            "Delete a Preset that has already been deleted (idempotency)",
        ]
        integration_scenarios += [
            "Create Preset → Issue CMD_OPEN_PRESET → verify URL in CommandPayload",
        ]

    if bc == "Monitoring":
        edge_cases += [
            "SystemMetrics with cpu_percent=0.0 (valid minimum)",
            "SystemMetrics with ram_percent=100.0 (valid maximum: system at capacity)",
            "ThresholdExceeded fires at exactly threshold boundary (e.g., ram=90.0)",
        ]

    return QAChecklist(
        story_id=story_id,
        edge_cases=edge_cases,
        integration_scenarios=integration_scenarios,
        property_invariants=property_invariants,
        regression_notes=(
            "For any bug fixed during this story, write a regression test that:\n"
            "  1. Fails WITHOUT the fix applied\n"
            "  2. Passes WITH the fix applied\n"
            "Place in tests/integration/ with filename suffix _regression.py"
        ),
    )


# ---------------------------------------------------------------------------
# Test file scaffolds
# ---------------------------------------------------------------------------

def scaffold_integration_test(story_id: str, description: str) -> Path:
    """Create a skeleton integration test file for a story."""
    slug = story_id.lower().replace("-", "_")
    path = _INTEGRATION_DIR / f"test_{slug}_integration.py"
    if path.exists():
        return path

    content = f'''"""
Integration tests for {story_id}: {description}
Generated by QA Agent — Phase 5.

These tests cross module/service boundaries. They may use:
- Django test client
- requests-mock for HTTP simulation
- Real SQLite database (test settings)

They must NOT:
- Test framework internals (AP-04)
- Duplicate domain unit tests already in tests/unit/domain/
"""

import pytest


class Test{story_id.replace("-", "")}Integration:
    """Integration scenarios for {story_id}."""

    def test_placeholder(self):
        # Replace with real integration test
        pytest.skip("QA integration test scaffold — implement for {story_id}")
'''
    _INTEGRATION_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def scaffold_property_test(story_id: str, invariant: str) -> Path:
    """Create a skeleton property test file for a story."""
    slug = story_id.lower().replace("-", "_")
    path = _PROPERTY_DIR / f"test_{slug}_property.py"
    if path.exists():
        return path

    content = f'''"""
Property-based tests for {story_id}.
Invariant: {invariant}

Uses hypothesis for property testing.
Install: pip install hypothesis
"""

import pytest

try:
    from hypothesis import given, settings
    from hypothesis import strategies as st
    HYPOTHESIS_AVAILABLE = True
except ImportError:
    HYPOTHESIS_AVAILABLE = False


@pytest.mark.skipif(not HYPOTHESIS_AVAILABLE, reason="hypothesis not installed")
class Test{story_id.replace("-", "")}Properties:
    """Property tests for {story_id}."""

    def test_placeholder_property(self):
        # Replace with real property test
        pytest.skip("QA property test scaffold — implement for {story_id}")
'''
    _PROPERTY_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="QA / Tester Agent")
    sub = parser.add_subparsers(dest="command")

    cov = sub.add_parser("coverage", help="Run test suite with coverage report")

    ck = sub.add_parser("checklist", help="Print QA checklist for a story")
    ck.add_argument("story_id")

    si = sub.add_parser("scaffold-integration", help="Create integration test scaffold")
    si.add_argument("story_id")
    si.add_argument("description")

    sp = sub.add_parser("scaffold-property", help="Create property test scaffold")
    sp.add_argument("story_id")
    sp.add_argument("invariant")

    args = parser.parse_args()

    if args.command == "coverage":
        result = run_coverage()
        status = "PASS" if result.above_floor else "FAIL"
        print(f"Domain layer coverage: {result.domain_coverage_percent}%  [{status}]  (floor: {result.floor}%)")
        if not result.above_floor:
            raise SystemExit(1)

    elif args.command == "checklist":
        checklist = build_qa_checklist(args.story_id)
        print(f"\n=== QA Checklist for {args.story_id} ===")
        print("\nEdge Cases:")
        for ec in checklist.edge_cases:
            print(f"  [ ] {ec}")
        print("\nIntegration Scenarios:")
        for sc in checklist.integration_scenarios:
            print(f"  [ ] {sc}")
        print("\nProperty Invariants:")
        for inv in checklist.property_invariants:
            print(f"  [ ] {inv}")
        print(f"\nRegression Notes:\n{checklist.regression_notes}")

    elif args.command == "scaffold-integration":
        path = scaffold_integration_test(args.story_id, args.description)
        print(f"Integration test scaffold created: {path.relative_to(_ROOT)}")

    elif args.command == "scaffold-property":
        path = scaffold_property_test(args.story_id, args.invariant)
        print(f"Property test scaffold created: {path.relative_to(_ROOT)}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
