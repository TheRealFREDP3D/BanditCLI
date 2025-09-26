"""Sample test to verify pytest setup."""
import pytest

def test_example():
    """A simple test to verify pytest is working."""
    assert 1 + 1 == 2

def test_example_failure():
    """A simple test that fails to verify error reporting. This test is expected to fail."""
    assert 1 + 1 == 3, "This test is designed to fail to verify that error reporting is working correctly"