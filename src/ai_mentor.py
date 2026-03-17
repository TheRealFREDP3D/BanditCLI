"""AI mentor module for BanditCLI.

This module provides AI-powered mentoring capabilities for the OverTheWire Bandit
wargame using LiteLLM for flexible model support. It includes educational guidance,
hint provision, and command explanations while maintaining conversation context.
"""

import importlib.resources
import json
import os
from collections.abc import Generator
from typing import TYPE_CHECKING, Callable, Optional

from .cache import Cache

try:
    import litellm

    LITELLM_AVAILABLE = True
except ImportError:
    LITELLM_AVAILABLE = False

if TYPE_CHECKING:
    from .config import ConfigManager


class BanditAIMentor:
    """AI-powered mentor for Bandit wargame educational guidance.

    Attributes:
        notify (Callable[[str, str], None]): Callback for status notifications.
        model (str): The AI model to use for responses.
        level_hints (Dict[str, str]): Predefined hints for each level.
        command_explanations (Dict[str, str]): Educational explanations for commands.
        disabled (bool): Whether AI mentor is currently disabled.
        conversation_history (Dict[str, List[Dict[str, str]]]): Session conversation history.
        system_prompt (str): System prompt defining AI mentor behaviour.
    """

    def __init__(
        self,
        notify_callback: Callable[[str, str], None],
        model: Optional[str] = None,
        data_file_path: str = "ai_mentor_data.json",
        config: Optional["ConfigManager"] = None,
        opt_out: bool = False,
    ) -> None:
        """Initialize AI mentor.

        Args:
            notify_callback: Callback for status/error notifications.
            model: The AI model to use (overrides config if provided).
            data_file_path: Path to JSON file with level hints and command explanations.
            config: ConfigManager instance for configuration settings.
            opt_out: Whether to opt out of AI features for privacy.
        """
        self.notify = notify_callback
        self.model: str = model or (
            config.get("ai.model") if config else os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
        )
        self.data_file_path: str = data_file_path
        self.level_hints: dict[str, str] = {}
        self.command_explanations: dict[str, str] = {}
        self.opt_out = opt_out
        self.cache = Cache(cache_dir=None, default_ttl=3600)
        self._load_data()

        api_key = os.getenv("OPENAI_API_KEY")
        self.disabled = any([self.opt_out, not LITELLM_AVAILABLE, not api_key])

        if self.disabled:
            if self.opt_out:
                reason = "AI mentor disabled by user opt-out for privacy"
            elif not LITELLM_AVAILABLE:
                reason = "LiteLLM not installed"
            else:
                reason = "OpenAI API key not found"
            self.notify(f"AI mentor disabled: {reason}", "warning")

        self.conversation_history: dict[str, list[dict[str, str]]] = {}

        self.system_prompt = """You are an AI mentor for the OverTheWire Bandit wargame, designed to help beginners learn cybersecurity and Linux command line skills. Your role is to provide guidance, hints, and educational context WITHOUT giving direct solutions.

IMPORTANT RULES:
1. NEVER provide the exact commands or solutions that solve the level
2. NEVER reveal passwords or direct answers
3. Instead, guide users toward understanding concepts and discovering solutions themselves
4. Provide hints about what to look for or what concepts to research
5. Explain relevant Linux commands and their purposes in general terms
6. Encourage experimentation and learning from mistakes
7. Ask leading questions that help users think through problems
8. Provide context about cybersecurity concepts when relevant

RESPONSE STYLE:
- Be encouraging and supportive
- Use a friendly, mentor-like tone
- Break down complex concepts into digestible pieces
- Provide examples of command usage in general contexts (not specific to the current level)
- Reference learning materials and documentation when helpful

CONTEXT AWARENESS:
- Pay attention to the current level the user is working on
- Consider their recent terminal commands and output
- Adapt explanations to their apparent skill level
- Build on previous conversations and learning progress

Remember: Your goal is to teach and guide, not to solve problems for the user."""

    def _load_data(self) -> None:
        """Load level hints and command explanations from JSON data file."""
        try:
            with importlib.resources.open_text("src", self.data_file_path) as f:
                data = json.load(f)
                self.level_hints = data.get("level_hints", {})
                self.command_explanations = data.get("command_explanations", {})
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self.notify(f"Error loading AI mentor data: {e}", "error")
            self.level_hints = {}
            self.command_explanations = {}

    def _trim_conversation_history(self, session_id: str, max_history: int = 10) -> None:
        """Trim conversation history to the specified maximum length.

        Args:
            session_id: The session identifier.
            max_history: Maximum number of messages to keep.
        """
        if session_id in self.conversation_history:
            history = self.conversation_history[session_id]
            if len(history) > max_history:
                self.conversation_history[session_id] = history[-max_history:]

    def get_response(
        self,
        user_message: str,
        session_id: str = "default",
        current_level: int = 0,
        recent_commands: Optional[list[str]] = None,
        terminal_output: str = "",
        stream: bool = True,
    ) -> Generator[str, None, None]:
        """Generate AI mentor response with context awareness and caching.

        **Data Privacy Notice**: The following data may be sent to the OpenAI API:
        - User messages and conversation history
        - Current Bandit level number
        - Last 5 commands entered by the user (if recent_commands provided)
        - Last 500 characters of terminal output (if terminal_output provided)

        Args:
            user_message: The user's question or message.
            session_id: Session identifier for conversation history tracking.
            current_level: Current Bandit level number.
            recent_commands: List of recently executed commands for context.
            terminal_output: Recent terminal output for additional context.
            stream: Whether to stream the response (default: True).

        Yields:
            str: Response chunks from the AI model.
        """
        if self.disabled:
            if self.opt_out:
                yield "AI mentor is disabled due to privacy opt-out. You can enable it in settings if you want AI assistance."
            else:
                yield "AI mentor is currently disabled. Please set your OpenAI API key in the .env file to enable this feature."
            return

        cache_key = self.cache.generate_hash_key(current_level, user_message)
        cached_response = self.cache.get(cache_key)
        if cached_response is not None:
            self.notify("AI response loaded from cache", "info")
            yield cached_response
            return

        try:
            if session_id not in self.conversation_history:
                self.conversation_history[session_id] = []

            context_parts = []
            if current_level is not None:
                context_parts.append(f"Current level: Bandit Level {current_level}")

            if recent_commands:
                context_parts.append(f"Recent commands: {', '.join(recent_commands[-5:])}")

            if terminal_output:
                limited_output = (
                    terminal_output[-500:] if len(terminal_output) > 500 else terminal_output
                )
                context_parts.append(f"Recent terminal output: {limited_output}")

            context_message = "\n".join(context_parts) if context_parts else ""

            messages = [{"role": "system", "content": self.system_prompt}]
            messages.extend(self.conversation_history[session_id])

            if context_message:
                messages.append(
                    {"role": "system", "content": f"Current context: {context_message}"}
                )

            messages.append({"role": "user", "content": user_message})

            try:
                stream_response = litellm.completion(  # type: ignore[union-attr]
                    model=self.model,
                    messages=messages,
                    max_tokens=500,
                    temperature=0.7,
                    stream=True,
                    timeout=30,
                )

                full_response = ""
                for chunk in stream_response:
                    content = chunk.choices[0].delta.content or ""  # type: ignore[union-attr]
                    if content:
                        full_response += content
                        yield content

                self.cache.set(cache_key, full_response, ttl=3600)

                self.conversation_history[session_id].extend(
                    [
                        {"role": "user", "content": user_message},
                        {"role": "assistant", "content": full_response},
                    ]
                )
                self._trim_conversation_history(session_id)

            except Exception as api_error:
                self.notify(f"AI API Error: {api_error}", "error")
                yield "I'm sorry, there was an error with the AI service. Please try again later."

        except Exception as e:
            self.notify(f"Error generating AI response: {e}", "error")
            yield "I'm sorry, I'm having trouble responding right now. Please try again later."

    def clear_conversation(self, session_id: str = "default") -> None:
        """Clear conversation history for a specific session.

        Args:
            session_id: The session identifier to clear (default: "default").
        """
        if session_id in self.conversation_history:
            del self.conversation_history[session_id]

    def get_level_hint(self, level_num: int) -> str:
        """Get a general educational hint for a specific level.

        Args:
            level_num: The Bandit level number.

        Returns:
            str: Educational hint for the level.
        """
        return self.level_hints.get(
            str(level_num),
            "Think about what the level description is asking you to find or do. Break down the problem into smaller steps.",
        )

    def explain_command(self, command: str) -> str:
        """Provide educational explanation for a Linux command.

        Args:
            command: The Linux command to explain.

        Returns:
            str: Educational explanation of the command.
        """
        return self.command_explanations.get(
            command,
            f"For information about '{command}', try using 'man {command}' or '{command} --help' to learn about its usage and options.",
        )

    def clear_cache(self) -> None:
        """Clear all AI mentor cache entries."""
        self.cache.clear()
        self.notify("AI mentor cache cleared", "info")

    def get_context_suggestions(
        self, terminal_output: str, recent_commands: list[str]
    ) -> list[str]:
        """Generate context-aware suggestions based on terminal errors.

        Args:
            terminal_output: Recent terminal output to analyse.
            recent_commands: List of recent commands.

        Returns:
            List[str]: Context-aware suggestions.
        """
        suggestions = []

        error_patterns = {
            r"command not found": "Try checking command spelling or use `which` to verify path",
            r"permission denied": "Consider using `sudo` or check file permissions with `ls -la`",
            r"no such file": "Verify file path exists with `ls` or use `find` to locate",
            r"connection refused": "Check if service is running and port is accessible",
            r"authentication failed": "Verify credentials or check SSH key permissions",
        }

        for pattern, suggestion in error_patterns.items():
            if pattern.lower() in terminal_output.lower():
                suggestions.append(suggestion)

        return suggestions

    def get_cache_stats(self) -> dict:
        """Get AI mentor cache statistics."""
        return self.cache.get_stats()
