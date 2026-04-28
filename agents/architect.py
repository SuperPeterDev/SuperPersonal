"""
Architect Agent — enforces DDD structural patterns and bounded context placement.

Responsibilities (Playbook §2.2):
- Define package/module skeleton before development starts on a new bounded context
- Produce ADRs for non-trivial structural choices
- Review diffs for layer violations (G-05)
- Enforce: Domain Layer has zero dependencies on Infrastructure Layer
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent
_CONFIG = json.loads((_ROOT / "config" / "playbook.json").read_text())
_ADR_DIR = _ROOT / _CONFIG["paths"]["adr_dir"]

# ---------------------------------------------------------------------------
# Layer violation detection (G-05)
# ---------------------------------------------------------------------------

# Patterns that must never appear inside domain/ directories
_INFRASTRUCTURE_IMPORTS = [
    r"from django",
    r"import django",
    r"from rest_framework",
    r"import rest_framework",
    r"import requests\b",
    r"from requests\b",
    r"import redis\b",
    r"from redis\b",
    r"import celery\b",
    r"from celery\b",
    r"import sqlalchemy\b",
    r"import psycopg2\b",
    r"import boto",
    r"import paramiko",
    r"import pycaw",
    r"import pyautogui",
]

# Patterns that must never appear inside domain/ for the client side
_CLIENT_DOMAIN_INFRA_IMPORTS = _INFRASTRUCTURE_IMPORTS + [
    r"import subprocess\b",
    r"from subprocess\b",
    r"import os\b",
    r"from os\b",
]


@dataclass
class LayerViolation:
    file: str
    line_number: int
    line: str
    reason: str


@dataclass
class LayerCheckResult:
    violations: list[LayerViolation]
    passed: bool


def check_layer_violations(diff_text: str) -> LayerCheckResult:
    """
    G-05: Scan a git diff for infrastructure imports inside domain/ directories.
    Only addition lines (+) in domain/ files are checked.
    """
    violations: list[LayerViolation] = []
    current_file = ""
    line_number = 0

    for raw_line in diff_text.splitlines():
        if raw_line.startswith("+++ b/"):
            current_file = raw_line[6:]
            line_number = 0
            continue

        if raw_line.startswith("@@"):
            # Extract starting line number from hunk header
            match = re.search(r"\+(\d+)", raw_line)
            if match:
                line_number = int(match.group(1)) - 1
            continue

        if raw_line.startswith("+") and not raw_line.startswith("+++"):
            line_number += 1
            line = raw_line[1:]

            # Only check domain/ files
            if "/domain/" not in current_file:
                continue

            patterns = (
                _CLIENT_DOMAIN_INFRA_IMPORTS
                if current_file.startswith("src/client")
                else _INFRASTRUCTURE_IMPORTS
            )
            for pattern in patterns:
                if re.search(pattern, line):
                    violations.append(LayerViolation(
                        file=current_file,
                        line_number=line_number,
                        line=line.strip(),
                        reason=f"Infrastructure import in domain layer: '{pattern}'",
                    ))
        elif not raw_line.startswith("-"):
            line_number += 1

    return LayerCheckResult(violations=violations, passed=len(violations) == 0)


# ---------------------------------------------------------------------------
# Dead code detection (G-10)
# ---------------------------------------------------------------------------

@dataclass
class UnreachableCodeResult:
    unreachable_identifiers: list[str]
    passed: bool


def check_unreachable_code(diff_text: str) -> UnreachableCodeResult:
    """
    G-10: Detect methods or classes added in the [GREEN] commit that are not
    referenced by any test. This is a heuristic — surfaces candidates for review.
    """
    added_definitions: list[str] = []
    added_usages: set[str] = set()

    for raw_line in diff_text.splitlines():
        if not raw_line.startswith("+"):
            continue
        line = raw_line[1:]

        class_match = re.search(r"class\s+([A-Za-z][A-Za-z0-9_]+)", line)
        func_match = re.search(r"def\s+([a-z][a-z0-9_]+)", line)
        if class_match:
            added_definitions.append(class_match.group(1))
        if func_match:
            name = func_match.group(1)
            if not name.startswith("test_"):
                added_definitions.append(name)

        # Simple usage detection: identifier appears without def/class keyword
        for word in re.findall(r"\b([A-Za-z][A-Za-z0-9_]+)\b", line):
            added_usages.add(word)

    unreachable = [d for d in added_definitions if d not in added_usages]
    return UnreachableCodeResult(unreachable_identifiers=unreachable, passed=len(unreachable) == 0)


# ---------------------------------------------------------------------------
# Package skeleton generation
# ---------------------------------------------------------------------------

def create_bounded_context_skeleton(context_name: str, location: str = "src/server") -> list[str]:
    """
    Create the DDD layer skeleton for a new bounded context.
    Returns list of created paths.
    """
    base = _ROOT / location / context_name.lower()
    created: list[str] = []

    dirs = [
        base / "domain",
        base / "application",
        base / "infrastructure",
        base / "api",
        base / "migrations",
    ]

    files_per_dir = {
        "domain": ["__init__.py", "models.py", "services.py", "events.py"],
        "application": ["__init__.py", "services.py", "commands.py"],
        "infrastructure": ["__init__.py", "repositories.py", "serializers.py"],
        "api": ["__init__.py", "views.py", "urls.py"],
        "migrations": ["__init__.py"],
    }

    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
        dir_name = d.name
        for fname in files_per_dir.get(dir_name, ["__init__.py"]):
            fpath = d / fname
            if not fpath.exists():
                fpath.write_text(f'"""\n{context_name} — {dir_name}/{fname}\nGenerated by Architect Agent.\n"""\n')
                created.append(str(fpath.relative_to(_ROOT)))

    return created


# ---------------------------------------------------------------------------
# ADR management
# ---------------------------------------------------------------------------

def list_adrs() -> list[str]:
    if not _ADR_DIR.exists():
        return []
    return sorted(p.name for p in _ADR_DIR.glob("ADR-*.md"))


def get_next_adr_number() -> str:
    adrs = list_adrs()
    if not adrs:
        return "001"
    last = sorted(adrs)[-1]
    num = int(re.search(r"ADR-(\d+)", last).group(1))
    return str(num + 1).zfill(3)


def create_adr(title: str, status: str, context: str, decision: str, consequences: str) -> str:
    num = get_next_adr_number()
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    filename = f"ADR-{num}-{slug}.md"
    path = _ADR_DIR / filename

    content = f"""# ADR-{num}: {title}

**Status:** {status}
**Date:** {datetime.now(timezone.utc).date().isoformat()}
**Deciders:** Architect Agent

---

## Context

{context}

## Decision

{decision}

## Consequences

{consequences}
"""
    _ADR_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return filename


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Architect Agent")
    sub = parser.add_subparsers(dest="command")

    lv = sub.add_parser("check-layers", help="Check a git diff for layer violations (G-05)")
    lv.add_argument("diff_file", help="Path to file containing git diff")

    uc = sub.add_parser("check-dead-code", help="Check a [GREEN] diff for unreachable code (G-10)")
    uc.add_argument("diff_file")

    sk = sub.add_parser("create-skeleton", help="Create bounded context package skeleton")
    sk.add_argument("context_name")
    sk.add_argument("--location", default="src/server")

    sub.add_parser("list-adrs", help="List all ADRs")

    ca = sub.add_parser("create-adr", help="Create a new ADR")
    ca.add_argument("title")
    ca.add_argument("--status", default="Proposed")
    ca.add_argument("--context", default="")
    ca.add_argument("--decision", default="")
    ca.add_argument("--consequences", default="")

    args = parser.parse_args()

    if args.command == "check-layers":
        diff_text = Path(args.diff_file).read_text()
        result = check_layer_violations(diff_text)
        if result.passed:
            print("Layer check PASSED — no violations found.")
        else:
            print(f"Layer check FAILED — {len(result.violations)} violation(s):")
            for v in result.violations:
                print(f"  {v.file}:{v.line_number}  {v.reason}")
                print(f"    {v.line}")
            raise SystemExit(1)

    elif args.command == "check-dead-code":
        diff_text = Path(args.diff_file).read_text()
        result = check_unreachable_code(diff_text)
        if result.passed:
            print("Dead code check PASSED.")
        else:
            print(f"Potential unreachable identifiers: {result.unreachable_identifiers}")

    elif args.command == "create-skeleton":
        created = create_bounded_context_skeleton(args.context_name, args.location)
        print(f"Created {len(created)} files:")
        for f in created:
            print(f"  {f}")

    elif args.command == "list-adrs":
        for adr in list_adrs():
            print(f"  {adr}")

    elif args.command == "create-adr":
        fname = create_adr(args.title, args.status, args.context, args.decision, args.consequences)
        print(f"ADR created: docs/adr/{fname}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
