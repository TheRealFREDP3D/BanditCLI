"""AI mentor module for BanditCLI.

This module provides AI-powered mentoring capabilities for the OverTheWire Bandit
wargame using LiteLLM for flexible model support. It includes educational guidance,
hint provision, and command explanations while maintaining conversation context.

The BanditAIMentor class handles AI interactions with proper educational constraints,
ensuring users learn concepts rather than receiving direct solutions.
"""
# src/ai_mentor.py
import os
import json
import importlib.resources
from typing import List, Dict, Callable, Generator, Optional

try:
    import litellm
    LITELLM_AVAILABLE = True
except ImportError:
    LITELLM_AVAILABLE = False
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
                 model: Optional[str] = None, data_file_path: str = "ai_mentor_data.json") -> None:
        """Initialize AI mentor with notification callback and configuration.
        
        Args:
            notify_callback: Callback for status/error notifications.
            model: The AI model to use (defaults to OPENAI_MODEL env var or gpt-3.5-turbo).
            data_file_path: Path to JSON file containing level hints and command explanations.
        """
        self.notify = notify_callback
        self.model: str = model or os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
        self.data_file_path: str = data_file_path
        self.level_hints: Dict[str, str] = {}
        self.command_explanations: Dict[str, str] = {}
        self._load_data()
        
        # Check if AI is available
        api_key = os.getenv("OPENAI_API_KEY")
        self.disabled = not LITELLM_AVAILABLE or not api_key
        
        if self.disabled:
            reason = "LiteLLM not installed" if not LITELLM_AVAILABLE else "OpenAI API key not found"
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
        """Generate AI mentor response with context awareness.
        
        Creates an educational response based on the user's message, current level,
        recent commands, and terminal output. Uses streaming for real-time response
        delivery and maintains conversation history for context.
        
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
        """Generate AI mentor response"""
        # If AI is disabled, return a default message
        if self.disabled:
            yield "AI mentor is currently disabled. Please set your OpenAI API key in the .env file to enable this feature."
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
                stream = litellm.completion(
                    model=self.model,
                    messages=messages,
                    max_tokens=500,
                    temperature=0.7,
                    stream=True,
                    timeout=30  # Add timeout
                )
                
                full_response = ""
                for chunk in stream:
                    content = chunk.choices[0].delta.content or ""
                    if content:  # Only yield non-empty content
                        full_response += content
                        yield content
                
                # Update conversation history
                self.conversation_history[session_id].extend([
                    {"role": "user", "content": user_message},
                    {"role": "assistant", "content": full_response}
                ])
                
                # Trim conversation history to prevent unbounded growth
                self._trim_conversation_history(session_id)
                
            except Exception as api_error:
                self.notify(f"AI API Error: {api_error}", "error")
                yield "I'm sorry, there was an error with the AI service. Please try again later."
                
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
        return self.command_explanations.get(command.lower(),
            f"'{command}' is a Linux command. Try 'man {command}' to learn more about it.")
