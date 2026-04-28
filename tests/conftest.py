"""
Shared test fixtures and configuration for the multi-agent TDD+DDD test suite.
This conftest.py is at the top level for all test directories.
"""

import pytest
import sys
from pathlib import Path

# Ensure src/ is in the path for all tests
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))


@pytest.fixture
def glossary_path():
    """Fixture providing path to the Ubiquitous Language Glossary."""
    return _ROOT / "docs" / "glossary.json"


@pytest.fixture
def backlog_path():
    """Fixture providing path to the User Story Backlog."""
    return _ROOT / "docs" / "backlog.json"


@pytest.fixture
def domain_model_path():
    """Fixture providing path to the Domain Model Canvas."""
    return _ROOT / "docs" / "domain_model.yaml"


@pytest.fixture
def adr_dir():
    """Fixture providing path to the ADR directory."""
    return _ROOT / "docs" / "adr"


@pytest.fixture
def config_path():
    """Fixture providing path to the playbook configuration."""
    return _ROOT / "config" / "playbook.json"


# pytest hooks for multi-agent reporting
def pytest_configure(config):
    """Initialize pytest — called once at the start of the test session."""
    config.addinivalue_line(
        "markers",
        "domain: mark test as a domain-layer unit test (no infrastructure deps)",
    )
    config.addinivalue_line(
        "markers",
        "integration: mark test as an integration test (may use Django/DB)",
    )
    config.addinivalue_line(
        "markers",
        "property: mark test as a property-based test (hypothesis)",
    )


def pytest_collection_modifyitems(config, items):
    """Auto-mark tests based on their file path."""
    for item in items:
        if "tests/unit/domain" in str(item.fspath):
            item.add_marker(pytest.mark.domain)
        elif "tests/integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "tests/property" in str(item.fspath):
            item.add_marker(pytest.mark.property)
