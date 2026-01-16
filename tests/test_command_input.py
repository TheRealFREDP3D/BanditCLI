"""Unit tests for the BanditCLIApp class."""
import os
import sys

# Add the src directory to the path so we can import the modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.main import BanditCLIApp


class TestBanditCLIApp:
    """Test cases for the BanditCLIApp class."""

    def test_init(self):
        """Test BanditCLIApp initialization."""
        app = BanditCLIApp()
        assert app is not None

    def test_app_components(self):
        """Test that app has required components."""
        app = BanditCLIApp()
        # Test that the app has the expected attributes
        assert hasattr(app, 'title')
        assert hasattr(app, 'ssh_manager')
        assert hasattr(app, 'ai_mentor')
