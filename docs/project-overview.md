# BanditCLI - The OverTheWire Bandit Wargame CLI Tool

## Overview

This project is a command-line tool for playing the OverTheWire Bandit wargame. It's built with Python and the Textual framework, providing a user-friendly interface within the terminal.

---

## Architecture

Here's a breakdown of its architecture:

### Core Components

`main.py`: This is the core of the application. It uses the Textual framework to create the tabbed layout you see when you run it. It handles user input and coordinates the other components. In v0.2.0, it includes session management, command history tracking, offline mode support, and integrates with the caching system.

`ssh_manager.py`: This module manages the SSH connection to the Bandit game server. It's responsible for connecting, sending your commands, and receiving the output. Features multi-session support, connection pooling, and robust error handling with automatic reconnection capabilities.

`level_info.py`: This component loads and displays information about each Bandit level, like the goals and recommended commands. It gets this data from the `src/bandit_levels.json` file. Includes search functionality and fallback data handling.

`ai_mentor.py`: This is the AI assistant. It uses OpenAI's GPT-3.5 (via LiteLLM for multi-provider support) to give you hints based on your current level and the commands you've recently used. Features conversation history management, context-aware responses, and graceful fallback when AI services are unavailable.

### v0.2.0 New Components

`command_history.py`: Manages persistent command history with navigation (up/down arrows), deduplication, and configurable history limits. Supports both in-memory and file-based persistence.

`session_manager.py`: Handles multiple user sessions with persistent storage. Tracks session metadata including connection details, current level, timestamps, and provides session switching capabilities.

`cache.py`: Provides file-based caching with TTL support for AI responses, level data, and other frequently accessed information. Improves performance and reduces API calls.

`config.py`: Centralized configuration management with JSON-based persistence. Supports hierarchical configuration with defaults, user overrides, and runtime updates.

### Supporting Files

`app.tcss`: This file styles the application, defining its colors and layout to make it look good in your terminal.

`src/bandit_levels.json`: This file is a database of all the Bandit level information, which is displayed in the "Level Info" tab.

`ai_mentor_data.json`: Contains level-specific hints and command explanations used by the AI mentor for context-aware responses.

---

## v0.2.0 Features

### Command History

- **Persistent Storage**: Command history is saved to disk and restored between sessions
- **Navigation**: Use arrow keys to navigate through previous commands
- **Deduplication**: Automatically removes duplicate commands from history
- **Configurable Limits**: Set maximum number of commands to store (default: 100)
- **Session Integration**: History is tracked per session for better organization

### Session Management

- **Multiple Sessions**: Create and manage multiple SSH sessions simultaneously
- **Persistent Sessions**: Session information is saved and restored between application restarts
- **Session Metadata**: Tracks connection details, current level, timestamps, and usage statistics
- **Easy Switching**: Quickly switch between different sessions without losing context
- **Session Cleanup**: Automatic cleanup of old sessions and management of session data

### Offline Mode

- **Reduced Functionality**: When offline, the application disables features requiring network connectivity
- **Local Access**: Still access level information, command history, and cached data
- **Clear Indicators**: User is notified when operating in offline mode
- **Graceful Degradation**: Application remains functional with limited capabilities

### Caching System

- **AI Response Caching**: Cache AI mentor responses to reduce API calls and improve performance
- **Level Data Caching**: Cache level information for faster loading
- **TTL Support**: Configurable time-to-live for cached items
- **Automatic Cleanup**: Expired cache items are automatically removed
- **Storage Management**: Configurable cache directory and size limits

### Enhanced AI Mentor

- **Context Awareness**: AI mentor considers current level, recent commands, and terminal output
- **Conversation History**: Maintains conversation context across multiple interactions
- **Multi-Provider Support**: Uses LiteLLM to support different AI providers (OpenAI, Anthropic, etc.)
- **Graceful Fallback**: Provides helpful responses even when AI services are unavailable
- **Educational Focus**: Designed to teach concepts rather than provide direct solutions

### Configuration Management

- **Centralized Config**: All settings managed through a single configuration system
- **Hierarchical Settings**: Support for default, user, and runtime configuration
- **Runtime Updates**: Configuration changes take effect immediately
- **Validation**: Automatic validation of configuration values
- **Backup/Restore**: Easy configuration backup and restoration

---

## Planned Features & Status

| Feature | Status | Priority | Target Version |
|---------|--------|----------|----------------|
| Multi-tab SSH sessions | Planned | Medium | v0.3.0 |
| Command auto-completion | Planned | High | v0.3.0 |
| Level progress tracking | Planned | Medium | v0.2.1 |
| Export/import sessions | Planned | Low | v0.3.0 |
| Terminal themes | Planned | Low | v0.2.1 |
| Keyboard shortcuts customization | Planned | Medium | v0.3.0 |
| Plugin system | Planned | Low | v0.4.0 |
| GUI mode | Planned | Low | v0.4.0 |
| Mobile companion app | Planned | Very Low | v1.0.0 |

---

## Data Storage

The application stores data in the user's home directory under `.bandit_cli/`:

- `config.json`: Application configuration
- `sessions.json`: Session information and metadata
- `cache/`: Cached data directory
- `history/`: Command history files
- `logs/`: Application log files (if enabled)

All data is stored in JSON format for easy inspection and manual editing if needed.