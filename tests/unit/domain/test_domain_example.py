"""
Example domain unit tests — pure domain logic, zero infrastructure.

These tests demonstrate the expected test structure for domain layer tests:
- No Django imports
- No external I/O (database, network, files)
- Direct instantiation of domain classes
- Test domain invariants and state transitions

Replace these example tests with real tests for your domain aggregates and services.
"""

import pytest


class TestDomainExamplePlaceholder:
    """Placeholder test class — replace with real domain tests."""

    def test_placeholder(self):
        """This is a placeholder. Replace with real domain tests."""
        # Example: test CommandStatus transition rules
        # Example: test CommandPayload validation (level 0-100, seconds > 0)
        # Example: test Device aggregate invariants (HardwareID uniqueness, last_seen monotonic increase)
        # Example: test that no domain class has uninitialized state
        pass
