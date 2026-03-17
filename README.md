# BanditCLI

A terminal interface for the [OverTheWire Bandit](https://overthewire.org/wargames/bandit/)
wargame with an integrated AI mentor, persistent sessions, and automatic
level-completion detection.

---

## Features

| Feature | Description |
|---|---|
| **SSH Terminal** | Full interactive SSH session inside a Textual TUI |
| **AI Mentor** | GPT-powered hints that guide without giving answers (requires `OPENAI_API_KEY`) |
| **Level Info** | Built-in goal, commands, and reading materials for all 34 levels |
| **Session Management** | Create, switch, and persist multiple named sessions |
| **Command History** | Persistent up/down arrow history across restarts |
| **Auto Password Detection** | Scans output for Bandit passwords and offers one-click next-level login |
| **Auto-save** | Debounced background saving of terminal history and AI conversations |
| **Performance Monitor** | Optional memory and timing metrics via `psutil` |

---

## Quick Start

### Prerequisites

- Python 3.11+
- `pip install -r requirements.txt`

### Environment

Copy `.env.example` to `.env` and fill in your keys:
```env
# Required for AI Mentor
OPENAI_API_KEY=sk-...

# Optional: override the default model
OPENAI_MODEL=gpt-3.5-turbo

# Optional: disable SSH host-key verification (not recommended)
BANDIT_CLI_INSECURE=false
```

### Run
```bash
python -m src.main
# or, if installed as a package:
bandit-cli
```

---

## How Password Detection Works

1. Every chunk of SSH output is passed through `PasswordDetector.feed()`.
2. A regex `\b([A-Za-z0-9]{32})\b` scans for 32-character tokens — the format
   used by all Bandit passwords.
3. When a new (not-yet-seen) password is found:
   - It is stored in the active session under `recovered_passwords[current_level]`.
   - The current level is marked complete.
   - Progress is force-saved to disk.
   - A `LevelCompleteModal` appears with the password and a
     **"Login to Level N →"** button.
4. Clicking the button disconnects the current SSH session, pre-fills the
   credentials, and reconnects as `bandit(N+1)` automatically.
5. The detector resets on every disconnect to avoid stale matches.

A 5-second cooldown between successive detections prevents a single `cat`
command that echoes the password multiple times from triggering the modal
more than once.

---

## Project Layout
```
src/
├── __init__.py            # Package version
├── main.py                # Textual app, PasswordDetector, LevelCompleteModal
├── ssh_manager.py         # SSHConnection, SSHManager, SSHConnectionPool
├── session_manager.py     # Session, SessionManager (includes recovered_passwords)
├── ai_mentor.py           # BanditAIMentor (LiteLLM)
├── level_info.py          # BanditLevelInfo
├── terminal_output.py     # EnhancedTerminalOutput, ANSIColorParser
├── command_history.py     # CommandHistory
├── config.py              # ConfigManager
├── cache.py               # File-based Cache
├── performance_monitor.py # PerformanceMonitor
├── app.tcss               # Textual CSS
├── bandit_levels.json     # Level data (goals, commands, reading materials)
└── ai_mentor_data.json    # Hint and command explanation data
```

---

## Configuration

All settings live in `~/.bandit_cli/config.json` and are managed by
`ConfigManager`. The defaults are:
```json
{
  "ssh":     { "host": "bandit.labs.overthewire.org", "port": 2220, "timeout": 10 },
  "ui":      { "theme": "dark", "max_recent_commands": 10 },
  "ai":      { "model": "gpt-3.5-turbo", "max_context_commands": 3, "fallback": true },
  "history": { "max_commands": 100, "persist": true },
  "cache":   { "enable": true, "path": "~/.bandit_cli/cache" }
}
```

---

## Keyboard Shortcuts

| Key | Action |
|---|---|
| `1` – `4` | Switch tabs (Terminal / Session / Level Info / AI Mentor) |
| `Ctrl+S` | Force-save progress |
| `N` | New session |
| `W` | Switch session dialog |
| `D` | Toggle dark mode |
| `Q` | Quit |
| `↑` / `↓` | Navigate command history (when input is focused) |
| `Ctrl+E` | Export terminal output (inside terminal widget) |
| `Ctrl+L` | Clear terminal output |