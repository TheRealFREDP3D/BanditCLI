"""Unit tests for caching in level info and AI mentor modules."""
import pytest
from unittest.mock import Mock, patch
import sys
import os

# Add the src directory to the path so we can import the modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from level_info import BanditLevelInfo
from ai_mentor import BanditAIMentor


class TestCachedLevelInfo:
    """Test cases for cached level info methods."""
    
    def test_get_level_info_uses_cache(self, tmp_path):
        """Test that get_level_info uses caching."""
        # Create a BanditLevelInfo instance with test data
        levels_data = {
            "0": {"level": 0, "goal": "Test goal", "commands": ["ls", "cat"]},
            "1": {"level": 1, "goal": "Another goal", "commands": ["pwd", "cd"]}
        }
        
        level_info = BanditLevelInfo()
        level_info.levels_data = levels_data
        
        # Mock the cache to track calls
        with patch('level_info.cache') as mock_cache:
            mock_cache.get.return_value = None  # Not in cache initially
            
            # Call get_level_info
            result1 = level_info.get_level_info(0)
            
            # Check that cache.get was called
            mock_cache.get.assert_called_with("level_info_0")
            
            # Check that cache.set was called to store the result
            mock_cache.set.assert_called_with("level_info_0", result1, ttl=3600)
            
            # Call again to verify it uses cache
            mock_cache.get.return_value = result1  # Now in cache
            result2 = level_info.get_level_info(0)
            
            # Check that the same result is returned
            assert result1 == result2
            # Check that cache.get was called again
            assert mock_cache.get.call_count == 2
    
    def test_format_level_info_uses_cache(self, tmp_path):
        """Test that format_level_info uses caching."""
        # Create a BanditLevelInfo instance with test data
        levels_data = {
            "0": {"level": 0, "goal": "Test goal", "commands": ["ls", "cat"]},
        }
        
        level_info = BanditLevelInfo()
        level_info.levels_data = levels_data
        
        # Mock the cache to track calls
        with patch('level_info.cache') as mock_cache:
            mock_cache.get.return_value = None  # Not in cache initially
            
            # Call format_level_info
            result1 = level_info.format_level_info(0)
            
            # Check that cache.get was called for the formatted info
            # Note: get_level_info is also cached, so we might see that call too
            # We're specifically checking for the formatted_level_info cache key
            calls = [call[0][0] for call in mock_cache.get.call_args_list]
            assert "formatted_level_info_0" in calls
            
            # Check that cache.set was called to store the result
            calls = [call[0][0] for call in mock_cache.set.call_args_list]
            assert "formatted_level_info_0" in calls
            
            # Call again to verify it uses cache
            mock_cache.get.return_value = result1  # Now in cache
            result2 = level_info.format_level_info(0)
            
            # Check that the same result is returned
            assert result1 == result2


class TestCachedAIMentor:
    """Test cases for cached AI mentor methods."""
    
    def test_get_level_hint_uses_cache(self):
        """Test that get_level_hint uses caching."""
        ai_mentor = BanditAIMentor()
        
        # Mock the cache to track calls
        with patch('ai_mentor.cache') as mock_cache:
            mock_cache.get.return_value = None  # Not in cache initially
            
            # Call get_level_hint
            result1 = ai_mentor.get_level_hint(0)
            
            # Check that cache.get was called
            mock_cache.get.assert_called_with("level_hint_0")
            
            # Check that cache.set was called to store the result
            mock_cache.set.assert_called_with("level_hint_0", result1, ttl=3600)
            
            # Call again to verify it uses cache
            mock_cache.get.return_value = result1  # Now in cache
            result2 = ai_mentor.get_level_hint(0)
            
            # Check that the same result is returned
            assert result1 == result2
            # Check that cache.get was called again
            assert mock_cache.get.call_count == 2
    
    def test_explain_command_uses_cache(self):
        """Test that explain_command uses caching."""
        ai_mentor = BanditAIMentor()
        
        # Mock the cache to track calls
        with patch('ai_mentor.cache') as mock_cache:
            mock_cache.get.return_value = None  # Not in cache initially
            
            # Call explain_command
            result1 = ai_mentor.explain_command("ls")
            
            # Check that cache.get was called
            mock_cache.get.assert_called_with("command_explanation_ls")
            
            # Check that cache.set was called to store the result
            mock_cache.set.assert_called_with("command_explanation_ls", result1, ttl=3600)
            
            # Call again to verify it uses cache
            mock_cache.get.return_value = result1  # Now in cache
            result2 = ai_mentor.explain_command("ls")
            
            # Check that the same result is returned
            assert result1 == result2
            # Check that cache.get was called again
            assert mock_cache.get.call_count == 2