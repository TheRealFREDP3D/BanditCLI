# BanditCLI - Project Context

## Project Overview

BanditCLI is a terminal-based interface for the OverTheWire Bandit wargame, built with Python and the Textual framework. This educational application provides a simplified interface for cybersecurity learning through hands-on challenges, featuring SSH connectivity, AI mentor assistance, and comprehensive level information.

**Key Technologies:**
- **Framework**: Textual (Python TUI framework)
- **SSH Client**: Paramiko for secure connections
- **AI Integration**: OpenAI API (GPT-3.5) via litellm
- **Data**: JSON files containing scraped level data from OverTheWire
- **Caching**: File-based caching system for improved performance

**Current Version**: 0.2.0  
**Supported Python Versions**: 3.8+

## Project Structure

```
bandit-cli-app/
├── src/
│   ├── main.py              # Main Textual application
│   ├── ssh_manager.py       # SSH connection management
│   ├── ai_mentor.py         # AI mentor functionality
│   ├── level_info.py        # Level information handling
│   ├── command_history.py   # Command history management
│   ├── session_manager.py   # Session management
│   ├── cache.py             # Caching utilities
│   ├── config.py            # Configuration management
│   ├── terminal_output.py   # Terminal output handling
│   ├── performance_monitor.py # Performance tracking
│   ├── app.tcss             # CSS styling for the application
│   ├── ai_mentor_data.json  # AI mentor configuration data
│   └── bandit_levels.json   # Level data scraped from OverTheWire
├── tests/                   # Test suite
├── docs/                    # Documentation
├── requirements.txt         # Python dependencies
├── requirements-dev.txt     # Development dependencies
├── pyproject.toml          # Project configuration
├── ruff.toml              # Linting configuration
├── README.md               # Project documentation
├── LICENSE                 # MIT License
├── SECURITY.md            # Security documentation
└── CONTRIBUTING.md        # Contributing guidelines
```

## Building and Running

### Prerequisites
- Python 3.8+
- An OpenAI API key (for AI mentor functionality)

### Setup
```bash
# Clone the repository
git clone <repository-url>
cd bandit-cli-app

# Create a virtual environment:
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install the required dependencies:
pip install -r requirements.txt

# (Optional) Install development dependencies for code quality tools:
pip install -r requirements-dev.txt

# Set your OpenAI API key as an environment variable:
export OPENAI_API_KEY="your-openai-api-key-here"  # On Windows: set OPENAI_API_KEY=your-openai-api-key-here
```

### Running the Application
```bash
# Using the installed script
bandit-cli

# Or run directly from source
python -m src.main
```

### Development Commands
```bash
# Format code
black src/ tests/

# Run linting
ruff check src/ tests/

# Type checking
mypy src/

# Run tests
pytest tests/
```

## Key Features

### SSH Terminal Interface
- Real-time SSH connection to bandit.labs.overthewire.org with configurable port (default 2220)
- Interactive terminal interface with full terminal emulation
- Connection status indicators and authentication management
- Username, password, and port input fields for flexible connection settings
- Command history navigation with up/down arrow keys

### Level Information Display
- View level objectives, recommended commands, and learning materials
- Navigate between different levels (currently levels 0-5 have full support)
- Clean, organized presentation
- Cached for improved performance

### AI Mentor System
- OpenAI GPT-3.5 integration for intelligent guidance
- Context-aware responses based on current level and recent commands
- Hint system that provides guidance without revealing solutions
- Interactive chat interface with conversation history

### Command History
- Persistent command history across sessions
- Navigate through previous commands with up/down arrow keys
- Configurable history size limit
- Automatic deduplication of commands

### Session Management
- Create and manage multiple sessions
- Save session information including hostname, port, username, and current level
- Switch between sessions
- Persistent session storage

### Offline Mode
- Access level information without internet connection
- Review command history and previous sessions
- Work with cached level data
- Toggle offline mode with keyboard shortcut

## Development Conventions

### Code Quality
- **Black**: Code formatting enforced
- **Ruff**: Linting and code analysis
- **MyPy**: Type checking with strict settings
- **Line Length**: 100 characters maximum

### Coding Standards
- All public functions and classes must have comprehensive docstrings in Google style
- All functions must have type hints
- Code should follow PEP 8 standards (enforced by Black and Ruff)
- New features should include appropriate tests

### Security Practices
- SSH passwords are stored in memory only during active sessions and securely cleared on disconnect
- Host key verification is enabled by default to prevent MITM attacks
- Input validation prevents injection attacks
- API keys are accessed via environment variables and never logged
- The AI mentor feature sends limited data to OpenAI API with opt-out capability

### Testing
- Aim for 80%+ code coverage
- Use pytest framework
- Mock external services (SSH connections, OpenAI API) for testing
- Place tests in `tests/` directory with appropriate naming convention

## Keyboard Shortcuts

- `d`: Toggle dark mode
- `q`: Quit the application
- `1`: Switch to Terminal tab
- `2`: Switch to Level Info tab
- `3`: Switch to AI Mentor tab
- `c`: Show cache statistics
- `ctrl+c`: Cancel operation
- `ctrl+shift+c`: Clear cache
- `?`: Ask AI about last output
- `s`: Show session info
- `n`: New session
- `w`: Switch session dialog
- `o`: Toggle offline mode

## Troubleshooting

### Common Issues
- **SSH Connection Fails**: Verify port 2220 is accessible, check credentials, and network connection
- **AI Mentor Not Working**: Verify `OPENAI_API_KEY` is set correctly and has valid billing
- **Command History Not Saving**: Check write permissions for `~/.bandit_cli/` directory
- **Application Won't Start**: Verify Python 3.8+ and all dependencies are installed

## Security Considerations

The application handles SSH credentials and sends terminal data to third-party APIs. Users should be aware of the security implications:

- SSH passwords are stored in memory only during active sessions
- The AI mentor feature sends limited data to OpenAI API (user messages, command history, terminal output)
- API keys are accessed via environment variables and never logged
- Host key verification is enabled by default to prevent MITM attacks
- Users can disable AI mentor completely via opt-out flag

For detailed security practices, refer to SECURITY.md.