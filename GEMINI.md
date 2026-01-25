# BanditCLI Project Context

## Project Overview

**BanditCLI** is a terminal-based interface for playing the [OverTheWire Bandit wargame](https://overthewire.org/wargames/bandit/). It provides a modern, interactive environment to learn cybersecurity concepts.

**Key Features:**
*   **SSH Terminal:** Integrated SSH client (via Paramiko) to connect to Bandit labs.
*   **Level Intelligence:** Displays level goals and tips (scraped/cached data).
*   **AI Mentor:** Context-aware AI assistance using OpenAI/LiteLLM.
*   **Session Management:** Saves progress (host, port, user, level).
*   **Offline Mode:** Access level data without an internet connection.

**Architecture:**
*   **Frontend:** Built with [Textual](https://textual.textualize.io/) for a rich Terminal User Interface (TUI).
*   **Backend:** Python 3.8+ handling SSH connections, data caching, and AI logic.
*   **Data:** Level data is stored in `src/bandit_levels.json`.

## Building and Running

### Prerequisites
*   Python 3.8+
*   OpenAI API Key (optional, for AI features)

### Setup
```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Install dev dependencies (for testing/linting)
pip install -r requirements-dev.txt

# Set environment variable
export OPENAI_API_KEY="your-key"
```

### Execution
Run the application directly:
```bash
python -m src.main
```
Or via the installed script (if installed via pip):
```bash
bandit-cli
```

### Testing & Quality
The project uses `pytest` for testing and standard Python tools for quality control.

```bash
# Run tests
pytest

# Format code
black src/ tests/

# Lint code
ruff check src/ tests/

# Type check
mypy src/
```

## Development Conventions

### Code Style
*   **Formatting:** Strictly follows **Black** formatting rules.
*   **Linting:** Enforced via **Ruff**.
*   **Type Hints:** Mandatory for all public functions/methods (`mypy` strictness).
*   **Docstrings:** Google-style docstrings required for all public classes and functions.

### Directory Structure
*   `src/`: Main source code.
    *   `main.py`: Entry point and TUI layout.
    *   `ssh_manager.py`: Paramiko wrapper for SSH connections.
    *   `ai_mentor.py`: AI integration logic.
    *   `bandit_levels.json`: Static data for game levels.
*   `tests/`: `pytest` suite.
*   `docs/`: Architecture and API documentation.

### Contribution Guidelines
*   New features must have accompanying tests.
*   Aim for >80% test coverage.
*   Avoid adding new dependencies unless critical.
*   Ensure cross-platform compatibility (Linux/Windows/Mac).
