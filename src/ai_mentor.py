"""AI mentor module for BanditCLI.

This module provides AI-powered mentoring capabilities for the OverTheWire Bandit
wargame using LiteLLM for flexible model support. It includes educational guidance,
hint provision, and command explanations while maintaining conversation context.

The BanditAIMentor class handles AI interactions with proper educational constraints,
ensuring users learn concepts rather than receiving direct solutions.
"""
# src/ai_mentor.py
import importlib.resources
import json
import os
from typing import Callable, Dict, Generator, List, Optional, Any

from src.cache import Cache

try:
    import litellm
    LITELLM_AVAILABLE = True
except ImportError:
    LITELLM_AVAILABLE = False

# Import ConfigManager for configuration management
try:
    from src.config import ConfigManager
except ImportError:
    ConfigManager = None
class BanditAIMentor:
    """AI-powered mentor for Bandit wargame educational guidance.

    This class provides AI mentoring capabilities for the OverTheWire Bandit
    wargame, offering educational guidance, hints, and command explanations.
    It uses LiteLLM for flexible model support and maintains conversation
    history for context-aware responses.

    The mentor is designed to teach concepts rather than provide direct solutions,
    following educational best practices for cybersecurity learning.

    Attributes:
        notify (Callable[[str, str], None]): Callback for status notifications.
        model (str): The AI model to use for responses.
        data_file_path (str): Path to the JSON data file for hints and explanations.
        level_hints (Dict[str, str]): Predefined hints for each level.
        command_explanations (Dict[str, str]): Educational explanations for commands.
        disabled (bool): Flag indicating if AI mentor is disabled.
        conversation_history (Dict[str, List[Dict[str, str]]]): Session conversation history.
        system_prompt (str): System prompt defining AI mentor behavior and constraints.
    """
    def __init__(self, notify_callback: Callable[[str, str], None],
                 model: Optional[str] = None, data_file_path: str = "ai_mentor_data.json",
                 config: Optional['ConfigManager'] = None, opt_out: bool = False) -> None:
        """Initialize AI mentor with notification callback and configuration.

        Args:
            notify_callback: Callback for status/error notifications.
            model: The AI model to use (overrides config if provided).
            data_file_path: Path to JSON file containing level hints and command explanations.
            config: ConfigManager instance for accessing configuration settings.
            opt_out: Whether to opt out of AI features for privacy.
        """
        self.notify = notify_callback
        self.model: str = model or (config.get('ai.model') if config else os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"))
        self.data_file_path: str = data_file_path
        self.level_hints: Dict[str, str] = {}
        self.command_explanations: Dict[str, str] = {}
        self.opt_out = opt_out
        self.cache = Cache(cache_dir=None, default_ttl=3600)  # 1 hour TTL for AI responses
        self._load_data()

        # Check if AI is available and not opted out
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

        # LiteLLM can handle different providers, so we don't need a specific client instance.
        # We can check for a general API key, but since we are defaulting to a local model,
        # we might not need one. For now, we'll assume that if a user wants to use a
        # different model, they will set the appropriate environment variables.
        self.conversation_history: Dict[str, List[Dict[str, str]]] = {}

        # System prompt for the AI mentor
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

Remember: Your goal is to teach and guide, not to solve problems for the user. Help them become better problem solvers and Linux users."""

    def _load_data(self) -> None:
        """Load level hints and command explanations from JSON data file.

        Attempts to load the JSON data file containing predefined level hints
        and command explanations. Handles file not found and JSON decode errors
        gracefully by initializing empty dictionaries.
        """
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
        """Trim the conversation history to the specified maximum length.

        Args:
            session_id: The session identifier
            max_history: Maximum number of messages to keep in history
        """
        if session_id in self.conversation_history:
            history = self.conversation_history[session_id]
            if len(history) > max_history:
                # Keep the system prompt and the most recent messages
                self.conversation_history[session_id] = history[-max_history:]

    def get_response(self, user_message: str, session_id: str = "default",
                    current_level: int = 0, recent_commands: Optional[List[str]] = None,
                    terminal_output: str = "", stream: bool = True) -> Generator[str, None, None]:
        """Generate AI mentor response with context awareness and caching.

        Creates an educational response based on the user's message, current level,
        recent commands, and terminal output. Uses streaming for real-time response
        delivery and maintains conversation history for context. Implements caching
        to improve performance for repeated questions.

        **Data Privacy Notice**: The following data may be sent to OpenAI API:
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

        Note:
            If AI is disabled, returns a message indicating the disabled status.
            Handles API errors gracefully with fallback responses.
        """
        # If AI is disabled, return a default message
        if self.disabled:
            if self.opt_out:
                yield "AI mentor is disabled due to privacy opt-out. You can enable it in settings if you want AI assistance."
            else:
                yield "AI mentor is currently disabled. Please set your OpenAI API key in the .env file to enable this feature."
            return
        
        # Check cache first
        cache_key = self.cache.generate_hash_key(current_level, user_message)
        cached_response = self.cache.get(cache_key)
        if cached_response is not None:
            self.notify("AI response loaded from cache", severity="info")
            if stream:
                for char in cached_response:
                    yield char
            else:
                yield cached_response
            return

        try:
            # Initialize conversation history for new sessions
            if session_id not in self.conversation_history:
                self.conversation_history[session_id] = []

            # Build context message
            context_parts = []
            if current_level is not None:
                context_parts.append(f"Current level: Bandit Level {current_level}")

            if recent_commands:
                context_parts.append(f"Recent commands: {', '.join(recent_commands[-5:])}")

            if terminal_output:
                # Limit terminal output to avoid token limits
                limited_output = terminal_output[-500:] if len(terminal_output) > 500 else terminal_output
                context_parts.append(f"Recent terminal output: {limited_output}")

            context_message = "\n".join(context_parts) if context_parts else ""

            # Prepare messages for the API
            messages = [{"role": "system", "content": self.system_prompt}]

            # Add conversation history (already trimmed to max length)
            messages.extend(self.conversation_history[session_id])

            # Add context if available
            if context_message:
                messages.append({
                    "role": "system",
                    "content": f"Current context: {context_message}"
                })

            # Add user message
            messages.append({"role": "user", "content": user_message})

            # Generate response with error handling
            try:
                stream_response = litellm.completion(
                    model=self.model,
                    messages=messages,
                    max_tokens=500,
                    temperature=0.7,
                    stream=True,
                    timeout=30  # Add timeout
                )

                full_response = ""
                for chunk in stream_response:
                    content = chunk.choices[0].delta.content or ""
                    if content:  # Only yield non-empty content
                        full_response += content
                        yield content

                # Cache the complete response
                self.cache.set(cache_key, full_response, ttl=3600)  # Cache for 1 hour

                # Update conversation history
                self.conversation_history[session_id].extend([
                    {"role": "user", "content": user_message},
                    {"role": "assistant", "content": full_response}
                ])

                # Trim conversation history to prevent unbounded growth
                self._trim_conversation_history(session_id)

                # Update response quality tracking
                self.response_quality['total_responses'] += 1
                self.response_quality['successful_responses'] += 1

            except Exception as api_error:
                self.notify(f"AI API Error: {api_error}", "error")
                yield "I'm sorry, there was an error with the AI service. Please try again later."

                # Update response quality tracking
                self.response_quality['total_responses'] += 1
                self.response_quality['failed_responses'] += 1

        except Exception as e:
            self.notify(f"Error generating AI response: {e}", "error")
            yield "I'm sorry, I'm having trouble responding right now. Please try again later."

    def clear_conversation(self, session_id: str = "default") -> None:
        """Clear conversation history for a specific session.

        Removes the conversation history for the given session ID,
        effectively starting a fresh conversation.

        Args:
            session_id: The session identifier to clear (default: "default").
        """
        if session_id in self.conversation_history:
            del self.conversation_history[session_id]

    def get_level_hint(self, level_num: int) -> str:
        """Get a general educational hint for a specific level.

        Provides a predefined hint for the specified level that guides
        learning without revealing direct solutions or spoilers.

        Args:
            level_num: The Bandit level number.

        Returns:
            str: Educational hint for the level, or a general hint if none is defined.
        """
        return self.level_hints.get(str(level_num),
            "Think about what the level description is asking you to find or do. Break down the problem into smaller steps.")

    def explain_command(self, command: str) -> str:
        """Provide educational explanation for a Linux command.

        Returns a predefined educational explanation for the given command,
        focusing on its purpose and general usage rather than specific
        applications that might spoil level solutions.

        Args:
            command: The Linux command to explain.

        Returns:
            str: Educational explanation of the command, or a general suggestion
            to check the manual page if no specific explanation is available.
        """
        return self.command_explanations.get(command,
            f"For information about '{command}', try using 'man {command}' or '{command} --help' to learn about its usage and options.")
    def clear_cache(self) -> None:
        """Clear all AI mentor cache entries."""
        self.cache.clear()
        self.notify("AI mentor cache cleared", severity="info")
    
    def get_context_suggestions(self, terminal_output: str, recent_commands: List[str]) -> List[str]:
        """Generate context-aware suggestions based on terminal errors.
        
        Args:
            terminal_output: Recent terminal output to analyze
            recent_commands: List of recent commands
            
        Returns:
            List[str]: Context-aware suggestions
        """
        suggestions = []
        
        # Check for common error patterns
        error_patterns = {
            r'command not found': 'Try checking command spelling or use `which` to verify path',
            r'permission denied': 'Consider using `sudo` or check file permissions with `ls -la`',
            r'no such file': 'Verify file path exists with `ls` or use `find` to locate',
            r'connection refused': 'Check if service is running and port is accessible',
            r'authentication failed': 'Verify credentials or check SSH key permissions'
        }
        
        for pattern, suggestion in error_patterns.items():
            if pattern.lower() in terminal_output.lower():
                suggestions.append(suggestion)
        
        return suggestions
    
    def get_cache_stats(self) -> Dict:
        """Get AI mentor cache statistics."""
        return self.cache.get_stats()
    
    def get_response_with_context(self, level: int, question: str, terminal_output: str = "", recent_commands: List[str] = None) -> str:
        """Get AI response with context-aware suggestions.
        
        Args:
            level: Current Bandit level
            question: User's question
            terminal_output: Recent terminal output for context
            recent_commands: List of recent commands
            
        Returns:
            str: AI response with context suggestions
        """
        # Get base response
        response = self.get_response(level, question)
        
        # Add context suggestions if terminal output is provided
        if terminal_output and recent_commands is not None:
            suggestions = self.get_context_suggestions(terminal_output, recent_commands)
            if suggestions:
                response += "\n\n**Context-Aware Suggestions:**\n"
                for suggestion in suggestions:
                    response += f"- {suggestion}\n"
        
        return response
    
    def get_response_quality_stats(self) -> Dict:
        """Get response quality statistics.
        
        Returns:
            Dict: Quality metrics including success rate and response times
        """
        total = self.response_quality['total_responses']
        if total == 0:
            return {
                'success_rate': 0.0,
                'total_responses': 0,
                'successful_responses': 0,
                'failed_responses': 0,
                'avg_response_time': 0.0
            }
        
        success_rate = (self.response_quality['successful_responses'] / total) * 100
        
        return {
            'success_rate': round(success_rate, 2),
            'total_responses': total,
            'successful_responses': self.response_quality['successful_responses'],
            'failed_responses': self.response_quality['failed_responses'],
            'avg_response_time': self.response_quality['avg_response_time']
        }
    
    def get_enhanced_response_with_quality(self, level: int, question: str, terminal_output: str = "", recent_commands: List[str] = None) -> Dict[str, Any]:
        """Get AI response with quality indicators.
        
        Args:
            level: Current Bandit level
            question: User's question
            terminal_output: Recent terminal output for context
            recent_commands: List of recent commands
            
        Returns:
            Dict: Response with quality metrics
        """
        import time
        start_time = time.time()
        
        try:
            # Get base response
            response = self.get_response(level, question)
            
            # Calculate response time
            response_time = time.time() - start_time
            
            # Determine confidence based on response characteristics
            confidence = self._calculate_confidence(response, question)
            
            # Determine relevance based on context matching
            relevance = self._calculate_relevance(response, level, question)
            
            # Add context suggestions if terminal output is provided
            if terminal_output and recent_commands is not None:
                suggestions = self.get_context_suggestions(terminal_output, recent_commands)
                if suggestions:
                    response += "\n\n**Context-Aware Suggestions:**\n"
                    for suggestion in suggestions:
                        response += f"- {suggestion}\n"
            
            return {
                'response': response,
                'confidence': confidence,
                'relevance': relevance,
                'response_time': round(response_time, 2),
                'has_context_suggestions': bool(terminal_output and recent_commands)
            }
            
        except Exception as e:
            return {
                'response': f"Error generating response: {e}",
                'confidence': 0.0,
                'relevance': 0.0,
                'response_time': 0.0,
                'has_context_suggestions': False,
                'error': str(e)
            }
    
    def _calculate_confidence(self, response: str, question: str) -> float:
        """Calculate confidence score for AI response.
        
        Args:
            response: The AI response
            question: The original question
            
        Returns:
            float: Confidence score (0.0 to 1.0)
        """
        if not response or not question:
            return 0.0
        
        # Basic confidence metrics
        response_length = len(response)
        question_length = len(question)
        
        # Response should be substantial but not too long
        length_score = 0.0
        if 50 <= response_length <= 1000:
            length_score = 1.0
        elif response_length < 50:
            length_score = 0.3
        else:
            length_score = 0.7
        
        # Check for educational content indicators
        educational_keywords = ['explain', 'learn', 'understand', 'concept', 'command', 'hint', 'suggest']
        educational_score = sum(1 for keyword in educational_keywords if keyword in response.lower()) / len(educational_keywords)
        
        # Avoid direct solution indicators
        solution_keywords = ['password', 'answer', 'solution', 'exact command']
        solution_penalty = sum(1 for keyword in solution_keywords if keyword in response.lower()) / len(solution_keywords)
        
        # Calculate final confidence
        confidence = (length_score * 0.4) + (educational_score * 0.4) - (solution_penalty * 0.2)
        return max(0.0, min(1.0, confidence))
    
    def _calculate_relevance(self, response: str, level: int, question: str) -> float:
        """Calculate relevance score for AI response.
        
        Args:
            response: The AI response
            level: Current Bandit level
            question: The original question
            
        Returns:
            float: Relevance score (0.0 to 1.0)
        """
        if not response:
            return 0.0
        
        # Check if response mentions relevant concepts
        level_relevance = 1.0 if f"level {level}" in response.lower() or f"bandit {level}" in response.lower() else 0.5
        
        # Check if response addresses the question topic
        question_words = set(question.lower().split())
        response_words = set(response.lower().split())
        word_overlap = len(question_words.intersection(response_words)) / max(len(question_words), 1)
        
        # Calculate final relevance
        relevance = (level_relevance * 0.6) + (word_overlap * 0.4)
        return max(0.0, min(1.0, relevance))
