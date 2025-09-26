"""Shared test configurations and fixtures."""
import sys
import os
import pytest

# Add the src directory to the path so we can import the modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))