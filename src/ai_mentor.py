import openai
import os
import json
from typing import List, Dict, Optional
from datetime import datetime

from cache import cache

class BanditAIMentor:
    def __init__(self):
        # Check if OpenAI API key is set
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or api_key == "your-openai-api-key-here":
            self.client = None
            self.disabled = True
        else:
            # OpenAI client is already configured via environment variables
            self.client = openai.OpenAI()
            self.disabled = False
            
        self.conversation_history = {}
        
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

    def get_response(self, user_message: str, session_id: str = "default", 
                    current_level: int = 0, recent_commands: List[str] = None,
                    terminal_output: str = "") -> str:
        """Generate AI mentor response"""
        # If AI is disabled, return a default message
        if self.disabled:
            return "AI mentor is currently disabled. Please set your OpenAI API key in the .env file to enable this feature."
        
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
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                max_tokens=500,
                temperature=0.7
            )
            
            ai_response = response.choices[0].message.content
            
            # Update conversation history
            self.conversation_history[session_id].append({
                "role": "user", 
                "content": user_message
            })
            self.conversation_history[session_id].append({
                "role": "assistant", 
                "content": ai_response
            })
            
            return ai_response
            
        except Exception as e:
            print(f"Error generating AI response: {e}")
            return "I'm sorry, I'm having trouble responding right now. Please try again later."
    
    def clear_conversation(self, session_id: str = "default"):
        """Clear conversation history for a session"""
        if session_id in self.conversation_history:
            del self.conversation_history[session_id]
    
    def get_level_hint(self, level_num: int) -> str:
        """Get a general hint for a specific level without spoilers"""
        # Try to get from cache first
        cache_key = f"level_hint_{level_num}"
        cached_hint = cache.get(cache_key)
        if cached_hint is not None:
            return cached_hint
        
        level_hints = {
            0: "This level is about connecting to the game server using SSH. Think about what information you need to establish a secure connection.",
            1: "Look for files in your current directory. What commands can help you see what's available?",
            2: "Sometimes files have unusual names that make them tricky to access. How do you handle special characters in filenames?",
            3: "Hidden files in Linux start with a dot. How can you see all files, including hidden ones?",
            4: "When you have many files, you might need to examine their contents or properties to find what you're looking for.",
            5: "File properties like size, permissions, and type can help you identify the right file among many options.",
        }
        
        hint = level_hints.get(level_num, 
            "Think about what the level description is asking you to find or do. Break down the problem into smaller steps.")
        
        # Cache the result for 1 hour
        cache.set(cache_key, hint, ttl=3600)
        
        return hint
    
    import hashlib

    def explain_command(self, command: str) -> str:
        """Provide educational explanation of a command"""
        # Try to get from cache first
        command_hash = hashlib.sha256(command.encode('utf-8')).hexdigest()
        cache_key = f"command_explanation_{command_hash}"
        cached_explanation = cache.get(cache_key)
        if cached_explanation is not None:
            return cached_explanation
        
        command_explanations = {
            "ls": "Lists directory contents. Try 'ls -la' to see all files including hidden ones with detailed information.",
            "cat": "Displays file contents. Use it to read text files.",
            "cd": "Changes directory. 'cd ..' goes up one level, 'cd ~' goes to home directory.",
            "pwd": "Shows your current directory path.",
            "find": "Searches for files and directories. Very powerful with many options for filtering.",
            "grep": "Searches for text patterns within files.",
            "file": "Determines file type. Useful when file extensions are misleading or missing.",
            "du": "Shows disk usage. Can help find files by size.",
            "ssh": "Secure Shell - used to connect to remote systems securely.",
        }
        
        explanation = command_explanations.get(command.lower(), 
            f"'{command}' is a Linux command. Try 'man {command}' to learn more about it.")
        
        # Cache the result for 1 hour
        cache.set(cache_key, explanation, ttl=3600)
        
        return explanation

# Global instance
ai_mentor = BanditAIMentor()