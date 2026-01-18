"""Unit tests for the BanditAIMentor class."""

import json
import os
import sys
import tempfile
from unittest.mock import MagicMock, Mock, patch

# Add the src directory to the path so we can import the modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from ai_mentor import BanditAIMentor


class TestBanditAIMentor:
    """Test cases for the BanditAIMentor class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.mock_notify = Mock()
        self.temp_dir = tempfile.mkdtemp()
        self.test_data_file = os.path.join(self.temp_dir, "test_ai_mentor_data.json")

        # Create test data
        self.test_data = {
            "level_hints": {
                "0": "For level 0, try using SSH to connect to the server.",
                "1": "For level 1, look for files in the current directory.",
            },
            "command_explanations": {
                "ls": "List directory contents",
                "cat": "Display file contents",
                "ssh": "Secure shell connection",
            },
        }

        with open(self.test_data_file, "w") as f:
            json.dump(self.test_data, f)

    def teardown_method(self):
        """Clean up after each test method."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_init_default(self):
        """Test BanditAIMentor initialization with default parameters."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
            mentor = BanditAIMentor(self.mock_notify)

            assert mentor.notify == self.mock_notify
            assert mentor.data_file_path == "ai_mentor_data.json"
            assert mentor.level_hints is not None
            assert mentor.command_explanations is not None
            assert mentor.conversation_history == {}
            assert mentor.system_prompt is not None

    def test_init_custom_params(self):
        """Test BanditAIMentor initialization with custom parameters."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
            mentor = BanditAIMentor(
                notify_callback=self.mock_notify,
                model="gpt-4",
                data_file_path=self.test_data_file,
                opt_out=False,
            )

            assert mentor.model == "gpt-4"
            assert mentor.data_file_path == self.test_data_file

    def test_init_opt_out(self):
        """Test BanditAIMentor initialization with opt-out."""
        mentor = BanditAIMentor(notify_callback=self.mock_notify, opt_out=True)

        assert mentor.opt_out is True
        assert mentor.disabled is True
        self.mock_notify.assert_called_with(
            "AI mentor disabled: AI mentor disabled by user opt-out for privacy", "warning"
        )

    def test_init_no_api_key(self):
        """Test BanditAIMentor initialization without API key."""
        with patch.dict(os.environ, {}, clear=True):
            mentor = BanditAIMentor(self.mock_notify)

            assert mentor.disabled is True
            self.mock_notify.assert_called_with(
                "AI mentor disabled: OpenAI API key not found", "warning"
            )

    def test_init_no_litellm(self):
        """Test BanditAIMentor initialization without LiteLLM."""
        with patch("src.ai_mentor.LITELLM_AVAILABLE", False):
            with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
                mentor = BanditAIMentor(self.mock_notify)

                assert mentor.disabled is True
                self.mock_notify.assert_called_with(
                    "AI mentor disabled: LiteLLM not installed", "warning"
                )

    def test_load_data_success(self):
        """Test successful loading of AI mentor data."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
            mentor = BanditAIMentor(
                notify_callback=self.mock_notify, data_file_path=self.test_data_file
            )

            assert mentor.level_hints == self.test_data["level_hints"]
            assert mentor.command_explanations == self.test_data["command_explanations"]

    def test_load_data_file_not_found(self):
        """Test loading AI mentor data when file doesn't exist."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
            mentor = BanditAIMentor(
                notify_callback=self.mock_notify, data_file_path="nonexistent.json"
            )

            assert mentor.level_hints == {}
            assert mentor.command_explanations == {}
            self.mock_notify.assert_called()

    def test_load_data_invalid_json(self):
        """Test loading AI mentor data with invalid JSON."""
        invalid_file = os.path.join(self.temp_dir, "invalid.json")
        with open(invalid_file, "w") as f:
            f.write("invalid json content")

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
            mentor = BanditAIMentor(notify_callback=self.mock_notify, data_file_path=invalid_file)

            assert mentor.level_hints == {}
            assert mentor.command_explanations == {}
            self.mock_notify.assert_called()

    def test_trim_conversation_history(self):
        """Test trimming conversation history."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
            mentor = BanditAIMentor(self.mock_notify)

            # Add more than max_history messages
            session_id = "test_session"
            mentor.conversation_history[session_id] = [
                {"role": "user", "content": f"Message {i}"} for i in range(15)
            ]

            mentor._trim_conversation_history(session_id, max_history=10)

            # Should keep only the last 10 messages
            assert len(mentor.conversation_history[session_id]) == 10
            assert mentor.conversation_history[session_id][0]["content"] == "Message 5"

    def test_trim_conversation_history_no_session(self):
        """Test trimming conversation history for non-existent session."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
            mentor = BanditAIMentor(self.mock_notify)

            # Should not raise error for non-existent session
            mentor._trim_conversation_history("nonexistent_session")

    @patch("src.ai_mentor.litellm.completion")
    def test_get_response_success(self, mock_completion):
        """Test successful AI response generation."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Test AI response"
        mock_completion.return_value = mock_response

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
            mentor = BanditAIMentor(self.mock_notify)

            response_chunks = list(
                mentor.get_response(
                    user_message="Test message", session_id="test_session", current_level=0
                )
            )

            assert response_chunks == ["Test AI response"]
            mock_completion.assert_called_once()

    @patch("src.ai_mentor.litellm.completion")
    def test_get_response_streaming(self, mock_completion):
        """Test AI response generation with streaming."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Test AI response"
        mock_completion.return_value = mock_response

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
            mentor = BanditAIMentor(self.mock_notify)

            response_chunks = list(
                mentor.get_response(
                    user_message="Test message",
                    session_id="test_session",
                    current_level=0,
                    stream=True,
                )
            )

            # Should stream character by character
            assert response_chunks == list("Test AI response")

    def test_get_response_disabled_opt_out(self):
        """Test AI response generation when disabled due to opt-out."""
        mentor = BanditAIMentor(notify_callback=self.mock_notify, opt_out=True)

        response_chunks = list(
            mentor.get_response(
                user_message="Test message", session_id="test_session", current_level=0
            )
        )

        assert response_chunks == [
            "AI mentor is disabled due to privacy opt-out. You can enable it in settings if you want AI assistance."
        ]

    def test_get_response_disabled_no_api_key(self):
        """Test AI response generation when disabled due to no API key."""
        with patch.dict(os.environ, {}, clear=True):
            mentor = BanditAIMentor(self.mock_notify)

            response_chunks = list(
                mentor.get_response(
                    user_message="Test message", session_id="test_session", current_level=0
                )
            )

            assert response_chunks == [
                "AI mentor is currently disabled. Please set your OpenAI API key in the .env file to enable this feature."
            ]

    @patch("src.ai_mentor.litellm.completion")
    def test_get_response_with_cache(self, mock_completion):
        """Test AI response generation with caching."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Test AI response"
        mock_completion.return_value = mock_response

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
            mentor = BanditAIMentor(self.mock_notify)

            # First call
            response_chunks1 = list(
                mentor.get_response(
                    user_message="Test message", session_id="test_session", current_level=0
                )
            )

            # Second call should use cache
            response_chunks2 = list(
                mentor.get_response(
                    user_message="Test message", session_id="test_session", current_level=0
                )
            )

            assert response_chunks1 == response_chunks2
            # litellm should only be called once (first time)
            assert mock_completion.call_count == 1

    @patch("src.ai_mentor.litellm.completion")
    def test_get_response_api_error(self, mock_completion):
        """Test AI response generation with API error."""
        mock_completion.side_effect = Exception("API Error")

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
            mentor = BanditAIMentor(self.mock_notify)

            response_chunks = list(
                mentor.get_response(
                    user_message="Test message", session_id="test_session", current_level=0
                )
            )

            # Should return fallback response
            assert len(response_chunks) > 0
            assert any("error" in chunk.lower() for chunk in response_chunks)

    @patch("src.ai_mentor.litellm.completion")
    def test_get_response_with_context(self, mock_completion):
        """Test AI response generation with full context."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Contextual response"
        mock_completion.return_value = mock_response

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
            mentor = BanditAIMentor(self.mock_notify)

            response_chunks = list(
                mentor.get_response(
                    user_message="Test message",
                    session_id="test_session",
                    current_level=5,
                    recent_commands=["ls", "cat file.txt"],
                    terminal_output="file content here",
                )
            )

            assert response_chunks == ["Contextual response"]

            # Verify the call included context
            call_args = mock_completion.call_args
            messages = call_args[1]["messages"]

            # Should include system prompt and user message with context
            assert len(messages) >= 2
            assert any("level 5" in str(msg).lower() for msg in messages)
            assert any("ls" in str(msg) for msg in messages)
            assert any("file content here" in str(msg) for msg in messages)

    @patch("src.ai_mentor.litellm.completion")
    def test_get_response_conversation_history(self, mock_completion):
        """Test AI response generation maintains conversation history."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Response 1"
        mock_completion.return_value = mock_response

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
            mentor = BanditAIMentor(self.mock_notify)

            # First message
            list(
                mentor.get_response(
                    user_message="First message", session_id="test_session", current_level=0
                )
            )

            # Second message - should include conversation history
            mock_response.choices[0].message.content = "Response 2"
            response_chunks = list(
                mentor.get_response(
                    user_message="Second message", session_id="test_session", current_level=0
                )
            )

            assert response_chunks == ["Response 2"]

            # Verify conversation history was included
            call_args = mock_completion.call_args
            messages = call_args[1]["messages"]

            # Should have system prompt, first user message, first response, second user message
            assert len(messages) >= 4

    def test_get_level_hint(self):
        """Test getting level hint."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
            mentor = BanditAIMentor(
                notify_callback=self.mock_notify, data_file_path=self.test_data_file
            )

            hint = mentor.get_level_hint(0)
            assert hint == self.test_data["level_hints"]["0"]

    def test_get_level_hint_not_found(self):
        """Test getting level hint for non-existent level."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
            mentor = BanditAIMentor(
                notify_callback=self.mock_notify, data_file_path=self.test_data_file
            )

            hint = mentor.get_level_hint(999)
            assert (
                hint
                == "Think about what the level description is asking you to find or do. Break down the problem into smaller steps."
            )

    def test_explain_command(self):
        """Test getting command explanation."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
            mentor = BanditAIMentor(
                notify_callback=self.mock_notify, data_file_path=self.test_data_file
            )

            explanation = mentor.explain_command("ls")
            assert explanation == self.test_data["command_explanations"]["ls"]

    def test_explain_command_not_found(self):
        """Test getting command explanation for non-existent command."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
            mentor = BanditAIMentor(
                notify_callback=self.mock_notify, data_file_path=self.test_data_file
            )

            explanation = mentor.explain_command("nonexistent")
            assert (
                explanation
                == "For information about 'nonexistent', try using 'man nonexistent' or 'nonexistent --help' to learn about its usage and options."
            )

    def test_clear_cache(self):
        """Test clearing AI mentor cache."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
            mentor = BanditAIMentor(self.mock_notify)

            mentor.clear_cache()

            self.mock_notify.assert_called_with("AI mentor cache cleared", severity="info")

    def test_get_context_suggestions(self):
        """Test getting context-aware suggestions."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
            mentor = BanditAIMentor(self.mock_notify)

            suggestions = mentor.get_context_suggestions(
                terminal_output="command not found: xyz", recent_commands=["xyz", "ls"]
            )

            assert len(suggestions) > 0
            assert any("spelling" in suggestion.lower() for suggestion in suggestions)

    def test_get_context_suggestions_no_errors(self):
        """Test getting context suggestions with no errors."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
            mentor = BanditAIMentor(self.mock_notify)

            suggestions = mentor.get_context_suggestions(
                terminal_output="normal output", recent_commands=["ls", "pwd"]
            )

            assert suggestions == []

    def test_get_cache_stats(self):
        """Test getting cache statistics."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
            mentor = BanditAIMentor(self.mock_notify)

            stats = mentor.get_cache_stats()

            assert isinstance(stats, dict)

    @patch("src.ai_mentor.litellm.completion")
    def test_get_response_with_context_suggestions(self, mock_completion):
        """Test getting AI response with context suggestions."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Base response"
        mock_completion.return_value = mock_response

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
            mentor = BanditAIMentor(self.mock_notify)

            response = mentor.get_response_with_context(
                level=0,
                question="Test question",
                terminal_output="command not found",
                recent_commands=["wrongcommand"],
            )

            assert "Base response" in response
            assert "Context-Aware Suggestions" in response

    def test_get_response_quality_stats(self):
        """Test getting response quality statistics."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
            mentor = BanditAIMentor(self.mock_notify)

            stats = mentor.get_response_quality_stats()

            assert isinstance(stats, dict)

    @patch("src.ai_mentor.importlib.resources.open_text")
    def test_load_data_from_package_resources(self, mock_open_text):
        """Test loading AI mentor data from package resources."""
        mock_file = MagicMock()
        mock_file.__enter__.return_value = mock_file
        mock_file.read.return_value = json.dumps(self.test_data)
        mock_open_text.return_value = mock_file

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
            mentor = BanditAIMentor(
                notify_callback=self.mock_notify, data_file_path="test_data.json"
            )

            assert mentor.level_hints == self.test_data["level_hints"]
            assert mentor.command_explanations == self.test_data["command_explanations"]
            mock_open_text.assert_called_once_with("src", "test_data.json")

    def test_data_privacy_notice_in_docstring(self):
        """Test that data privacy notice is documented in get_response method."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
            mentor = BanditAIMentor(self.mock_notify)

            # Check that the method docstring contains privacy notice
            docstring = mentor.get_response.__doc__
            assert "Data Privacy Notice" in docstring
            assert "OpenAI API" in docstring

    @patch("src.ai_mentor.litellm.completion")
    def test_response_with_truncated_terminal_output(self, mock_completion):
        """Test that terminal output is properly truncated."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Response"
        mock_completion.return_value = mock_response

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
            mentor = BanditAIMentor(self.mock_notify)

            # Use very long terminal output
            long_output = "x" * 1000
            list(
                mentor.get_response(
                    user_message="Test message",
                    session_id="test_session",
                    current_level=0,
                    terminal_output=long_output,
                )
            )

            # Verify the call included truncated output
            call_args = mock_completion.call_args
            messages = call_args[1]["messages"]

            # Should truncate to 500 characters
            terminal_content = str(messages)
            assert len(terminal_content) < len(long_output) + 100  # Allow for other content
