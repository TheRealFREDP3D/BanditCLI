"""Unit tests for the BanditLevelInfo class."""

import json
import os
import sys
import tempfile
from unittest.mock import MagicMock, Mock, patch

# Add the src directory to the path so we can import the modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from level_info import BanditLevelInfo


class TestBanditLevelInfo:
    """Test cases for the BanditLevelInfo class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.mock_notify = Mock()
        self.temp_dir = tempfile.mkdtemp()
        self.test_levels_file = os.path.join(self.temp_dir, "test_levels.json")

        # Create test data
        self.test_data = {
            "0": {
                "level": 0,
                "title": "Level 0",
                "goal": "Connect to bandit.labs.overthewire.org on port 2220 using SSH.",
                "commands": ["ssh", "ls"],
                "reading_material": [
                    {"title": "SSH Basics", "url": "https://example.com/ssh"},
                    "Manual page",
                ],
                "url": "https://overthewire.org/wargames/bandit/bandit0.html",
            },
            "1": {
                "level": 1,
                "title": "Level 1",
                "goal": "Find the password for the next level.",
                "commands": ["ls", "cat", "grep"],
                "reading_material": [
                    {"title": "File Operations", "url": "https://example.com/files"}
                ],
                "url": "https://overthewire.org/wargames/bandit/bandit1.html",
            },
        }

        with open(self.test_levels_file, "w") as f:
            json.dump(self.test_data, f)

    def teardown_method(self):
        """Clean up after each test method."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_init_default(self):
        """Test BanditLevelInfo initialization with default parameters."""
        level_info = BanditLevelInfo()

        assert level_info.levels_file_path == "bandit_levels.json"
        assert level_info.notify is not None
        assert level_info.cache is not None
        assert level_info.levels_data is not None

    def test_init_custom_params(self):
        """Test BanditLevelInfo initialization with custom parameters."""
        custom_notify = Mock()
        level_info = BanditLevelInfo(
            levels_file_path=self.test_levels_file, notify_callback=custom_notify
        )

        assert level_info.levels_file_path == self.test_levels_file
        assert level_info.notify == custom_notify

    def test_default_notify(self):
        """Test default notification handler."""
        level_info = BanditLevelInfo()

        # Capture print output
        with patch("builtins.print") as mock_print:
            level_info._default_notify("Test message", "warning")
            mock_print.assert_called_once_with("[WARNING] Test message")

    def test_load_levels_data_from_file_success(self):
        """Test successful loading of level data from file."""
        level_info = BanditLevelInfo(
            levels_file_path=self.test_levels_file, notify_callback=self.mock_notify
        )

        data = level_info._load_levels_data_from_file()

        assert data == self.test_data
        self.mock_notify.assert_called()

    def test_load_levels_data_from_file_not_found(self):
        """Test loading level data when file doesn't exist (fallback)."""
        level_info = BanditLevelInfo(
            levels_file_path="nonexistent.json", notify_callback=self.mock_notify
        )

        data = level_info._load_levels_data_from_file()

        # Should return fallback data
        assert "0" in data
        assert data["0"]["level"] == 0
        self.mock_notify.assert_called()

    def test_load_levels_data_from_file_invalid_json(self):
        """Test loading level data with invalid JSON (fallback)."""
        invalid_file = os.path.join(self.temp_dir, "invalid.json")
        with open(invalid_file, "w") as f:
            f.write("invalid json content")

        level_info = BanditLevelInfo(
            levels_file_path=invalid_file, notify_callback=self.mock_notify
        )

        data = level_info._load_levels_data_from_file()

        # Should return fallback data
        assert "0" in data
        assert data["0"]["level"] == 0
        self.mock_notify.assert_called()

    def test_get_fallback_data(self):
        """Test fallback data generation."""
        level_info = BanditLevelInfo(notify_callback=self.mock_notify)
        fallback = level_info._get_fallback_data()

        assert "0" in fallback
        assert fallback["0"]["level"] == 0
        assert fallback["0"]["title"] == "Level 0"
        assert "ssh" in fallback["0"]["commands"]

    def test_load_levels_data_with_cache(self):
        """Test loading level data with caching."""
        level_info = BanditLevelInfo(
            levels_file_path=self.test_levels_file, notify_callback=self.mock_notify
        )

        # First call should load from file
        data1 = level_info._load_levels_data()
        assert data1 == self.test_data

        # Second call should use cache
        data2 = level_info._load_levels_data()
        assert data2 == self.test_data

        # Cache should be used (verify by checking cache mock)
        assert level_info.cache.get.called

    def test_get_level_info_success(self):
        """Test getting level information for existing level."""
        level_info = BanditLevelInfo(
            levels_file_path=self.test_levels_file, notify_callback=self.mock_notify
        )

        level_info_data = level_info.get_level_info(0)

        assert level_info_data == self.test_data["0"]
        assert level_info_data["title"] == "Level 0"

    def test_get_level_info_not_found(self):
        """Test getting level information for non-existing level."""
        level_info = BanditLevelInfo(
            levels_file_path=self.test_levels_file, notify_callback=self.mock_notify
        )

        level_info_data = level_info.get_level_info(999)

        assert level_info_data is None

    def test_get_level_info_with_cache(self):
        """Test getting level information with caching."""
        level_info = BanditLevelInfo(
            levels_file_path=self.test_levels_file, notify_callback=self.mock_notify
        )

        # First call should cache the result
        result1 = level_info.get_level_info(0)
        result2 = level_info.get_level_info(0)

        assert result1 == result2
        assert result1 == self.test_data["0"]

    def test_get_all_levels(self):
        """Test getting all level information."""
        level_info = BanditLevelInfo(
            levels_file_path=self.test_levels_file, notify_callback=self.mock_notify
        )

        all_levels = level_info.get_all_levels()

        assert all_levels == self.test_data

    def test_get_available_levels(self):
        """Test getting list of available level numbers."""
        level_info = BanditLevelInfo(
            levels_file_path=self.test_levels_file, notify_callback=self.mock_notify
        )

        available_levels = level_info.get_available_levels()

        assert available_levels == [0, 1]

    def test_get_level_goal_success(self):
        """Test getting goal for existing level."""
        level_info = BanditLevelInfo(
            levels_file_path=self.test_levels_file, notify_callback=self.mock_notify
        )

        goal = level_info.get_level_goal(0)

        assert goal == self.test_data["0"]["goal"]

    def test_get_level_goal_not_found(self):
        """Test getting goal for non-existing level."""
        level_info = BanditLevelInfo(
            levels_file_path=self.test_levels_file, notify_callback=self.mock_notify
        )

        goal = level_info.get_level_goal(999)

        assert goal == "Level information not available"

    def test_get_recommended_commands_success(self):
        """Test getting recommended commands for existing level."""
        level_info = BanditLevelInfo(
            levels_file_path=self.test_levels_file, notify_callback=self.mock_notify
        )

        commands = level_info.get_recommended_commands(0)

        assert commands == self.test_data["0"]["commands"]

    def test_get_recommended_commands_not_found(self):
        """Test getting recommended commands for non-existing level."""
        level_info = BanditLevelInfo(
            levels_file_path=self.test_levels_file, notify_callback=self.mock_notify
        )

        commands = level_info.get_recommended_commands(999)

        assert commands == []

    def test_get_reading_materials_success(self):
        """Test getting reading materials for existing level."""
        level_info = BanditLevelInfo(
            levels_file_path=self.test_levels_file, notify_callback=self.mock_notify
        )

        materials = level_info.get_reading_materials(0)

        assert materials == self.test_data["0"]["reading_material"]

    def test_get_reading_materials_not_found(self):
        """Test getting reading materials for non-existing level."""
        level_info = BanditLevelInfo(
            levels_file_path=self.test_levels_file, notify_callback=self.mock_notify
        )

        materials = level_info.get_reading_materials(999)

        assert materials == []

    def test_format_level_info_success(self):
        """Test formatting level information for existing level."""
        level_info = BanditLevelInfo(
            levels_file_path=self.test_levels_file, notify_callback=self.mock_notify
        )

        formatted = level_info.format_level_info(0)

        assert "Bandit Level 0" in formatted
        assert "Level 0" in formatted
        assert "Connect to bandit.labs.overthewire.org" in formatted
        assert "ssh" in formatted
        assert "SSH Basics" in formatted

    def test_format_level_info_not_found(self):
        """Test formatting level information for non-existing level."""
        level_info = BanditLevelInfo(
            levels_file_path=self.test_levels_file, notify_callback=self.mock_notify
        )

        formatted = level_info.format_level_info(999)

        assert "Level 999 - Not Available" in formatted
        assert "Available levels: 0, 1" in formatted

    def test_format_level_info_with_cache(self):
        """Test formatting level information with caching."""
        level_info = BanditLevelInfo(
            levels_file_path=self.test_levels_file, notify_callback=self.mock_notify
        )

        # First call should cache the result
        result1 = level_info.format_level_info(0)
        result2 = level_info.format_level_info(0)

        assert result1 == result2

    def test_format_level_info_from_data(self):
        """Test internal method _format_level_info_from_data."""
        level_info = BanditLevelInfo(notify_callback=self.mock_notify)

        formatted = level_info._format_level_info_from_data(0, self.test_data["0"])

        assert "Bandit Level 0" in formatted
        assert "Level 0" in formatted
        assert "Connect to bandit.labs.overthewire.org" in formatted

    def test_search_levels_by_goal(self):
        """Test searching levels by goal content."""
        level_info = BanditLevelInfo(
            levels_file_path=self.test_levels_file, notify_callback=self.mock_notify
        )

        results = level_info.search_levels("connect")

        assert 0 in results  # Level 0 contains "connect" in goal

    def test_search_levels_by_command(self):
        """Test searching levels by command content."""
        level_info = BanditLevelInfo(
            levels_file_path=self.test_levels_file, notify_callback=self.mock_notify
        )

        results = level_info.search_levels("grep")

        assert 1 in results  # Level 1 contains "grep" in commands

    def test_search_levels_case_insensitive(self):
        """Test that search is case insensitive."""
        level_info = BanditLevelInfo(
            levels_file_path=self.test_levels_file, notify_callback=self.mock_notify
        )

        results_lower = level_info.search_levels("ssh")
        results_upper = level_info.search_levels("SSH")

        assert results_lower == results_upper

    def test_search_levels_no_results(self):
        """Test searching levels with no matches."""
        level_info = BanditLevelInfo(
            levels_file_path=self.test_levels_file, notify_callback=self.mock_notify
        )

        results = level_info.search_levels("nonexistent")

        assert results == []

    def test_clear_cache(self):
        """Test clearing cache."""
        level_info = BanditLevelInfo(
            levels_file_path=self.test_levels_file, notify_callback=self.mock_notify
        )

        # Load some data to populate cache
        level_info.get_level_info(0)
        level_info.format_level_info(0)

        # Clear cache
        level_info.clear_cache()

        # Verify notification was called
        self.mock_notify.assert_called_with("Level cache cleared", severity="info")

    @patch("src.level_info.importlib.resources.open_text")
    def test_load_from_package_resources(self, mock_open_text):
        """Test loading level data from package resources."""
        mock_file = MagicMock()
        mock_file.__enter__.return_value = mock_file
        mock_file.read.return_value = json.dumps(self.test_data)
        mock_open_text.return_value = mock_file

        level_info = BanditLevelInfo(
            levels_file_path="test_levels.json", notify_callback=self.mock_notify
        )

        data = level_info._load_levels_data_from_file()

        assert data == self.test_data
        mock_open_text.assert_called_once_with("src", "test_levels.json")

    def test_level_info_with_minimal_data(self):
        """Test handling level info with minimal required fields."""
        minimal_data = {"0": {"level": 0, "goal": "Basic goal"}}

        minimal_file = os.path.join(self.temp_dir, "minimal.json")
        with open(minimal_file, "w") as f:
            json.dump(minimal_data, f)

        level_info = BanditLevelInfo(
            levels_file_path=minimal_file, notify_callback=self.mock_notify
        )

        # Test methods with minimal data
        goal = level_info.get_level_goal(0)
        commands = level_info.get_recommended_commands(0)
        materials = level_info.get_reading_materials(0)

        assert goal == "Basic goal"
        assert commands == []
        assert materials == []

    def test_level_info_with_mixed_reading_materials(self):
        """Test handling mixed reading material formats."""
        mixed_data = {
            "0": {
                "level": 0,
                "goal": "Test goal",
                "reading_material": [
                    {"title": "Link", "url": "https://example.com"},
                    {"title": "Title only"},
                    "Plain text material",
                    {"url": "URL only"},  # Missing title
                ],
            }
        }

        mixed_file = os.path.join(self.temp_dir, "mixed.json")
        with open(mixed_file, "w") as f:
            json.dump(mixed_data, f)

        level_info = BanditLevelInfo(levels_file_path=mixed_file, notify_callback=self.mock_notify)

        formatted = level_info.format_level_info(0)

        assert "[Link](https://example.com)" in formatted
        assert "Title only" in formatted
        assert "Plain text material" in formatted
        # URL without title should not create a link
        assert "](URL only)" not in formatted
