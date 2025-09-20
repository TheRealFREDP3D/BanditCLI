"""Sample test to verify pytest setup."""
import pytest

def test_example():
    """A simple test to verify pytest is working."""
    assert 1 + 1 == 2

def test_example_failure():
    """A simple test that fails to verify error reporting."""
    assert 1 + 1 == 3