# API Documentation

## Overview

This document describes the public APIs provided by the BanditCLI application. The APIs are organized by module and include usage examples and parameter descriptions.

## Cache Module (`src/cache.py`)

### Class: `Cache`

A file-based caching system with expiration support and statistics tracking.

#### Constructor

```python
Cache(cache_dir: str = None, default_ttl: int = 3600)
```

**Parameters:**
- `cache_dir`: Directory to store cache files. If None, uses `~/.bandit_cli/cache`
- `default_ttl`: Default time-to-live in seconds for cached items (default: 3600)

#### Methods

##### `get(key: str) -> Optional[Any]`

Retrieve a value from the cache.

**Parameters:**
- `key`: Cache key to retrieve

**Returns:**
- Cached value or `None` if not found or expired

**Example:**
```python
cache = Cache()
value = cache.get("user_123")  # Returns cached data or None
```

##### `set(key: str, value: Any, ttl: int = None) -> None`

Store a value in the cache.

**Parameters:**
- `key`: Cache key for storage
- `value`: Value to cache
- `ttl`: Time-to-live in seconds. If None, uses default TTL

**Example:**
```python
cache.set("user_123", {"name": "Alice"}, ttl=1800)  # Cache for 30 minutes
```

##### `clear() -> None`

Remove all cached items.

**Example:**
```python
cache.clear()  # Removes all cache files
```

##### `clear_key(key: str) -> None`

Remove a specific cached item.

**Parameters:**
- `key`: Cache key to remove

**Example:**
```python
cache.clear_key("user_123")  # Removes specific item
```

##### `get_stats() -> Dict`

Get comprehensive cache statistics.

**Returns:**
Dictionary containing:
- `hits`: Number of cache hits
- `misses`: Number of cache misses
- `sets`: Number of cache sets
- `clears`: Number of cache clears
- `hit_rate_percent`: Hit rate as percentage
- `total_requests`: Total cache requests
- `cache_size`: Number of items currently in cache

**Example:**
```python
stats = cache.get_stats()
print(f"Hit rate: {stats['hit_rate_percent']}%")
```

##### `cleanup_expired() -> int`

Remove expired cache entries.

**Returns:**
- Number of expired entries removed

**Example:**
```python
removed = cache.cleanup_expired()
print(f"Cleaned up {removed} expired entries")
```

##### `generate_hash_key(level: int, question: str) -> str`

Generate a hash key for AI responses based on level and question.

**Parameters:**
- `level`: The current level number
- `question`: The user's question

**Returns:**
- MD5 hash key for caching

**Example:**
```python
key = cache.generate_hash_key(5, "How do I find hidden files?")
```

## Configuration Module (`src/config.py`)

### Class: `ConfigManager`

Manages application configuration with default values and user overrides.

#### Constructor

```python
ConfigManager(config_file: str = None)
```

**Parameters:**
- `config_file`: Path to configuration file. If None, uses `~/.bandit_cli/config.json`

#### Methods

##### `get(key_path: str, default: Any = None) -> Any`

Get a configuration value using dot notation.

**Parameters:**
- `key_path`: Dot-separated path (e.g., "ssh.port", "ai.model")
- `default`: Default value if key not found

**Returns:**
- Configuration value or default

**Example:**
```python
config = ConfigManager()
host = config.get("ssh.host", "localhost")
port = config.get("ssh.port", 22)
```

##### `set(key_path: str, value: Any) -> None`

Set a configuration value using dot notation.

**Parameters:**
- `key_path`: Dot-separated path (e.g., "ssh.port", "ai.model")
- `value`: Value to set

**Example:**
```python
config.set("ssh.host", "example.com")
config.set("ai.model", "gpt-4")
config.set("new.nested.key", "value")  # Creates nested structure
```

##### `load_config() -> Dict[str, Any]`

Load configuration from file and merge with defaults.

**Returns:**
- Merged configuration dictionary

**Example:**
```python
config = ConfigManager()
settings = config.load_config()
print(settings['ssh']['host'])  # 'bandit.labs.overthewire.org'
```

##### `save_config() -> None`

Save current configuration to file.

**Example:**
```python
config.set("ssh.port", 2220)
config.save_config()  # Persists to disk
```

##### `reset_to_default() -> None`

Reset all configuration to default values.

**Example:**
```python
config.reset_to_default()  # Resets all settings to defaults
```

## SSH Manager Module (`src/ssh_manager.py`)

### Class: `SSHConnection`

Thread-safe SSH connection with background output reading.

#### Constructor

```python
SSHConnection(hostname: str, port: int, username: str, password: str,
           notify_callback: Callable[[str, str], None], timeout: int = 10,
           verify_host_key: bool = True)
```

**Parameters:**
- `hostname`: Remote server hostname
- `port`: SSH port number
- `username`: SSH username
- `password`: SSH password
- `notify_callback`: Callback for status/error notifications (message, severity)
- `timeout`: Connection timeout in seconds (default: 10)
- `verify_host_key`: Whether to verify host keys (default: True)

#### Methods

##### `connect() -> bool`

Establish SSH connection with interactive shell.

**Returns:**
- `True` if connection successful, `False` otherwise

**Example:**
```python
def notify(msg, severity):
    print(f"[{severity}] {msg}")

conn = SSHConnection("example.com", 22, "user", "pass", notify)
if conn.connect():
    print("Connected successfully")
```

##### `send_command(command: str) -> None`

Send command to SSH session.

**Parameters:**
- `command`: Command to send to remote shell

**Example:**
```python
conn.send_command("ls -la\n")
```

##### `disconnect() -> None`

Close SSH connection safely with thread cleanup.

**Example:**
```python
conn.disconnect()  # Cleanly close connection
```

##### `resize_pty(width: int, height: int) -> bool`

Resize the interactive shell PTY.

**Parameters:**
- `width`: New width in characters
- `height`: New height in characters

**Returns:**
- `True` if resize successful, `False` otherwise

**Example:**
```python
conn.resize_pty(80, 24)  # Standard terminal size
```

##### `set_output_callback(callback: Callable[[str], None]) -> None`

Set callback function for handling SSH output.

**Parameters:**
- `callback`: Function to call when SSH output is received

**Example:**
```python
def handle_output(data):
    print(f"Received: {data}")

conn.set_output_callback(handle_output)
```

### Class: `SSHManager`

Multi-session SSH connection manager.

#### Constructor

```python
SSHManager(notify_callback: Callable[[str, str], None])
```

**Parameters:**
- `notify_callback`: Callback for status/error notifications

#### Methods

##### `create_connection(session_id: str, hostname: str, port: int,
                   username: str, password: str, timeout: int = 10,
                   verify_host_key: bool = True) -> bool`

Create new SSH connection with validation.

**Parameters:**
- `session_id`: Unique identifier for the SSH session
- `hostname`: Remote server hostname
- `port`: SSH port number
- `username`: SSH username
- `password`: SSH password
- `timeout`: Connection timeout in seconds (default: 10)
- `verify_host_key`: Whether to verify host keys (default: True)

**Returns:**
- `True` if connection successful, `False` otherwise

**Example:**
```python
manager = SSHManager(notify_callback)
success = manager.create_connection(
    "session1", "bandit.labs.overthewire.org", 2220, "bandit0", "password"
)
```

##### `get_connection(session_id: str) -> Optional[SSHConnection]`

Get SSH connection by session ID.

**Parameters:**
- `session_id`: Session identifier to look up

**Returns:**
- SSH connection if found, `None` otherwise

**Example:**
```python
conn = manager.get_connection("session1")
if conn:
    conn.send_command("ls\n")
```

##### `disconnect_session(session_id: str) -> None`

Disconnect and remove SSH session.

**Parameters:**
- `session_id`: Session identifier to disconnect

**Example:**
```python
manager.disconnect_session("session1")
```

##### `disconnect_all() -> None`

Disconnect all active SSH sessions.

**Example:**
```python
manager.disconnect_all()  # Close all connections
```

## AI Mentor Module (`src/ai_mentor.py`)

### Class: `AIMentor`

Intelligent guidance system using OpenAI API.

#### Constructor

```python
AIMentor(config_manager: ConfigManager, cache: Cache,
         notify_callback: Callable[[str, str], None])
```

**Parameters:**
- `config_manager`: Configuration manager instance
- `cache`: Cache instance for response caching
- `notify_callback`: Callback for status/error notifications

#### Methods

##### `ask_question(level: int, question: str, command_history: List[str],
               terminal_output: str) -> str`

Ask AI mentor a question with context.

**Parameters:**
- `level`: Current Bandit level number
- `question`: User's question
- `command_history`: Recent command history (last 5 commands)
- `terminal_output`: Recent terminal output (up to 500 characters)

**Returns:**
- AI mentor's response

**Example:**
```python
mentor = AIMentor(config, cache, notify_callback)
response = mentor.ask_question(
    level=5,
    question="How do I find hidden files?",
    command_history=["ls", "pwd", "whoami"],
    terminal_output="bandit5@bandit:~$ "
)
```

##### `clear_conversation_history() -> None`

Clear the conversation history.

**Example:**
```python
mentor.clear_conversation_history()
```

## Session Manager Module (`src/session_manager.py`)

### Class: `SessionManager`

Manages user session persistence.

#### Constructor

```python
SessionManager()
```

#### Methods

##### `create_session(name: str, hostname: str, port: int, username: str,
                 level: int) -> Dict`

Create a new session.

**Parameters:**
- `name`: Session name/identifier
- `hostname`: SSH hostname
- `port`: SSH port
- `username`: SSH username
- `level`: Current Bandit level

**Returns:**
- Created session dictionary

**Example:**
```python
manager = SessionManager()
session = manager.create_session(
    "bandit5", "bandit.labs.overthewire.org", 2220, "bandit5", 5
)
```

##### `get_session(name: str) -> Optional[Dict]`

Get session by name.

**Parameters:**
- `name`: Session name

**Returns:**
- Session dictionary if found, `None` otherwise

**Example:**
```python
session = manager.get_session("bandit5")
if session:
    print(f"Level: {session['level']}")
```

##### `list_sessions() -> List[Dict]`

List all saved sessions.

**Returns:**
- List of session dictionaries

**Example:**
```python
sessions = manager.list_sessions()
for session in sessions:
    print(f"{session['name']}: Level {session['level']}")
```

##### `delete_session(name: str) -> bool`

Delete a session.

**Parameters:**
- `name`: Session name to delete

**Returns:**
- `True` if deleted, `False` if not found

**Example:**
```python
success = manager.delete_session("old_session")
```

## Command History Module (`src/command_history.py`)

### Class: `CommandHistory`

Manages persistent command history with navigation.

#### Constructor

```python
CommandHistory(max_history: int = 100)
```

**Parameters:**
- `max_history`: Maximum number of commands to store (default: 100)

#### Methods

##### `add_command(command: str) -> None`

Add a command to history.

**Parameters:**
- `command`: Command to add

**Example:**
```python
history = CommandHistory()
history.add_command("ls -la")
```

##### `get_previous() -> Optional[str]`

Get previous command from history.

**Returns:**
- Previous command or `None` if at beginning

**Example:**
```python
prev_cmd = history.get_previous()
```

##### `get_next() -> Optional[str]`

Get next command from history.

**Returns:**
- Next command or `None` if at end

**Example:**
```python
next_cmd = history.get_next()
```

##### `reset_navigation() -> None`

Reset navigation pointer to current position.

**Example:**
```python
history.reset_navigation()
```

##### `clear() -> None`

Clear all command history.

**Example:**
```python
history.clear()
```

## Level Info Module (`src/level_info.py`)

### Class: `LevelInfo`

Manages Bandit level information.

#### Constructor

```python
LevelInfo(cache: Cache)
```

**Parameters:**
- `cache`: Cache instance for level data caching

#### Methods

##### `get_level_info(level: int) -> Optional[Dict]`

Get information for a specific level.

**Parameters:**
- `level`: Level number

**Returns:**
- Level information dictionary or `None` if not available

**Example:**
```python
info = LevelInfo(cache)
level_data = info.get_level_info(5)
if level_data:
    print(level_data['goal'])
```

##### `get_available_levels() -> List[int]`

Get list of available levels.

**Returns:**
- List of available level numbers

**Example:**
```python
levels = info.get_available_levels()
print(f"Available levels: {levels}")
```

## Global Instances

The following global instances are available for convenience:

```python
from src.cache import cache
from src.config import config
```

- `cache`: Global cache instance
- `config`: Global configuration manager instance

## Error Handling

All APIs use the following error handling patterns:

1. **Graceful Degradation**: Functions return default values or `None` on errors
2. **Notification System**: Errors are reported through callback functions
3. **Exception Safety**: All functions handle exceptions without crashing
4. **Logging**: Errors are logged for debugging purposes

## Thread Safety

- **SSH Connections**: All SSH operations are thread-safe using locks
- **Cache**: File operations are atomic and thread-safe
- **Configuration**: Thread-safe for read operations, writes are serialized

## Security Considerations

- **Passwords**: Securely cleared from memory after use
- **SSH**: Host key verification enabled by default
- **Rate Limiting**: Connection attempts limited to prevent brute force
- **Data Privacy**: Sensitive data excluded from AI requests
