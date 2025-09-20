# Bandit CLI Application Design

## Overview
This document outlines the design for a CLI version of the Bandit Wargame GUI application using the Textual Python framework. The application will provide a terminal-based interface for playing the OverTheWire Bandit wargame with features including an SSH terminal, level information display, and an AI mentor.

## Architecture

### Main Components

1. **Textual App (`main.py`)**:
   - Entry point for the Textual application
   - Sets up the main layout and composes the different widgets
   - Handles global events and state management
   - Implements offline mode functionality

2. **SSH Manager (`ssh_manager.py`)**:
   - Implements the SSH connection functionality using Paramiko
   - Provides a terminal-like interface for interacting with the Bandit server
   - Handles input/output with the SSH connection
   - Manages multiple SSH sessions

3. **Level Information (`level_info.py`)**:
   - Displays information about the current Bandit level
   - Loads level data from the JSON file
   - Shows level goals, recommended commands, and reading materials
   - Implements caching for improved performance

4. **AI Mentor (`ai_mentor.py`)**:
   - Integrates with the OpenAI API for AI-powered mentoring
   - Provides hints and guidance based on the current level and user's commands
   - Maintains conversation history
   - Implements caching for command explanations and level hints

5. **Command History (`command_history.py`)**:
   - Manages command history with persistence
   - Implements navigation through command history
   - Deduplicates commands in history

6. **Session Manager (`session_manager.py`)**:
   - Manages multiple user sessions
   - Persists session information to disk
   - Tracks current session and session metadata

7. **Configuration Manager (`config.py`)**:
   - Manages application configuration
   - Loads and saves configuration to file
   - Provides default values and validation

8. **Cache (`cache.py`)**:
   - Implements file-based caching system
   - Provides cache expiration and persistence
   - Used by level info, AI mentor, and other components

### Data Flow

1. User starts the application
2. Application initializes the Textual interface
3. User provides SSH credentials
4. SSH connection is established and terminal output is displayed
5. Level information is loaded and displayed
6. User can interact with the AI mentor for hints and guidance
7. User's commands and terminal output are tracked for context-aware mentoring
8. Command history is maintained and persisted
9. Sessions are created and managed
10. Configuration is loaded and applied
11. Data is cached for improved performance
12. User can toggle offline mode for working without internet

## Textual Components

### Widgets to Use

1. **TextArea**: For displaying terminal output and chat conversations
2. **Input**: For command input and message input
3. **DataTable**: For displaying structured data
4. **Markdown**: For displaying formatted text content
5. **Tabs**: For switching between different views (terminal, level info, mentor)
6. **Button**: For actions like connecting/disconnecting SSH
7. **Label**: For displaying status information
8. **Header**: For displaying application title and status

### Layout Structure

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Bandit Wargame CLI                                                [Status]  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │                              Terminal View                              │ │
│ │ ┌─────────────────────────────────────────────────────────────────────┐ │ │
│ │ │                         Terminal Output                             │ │ │
│ │ │                         (Scrollable)                                │ │ │
│ │ │                                                                     │ │ │
│ │ └─────────────────────────────────────────────────────────────────────┘ │ │
│ │ ┌─────────────────────────────────────────────────────────────────────┐ │ │
│ │ │ SSH Login: [Username] [Password] [Port] [Connect] [Disconnect]      │ │ │
│ │ └─────────────────────────────────────────────────────────────────────┘ │ │
│ │ ┌─────────────────────────────────────────────────────────────────────┐ │ │
│ │ │ > [Command Input]                                                   │ │ │
│ │ └─────────────────────────────────────────────────────────────────────┘ │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │                               Info View                                 │ │
│ │ ┌─────────────────────────────────────────────────────────────────────┐ │ │
│ │ │ Level: 1                                                            │ │ │
│ │ │ Goal: [Description of the level goal]                               │ │ │
│ │ │ Commands: [List of recommended commands]                            │ │ │
│ │ │ Reading Materials: [List of helpful links]                          │ │ │
│ │ └─────────────────────────────────────────────────────────────────────┘ │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │                              Mentor View                                │ │
│ │ ┌─────────────────────────────────────────────────────────────────────┐ │ │
│ │ │                        Conversation History                         │ │ │
│ │ │                        (Scrollable)                                 │ │ │
│ │ │                                                                     │ │ │
│ │ └─────────────────────────────────────────────────────────────────────┘ │ │
│ │ ┌─────────────────────────────────────────────────────────────────────┐ │ │
│ │ │ > [Message Input]                                                   │ │ │
│ │ └─────────────────────────────────────────────────────────────────────┘ │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### State Management

The application will maintain the following state:

1. **SSH Connection State**:
   - Connected/disconnected
   - Connection details (hostname, port, username, password)
   - Active session

2. **Current Level**:
   - Level number
   - Level information (loaded from JSON)

3. **AI Mentor State**:
   - Conversation history
   - Recent commands
   - Terminal output context

4. **Command History**:
   - List of previously entered commands
   - Current position in history navigation

5. **Session State**:
   - Current session information
   - List of available sessions
   - Session metadata

6. **Configuration State**:
   - User preferences and settings
   - Default values for various features

7. **UI State**:
   - Current active tab/view
   - Terminal scroll position
   - Input focus
   - Offline mode status

8. **Cache State**:
   - Cached level information
   - Cached AI responses
   - Cached command explanations

## Implementation Plan

1. Create the basic Textual application structure
2. Implement the SSH terminal functionality
3. Create the level information display
4. Integrate the AI mentor functionality
5. Design and implement the UI layout
6. Add state management
7. Implement command history functionality
8. Add session management
9. Implement configuration management
10. Add caching for improved performance
11. Implement offline mode
12. Test and refine the application
13. Create documentation and installation instructions
14. Add comprehensive unit tests