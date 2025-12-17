# Bandit Wargame CLI

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) ![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg) ![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg) ![Version](https://img.shields.io/badge/version-0.2.0-blue.svg)

A terminal-based interface for playing the OverTheWire Bandit wargame, built with Python and the Textual framework. This CLI application provides a simplified interface for playing the challenges, featuring:

- SSH Terminal Interface: Real-time SSH connection to the Bandit server
- Level Information Display: View level goals, recommended commands, and reading materials
- AI Mentor System: Get contextual hints and guidance without revealing solutions
- Command History: Navigate through previously entered commands
- Session Management: Save and switch between multiple sessions
- Offline Mode: Access level information and review sessions without internet
- Caching: Improved performance through intelligent caching of frequently accessed data

## ⚠️ Important Notes

### Level Availability

⚠️ **Level Data Availability**: Currently, only levels 0-5 (6 out of 34 Bandit levels) have full support with detailed goals, commands, and reading materials. For levels 6-33, the application will display a message directing you to the [official OverTheWire Bandit website](https://overthewire.org/wargames/bandit/).

### Data Privacy

🔒 **Data Privacy Notice**: When using the AI Mentor, your recent commands (last 5) and terminal output (up to 500 characters) are sent to OpenAI's API for context-aware responses. No passwords or sensitive credentials are intentionally sent, but be aware that command history may contain sensitive information. You can disable the AI Mentor by not setting the `OPENAI_API_KEY` environment variable.

## Features

### 🖥️ SSH Terminal Interface
- Real-time SSH connection to bandit.labs.overthewire.org with configurable port (default 2220)
- Interactive terminal interface with full terminal emulation
- Connection status indicators and authentication management
- Username, password, and port input fields for flexible connection settings
- Command history navigation with up/down arrow keys

### 📚 Level Information Display
- View level objectives, recommended commands, and learning materials
- Navigate between different levels
- Clean, organized presentation
- Cached for improved performance

### 🤖 AI Mentor System
- OpenAI GPT-3.5 integration for intelligent guidance
- Context-aware responses based on current level and recent commands
- Hint system that provides guidance without revealing solutions
- Interactive chat interface with conversation history

### 📜 Command History
- Persistent command history across sessions
- Navigate through previous commands with up/down arrow keys
- Configurable history size limit
- Automatic deduplication of commands

### 💾 Session Management
- Create and manage multiple sessions
- Save session information including hostname, port, username, and current level
- Switch between sessions
- Persistent session storage

### 🌐 Offline Mode
- Access level information without internet connection
- Review command history and previous sessions
- Work with cached level data
- Toggle offline mode with keyboard shortcut

### ⚡ Performance Optimizations
- Intelligent caching of level information, AI hints, and command explanations
- File-based cache with expiration
- Reduced API calls through caching

## Installation

### Prerequisites
- Python 3.8+
- An OpenAI API key (for AI mentor functionality)

### Setup

1. Clone the repository or download the source code
2. Navigate to the project directory:
   ```bash
   cd bandit-cli-app
   ```
3. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
4. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
5. (Optional) Install development dependencies for code quality tools:
   ```bash
   pip install -r requirements-dev.txt
   ```
6. Set your OpenAI API key as an environment variable:
   ```bash
   export OPENAI_API_KEY="your-openai-api-key-here"  # On Windows: set OPENAI_API_KEY=your-openai-api-key-here
   ```

## Usage

Run the application with:
```bash
python src/main.py
```

### Navigation

The application has three main tabs:
1. **Terminal**: SSH terminal interface for interacting with the Bandit server
2. **Level Info**: View information about the current Bandit level
3. **AI Mentor**: Chat with the AI mentor for hints and guidance

You can switch between tabs using:
- Mouse clicks on the tab headers
- Keyboard shortcuts: `1` (Terminal), `2` (Level Info), `3` (AI Mentor)
- The tabbed interface at the top

### SSH Connection

1. In the Terminal tab, enter your Bandit username, password, and port (default 2220)
2. Click "Connect" to establish an SSH connection to the Bandit server
3. Once connected, you can enter commands in the terminal input field
4. Use the "Disconnect" button to close the SSH connection

### Command History

- Use the up/down arrow keys in the command input field to navigate through command history
- Command history is persistent across sessions
- History is automatically saved and loaded

### Level Navigation

In the Level Info tab:
- Use the "Previous Level" and "Next Level" buttons to navigate between levels
- View level goals, recommended commands, and reading materials

### AI Mentor

In the AI Mentor tab:
- Type your question in the input field and press Enter or click "Send"
- The AI mentor will provide hints and guidance based on the current level and context
- View the conversation history in the chat display

### Session Management

- Sessions are automatically created and saved when you connect to a server
- Session information includes hostname, port, username, and current level
- Sessions persist across application restarts

### Offline Mode

- Press `o` to toggle offline mode
- In offline mode, you can view level information and review previous sessions
- SSH connections and AI mentor are disabled in offline mode
- The application subtitle indicates when offline mode is active

## Keyboard Shortcuts

- `d`: Toggle dark mode
- `q`: Quit the application
- `1`: Switch to Terminal tab
- `2`: Switch to Level Info tab
- `3`: Switch to AI Mentor tab
- `o`: Toggle offline mode

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
│   ├── app.tcss             # CSS styling for the application
├── bandit_levels.json       # Level data scraped from OverTheWire
├── requirements.txt         # Python dependencies
├── README.md               # This file
└── .env                    # Environment variables (not included in repo)
```

## Technology Stack

- **Framework**: Textual (Python TUI framework)
- **SSH Client**: Paramiko for secure connections
- **AI Integration**: OpenAI API (GPT-3.5)
- **Data**: JSON file containing scraped level data from OverTheWire
- **Caching**: File-based caching system for improved performance

## Troubleshooting

### Common Issues and Solutions

#### SSH Connection Fails
- Verify port 2220 is accessible
- Check your network connection and firewall settings
- Ensure your credentials are correct
- Try using a different network if behind a restrictive firewall

#### AI Mentor Not Working
- Verify `OPENAI_API_KEY` is set correctly
- Check API key validity and billing status
- Ensure internet connectivity
- Check [OpenAI's API status](https://status.openai.com/)

#### Command History Not Saving
- Verify write permissions for `~/.bandit_cli/` directory
- Check available disk space
- Try restarting the application

#### Terminal Display Issues
- Try resizing your terminal window
- Check terminal emulator compatibility
- Ensure your terminal supports UTF-8

#### Level Information Missing
- Note that only levels 0-5 are currently available
- Visit [OverTheWire Bandit](https://overthewire.org/wargames/bandit/) for other levels
- Check for application updates that might add more levels

#### Application Won't Start
- Verify Python 3.8+ is installed
- Check all dependencies are installed: `pip install -r requirements.txt`
- Look for conflicting packages in your Python environment
- Check the terminal for specific error messages

For additional help, see [SECURITY.md](SECURITY.md) for security-related issues or open an issue on GitHub.

## Development

### Code Quality Tools

This project uses modern Python code quality tools:

- **Black**: Code formatting (`black src/ tests/`)
- **Ruff**: Linting and code analysis (`ruff check src/ tests/`)
- **MyPy**: Type checking (`mypy src/`)

### Development Setup

1. Install development dependencies:
   ```bash
   pip install -r requirements-dev.txt
   ```

2. Format code:
   ```bash
   black src/ tests/
   ```

3. Run linting:
   ```bash
   ruff check src/ tests/
   ```

4. Type checking:
   ```bash
   mypy src/
   ```

5. Run tests:
   ```bash
   pytest tests/
   ```

### Code Standards

- All public functions and classes must have comprehensive docstrings in Google style
- All functions must have type hints
- Code should follow PEP 8 standards (enforced by Black and Ruff)
- New features should include appropriate tests

## Contributing

We welcome contributions of all kinds! See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines on:

- Code style and standards (PEP 8, type hints)
- Testing requirements and processes
- Pull request workflow
- Types of contributions we accept

Quick start:
1. Fork the repository
2. Create a feature branch
3. Make your changes following our guidelines
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License - see [LICENSE](LICENSE) for details.

Created for educational purposes to help users learn cybersecurity concepts through the OverTheWire Bandit wargame.

## Security

We take security seriously in this educational tool. See [SECURITY.md](SECURITY.md) for:

- Data handling and privacy policies
- SSH security considerations
- OpenAI API data sharing details
- Security best practices for users
- Responsible disclosure policy

## Acknowledgments

- [OverTheWire](https://overthewire.org/) for providing the Bandit wargame
- [Textual](https://github.com/Textualize/textual) for the terminal user interface framework
- [OpenAI](https://openai.com/) for AI mentor capabilities 
 