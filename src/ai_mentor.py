import litellm
import os
import json
import importlib
from typing import List, Dict, Optional, Callable
from datetime import datetime

from textual.app import Notify
class BanditAIMentor:
    def __init__(self, notify_callback: Callable[[str, str], None], model: str = None, data_file_path: str = "ai_mentor_data.json"):
        self.notify = notify_callback
        self.model: str = model or os.getenv("OPENAI_MODEL", "ollama/llama3.2")
        self.data_file_path: str = data_file_path
        self.level_hints: Dict[str, str] = {}
        self.command_explanations: Dict[str, str] = {}
        self._load_data()

        # LiteLLM can handle different providers, so we don't need a specific client instance.
        # We can check for a general API key, but since we are defaulting to a local model,
        # we might not need one. For now, we'll assume that if a user wants to use a
        # different model, they will set the appropriate environment variables.
        self.disabled = False
            
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

    def _load_data(self):
        """Load data from the JSON file."""
        try:
            with importlib.resources.open_text("src", self.data_file_path) as f:
                data = json.load(f)
                self.level_hints = data.get("level_hints", {})
                self.command_explanations = data.get("command_explanations", {})
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self.notify(f"Error loading AI mentor data: {e}", "error")
            self.level_hints = {}
            self.command_explanations = {}

    def get_response(self, user_message: str, session_id: str = "default", 
                    current_level: int = 0, recent_commands: List[str] = None,
                    terminal_output: str = ""):
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
            
            # Add conversation history (limit to last 10 exchanges)
            recent_history = self.conversation_history[session_id][-10:]
            messages.extend(recent_history)
            
            # Add context if available
            if context_message:
                messages.append({
                    "role": "system", 
                    "content": f"Current context: {context_message}"
                })
            
            # Add user message
            messages.append({"role": "user", "content": user_message})
            
            # Generate response
            stream = litellm.completion(
                model=self.model,
                messages=messages,
                max_tokens=500,
                temperature=0.7,
                stream=True
            )
            
            full_response = ""
            for chunk in stream:
                content = chunk.choices[0].delta.content or ""
                if content:
                    full_response += content
                    yield content
            
            # Update conversation history
            self.conversation_history[session_id].append({
                "role": "user", 
                "content": user_message
            })
            self.conversation_history[session_id].append({
                "role": "assistant", 
                "content": full_response
            })
            
        except litellm.exceptions.APIError as e:
            self.notify(f"LiteLLM API Error: {e}", "error")
            yield "I'm sorry, there was an error with the AI mentor service. Please try again later."
        except Exception as e:
            self.notify(f"Error generating AI response: {e}", "error")
            yield "I'm sorry, I'm having trouble responding right now. Please try again later."
    
    def clear_conversation(self, session_id: str = "default"):
        """Clear conversation history for a session"""
        if session_id in self.conversation_history:
            del self.conversation_history[session_id]
    
    def get_level_hint(self, level_num: int) -> str:
        """Get a general hint for a specific level without spoilers"""
        return self.level_hints.get(str(level_num),
            "Think about what the level description is asking you to find or do. Break down the problem into smaller steps.")
    
    def explain_command(self, command: str) -> str:
        """Provide educational explanation of a command"""
        return self.command_explanations.get(command.lower(),
            f"'{command}' is a Linux command. Try 'man {command}' to learn more about it.")