# Security Policy

## Security Overview

BanditCLI is committed to maintaining a secure educational tool for learning cybersecurity concepts through the OverTheWire Bandit wargame. This document outlines our security practices, data handling policies, and procedures for reporting security vulnerabilities.

**Scope**: This tool handles SSH credentials and sends terminal data to third-party APIs for AI assistance. Users should be aware of the security implications of using this educational tool.

## Data Handling and Privacy

### SSH Password Security

- **In-memory storage**: SSH passwords are stored in memory only during active sessions (reference `src/ssh_manager.py` lines 62, 202)
- **Secure cleanup**: Passwords are overwritten and cleared from memory on disconnect (lines 236-237)
- **No persistence**: Passwords are NOT logged or persisted to disk
- **Configurable host key policy**:
  - Default: Uses `paramiko.RejectPolicy()` with known hosts verification for security (lines 94-100)
  - Optional: Can use `paramiko.AutoAddPolicy()` for educational environments (creates MITM vulnerability)
- **Connection security**: 
  - Retry logic with exponential backoff (3 attempts, lines 107-127)
  - Disabled SSH agent and private key lookups for security (lines 118-119)
  - Connection timeout and proper error handling
- **Security warnings**: Users are warned when using insecure host key policies

### OpenAI API Data Sharing

The AI mentor feature sends the following data to OpenAI API (reference `src/ai_mentor.py` lines 147-151):

- User messages and conversation history
- Current Bandit level number
- Last 5 commands entered by the user (if recent_commands provided)
- Last 500 characters of terminal output (if terminal_output provided)

**Privacy protections**:

- **Opt-out capability**: Users can disable AI mentor completely via opt-out flag
- **Data minimization**: Only limited command history and terminal output are sent
- **No sensitive credentials**: Passwords and API keys are never sent to OpenAI
- **Local fallback**: Predefined hints and command explanations are available without API calls

**Important notes**:

- OpenAI's data usage policy applies to all transmitted data
- API key is read from environment variable `OPENAI_API_KEY` and is never logged or displayed
- AI mentor can be disabled by not setting the API key or using opt-out flag
- Users should review what data is sent before enabling this feature

### Environment Variables

Sensitive environment variables from `.env.example`:

- `OPENAI_API_KEY` (sensitive - never committed to version control)
- `OPENAI_MODEL`
- `BANDIT_CLI_INSECURE` (optional - disables host key verification)
- SSH configuration variables

**Security practices**:
- `.env` is included in `.gitignore` to prevent accidental commits of sensitive data
- API keys are accessed via `os.getenv()` and never logged or displayed
- Sensitive data is validated and sanitized before use

## Security Best Practices for Users

- **API keys**: Always use `.env` file for API keys, never hardcode them in source code
- **Data awareness**: Review what data is sent to OpenAI before enabling AI mentor
- **Privacy opt-out**: Use AI mentor opt-out if concerned about data privacy
- **Sensitive information**: Be cautious when entering sensitive information in terminal (it may be sent to OpenAI)
- **Password security**: Use strong, unique passwords for Bandit levels
- **Host verification**: Default settings use secure host key verification; only disable for trusted environments
- **Input validation**: The application validates all user inputs to prevent injection attacks
- **Dependencies**: Keep dependencies updated with `pip install --upgrade -r requirements.txt`

## Known Security Considerations

- **Host key policy**: Configurable host key verification (default secure, optional insecure for educational use)
- **Input validation**: Comprehensive input sanitization prevents command injection attacks
- **Data transmission**: Terminal output is sent to OpenAI API (privacy consideration with opt-out available)
- **Local storage**: No encryption for local cache files in `~/.bandit_cli/cache`
- **Memory security**: Passwords are securely overwritten in memory after use

## Responsible Disclosure Policy

### Reporting Security Vulnerabilities

**Preferred method**: GitHub Security Advisories (private reporting)
**Alternative**: Email to project maintainer

### Response Process

- **Acknowledgment**: 48-72 hours for initial acknowledgment
- **Resolution timeline**: Depends on severity and complexity
- **Disclosure**: Please allow reasonable time for fixes before public disclosure
- **Recognition**: Security researchers will be credited (unless they prefer anonymity)

### Vulnerability Reports

Please provide:

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Any suggested fixes or mitigations

## Supported Versions

| Version | Security Support | Status |
|---------|------------------|--------|
| v0.2.0 (latest) | Full support | Active |
| Older versions | Best effort support | Limited |

## Security Update Process

- **Patch releases**: Security fixes will be released as patch versions
- **Critical vulnerabilities**: Will be announced in GitHub Releases
- **User notification**: Users should subscribe to repository releases for notifications

---

Thank you for helping keep BanditCLI secure!
