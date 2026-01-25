# Architecture Documentation

## Overview

BanditCLI is a terminal-based application built with Python and the Textual framework that provides an interface for playing the OverTheWire Bandit wargame. The application follows a modular architecture with clear separation of concerns.

## System Architecture

### Core Components

#### 1. Main Application (`main.py`)
- **Purpose**: Entry point and main UI controller
- **Framework**: Textual TUI framework
- **Responsibilities**:
  - Initialize and manage the main application interface
  - Handle tab navigation between Terminal, Level Info, and AI Mentor
  - Coordinate between different modules
  - Manage application lifecycle and state

#### 2. SSH Management (`ssh_manager.py`)
- **Purpose**: Secure SSH connection handling
- **Key Classes**: `SSHConnection`, `SSHManager`
- **Features**:
  - Thread-safe SSH connections with background output reading
  - Rate limiting to prevent brute force attacks
  - Secure password handling and memory cleanup
  - Connection pooling and session management
  - Host key verification for security

#### 3. AI Mentor System (`ai_mentor.py`)
- **Purpose**: Intelligent guidance system using OpenAI API
- **Features**:
  - Context-aware responses based on current level and command history
  - Hint system without revealing solutions
  - Conversation history management
  - Caching to reduce API calls
  - Fallback mechanisms for API failures

#### 4. Level Information (`level_info.py`)
- **Purpose**: Bandit level data management
- **Data Source**: `bandit_levels.json` (scraped from OverTheWire)
- **Features**:
  - Level navigation and information display
  - Caching for performance
  - Support for levels 0-5 (with placeholder for others)

#### 5. Session Management (`session_manager.py`)
- **Purpose**: User session persistence
- **Features**:
  - Session creation, storage, and retrieval
  - Persistent storage across application restarts
  - Session metadata tracking (hostname, port, username, level)

#### 6. Command History (`command_history.py`)
- **Purpose**: Command history management
- **Features**:
  - Persistent command storage
  - Navigation with arrow keys
  - Deduplication and size limits
  - Cross-session persistence

#### 7. Caching System (`cache.py`)
- **Purpose**: Performance optimization through intelligent caching
- **Features**:
  - File-based cache with TTL support
  - Statistics tracking (hits, misses, hit rate)
  - Automatic cleanup of expired entries
  - Hash-based key generation for AI responses

#### 8. Configuration Management (`config.py`)
- **Purpose**: Application configuration
- **Features**:
  - JSON-based configuration storage
  - Default configuration with user overrides
  - Dot notation access (e.g., `config.get('ssh.port')`)
  - Automatic configuration directory creation

#### 9. Terminal Output (`terminal_output.py`)
- **Purpose**: Terminal emulation and output handling
- **Features**:
  - ANSI escape sequence processing
  - Terminal state management
  - Output buffering and display optimization

## Data Flow

### SSH Connection Flow
1. User enters credentials in Terminal tab
2. `SSHManager.create_connection()` validates input and checks rate limits
3. `SSHConnection.connect()` establishes SSH session with retry logic
4. Background thread (`_read_output`) continuously reads server output
5. Output is forwarded to UI through callback functions
6. User commands are sent through `SSHConnection.send_command()`

### AI Mentor Flow
1. User submits question in AI Mentor tab
2. System generates cache key based on level and question
3. Cache is checked for existing response
4. If cached, return cached response
5. If not cached, call OpenAI API with context:
   - Current level information
   - Recent command history (last 5 commands)
   - Recent terminal output (up to 500 characters)
6. Cache the API response
7. Display response to user

### Session Persistence Flow
1. User connects to SSH server
2. `SessionManager` creates session with connection details
3. Session is saved to JSON file in `~/.bandit_cli/sessions/`
4. Sessions are loaded on application startup
5. User can switch between saved sessions

## Security Considerations

### SSH Security
- **Host Key Verification**: Prevents MITM attacks
- **Rate Limiting**: 5 attempts per minute per hostname:port
- **Password Security**: Secure memory clearing using bytearray overwrite
- **No SSH Agent**: Disabled to prevent credential leakage
- **Timeout Protection**: Connection and operation timeouts

### Data Privacy
- **AI Mentor**: Only command history and terminal output sent to OpenAI
- **No Password Transmission**: Passwords explicitly excluded from AI requests
- **Local Storage**: All sensitive data stored locally
- **Configurable**: AI features can be disabled by not setting API key

## Performance Optimizations

### Caching Strategy
- **Level Information**: Cached indefinitely (updates only with application)
- **AI Responses**: Cached with 24-hour TTL
- **Configuration**: Cached in memory with disk persistence
- **Command History**: Cached for fast navigation

### Threading Model
- **SSH Output**: Background daemon thread for non-blocking I/O
- **AI Requests**: Asynchronous API calls to prevent UI freezing
- **UI Updates**: Thread-safe updates through Textual message system

## Error Handling

### Connection Errors
- **Retry Logic**: Exponential backoff for SSH connections
- **Graceful Degradation**: Application remains functional without SSH
- **User Notifications**: Clear error messages and recovery suggestions

### API Errors
- **Fallback Responses**: Predefined hints when API unavailable
- **Rate Limiting**: Respect OpenAI API limits
- **Timeout Handling**: Prevent hanging on slow API responses

### Data Corruption
- **Cache Validation**: JSON parsing with error recovery
- **Backup Creation**: Automatic backup of corrupted configuration
- **Graceful Recovery**: Continue with defaults when data is corrupted

## File Structure

```
~/.bandit_cli/
├── config.json          # User configuration
├── cache/               # Cached data
│   ├── *.cache         # Individual cache files
│   └── cache_stats.json # Cache statistics
├── sessions/            # Saved sessions
│   └── *.json         # Session files
└── history.json         # Command history
```

## Technology Stack

- **UI Framework**: Textual (Python TUI)
- **SSH Client**: Paramiko
- **AI Integration**: OpenAI API
- **Data Storage**: JSON files
- **Caching**: Custom file-based system
- **Configuration**: JSON with merge logic
- **Security**: Thread-safe operations with locks

## Future Extensibility

### Modular Design
The architecture supports easy addition of:
- New wargames (beyond Bandit)
- Additional AI providers
- Different authentication methods
- Enhanced caching strategies
- Plugin system for custom features

### Configuration System
The dot-notation configuration system allows for:
- Runtime configuration changes
- Feature flags
- User preferences
- Environment-specific settings

## Testing Strategy

### Unit Tests
- Individual module testing
- Mock external dependencies (SSH, API)
- Configuration edge cases
- Cache behavior validation

### Integration Tests
- End-to-end SSH workflows
- AI mentor integration
- Session persistence
- Multi-tab navigation

### Security Tests
- Password handling verification
- Rate limiting validation
- Host key verification
- Data privacy compliance
