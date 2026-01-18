"""Shared test configurations and fixtures."""

import os
import sys
from unittest.mock import Mock

import pytest

# Add the src directory to the path so we can import the modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


@pytest.fixture
def mock_notify():
    """Return a mock notification callback."""
    return Mock()
