"""
Example integration tests — cross-module/service boundaries.

These tests may use:
- Django test client (TestCase, APIClient)
- requests-mock for HTTP simulation
- Real SQLite test database (via Django settings)
- Multiple aggregates/contexts in a single test

They must NOT:
- Test framework internals (that's AP-04 — test the framework, not the domain)
- Duplicate domain unit tests already in tests/unit/domain/

Replace these example tests with real integration tests for your flows.
"""

import pytest


class TestIntegrationExamplePlaceholder:
    """Placeholder integration test class — replace with real integration tests."""

    def test_placeholder_integration(self):
        """
        This is a placeholder. Replace with real integration tests.

        Example scenarios:
        - Full Command lifecycle: POST /commands → poll GET /commands/pending → POST /commands/{id}/result
        - Device registration + command dispatch flow
        - CommandQueue drains in FIFO order when device reconnects
        """
        pass
