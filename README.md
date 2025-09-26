# Bandit Wargame CLI

A terminal-based interface for playing the OverTheWire Bandit wargame, built with Python and the Textual framework. This CLI application provides a simplified interface for playing the challenges, featuring:

- SSH Terminal Interface: Real-time SSH connection to the Bandit server
- Level Information Display: View level goals, recommended commands, and reading materials
- AI Mentor System: Get contextual hints and guidance without revealing solutions
- Command History: Navigate through previously entered commands
- Session Management: Save and switch between multiple sessions
- Offline Mode: Access level information and review sessions without internet
- Caching: Improved performance through intelligent caching of frequently accessed data

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
5. Set your OpenAI API key as an environment variable:
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

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is created for educational purposes. Please respect the OverTheWire terms of service when using this tool.

## Acknowledgments

- [OverTheWire](https://overthewire.org/) for providing the Bandit wargame
- [Textual](https://github.com/Textualize/textual) for the terminal user interface framework
- [OpenAI](https://openai.com/) for AI mentor capabilities