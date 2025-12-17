# Security Policy

## Security Overview

BanditCLI is committed to maintaining a secure educational tool for learning cybersecurity concepts through the OverTheWire Bandit wargame. This document outlines our security practices, data handling policies, and procedures for reporting security vulnerabilities.

**Scope**: This tool handles SSH credentials and sends terminal data to third-party APIs for AI assistance. Users should be aware of the security implications of using this educational tool.

## Data Handling and Privacy

### SSH Password Security

- **In-memory storage**: SSH passwords are stored in memory only during active sessions (reference `src/ssh_manager.py` lines 18, 39)
- **Automatic cleanup**: Passwords are cleared from memory on disconnect (line 140)
- **No persistence**: Passwords are NOT logged or persisted to disk
- **Host key policy**: The tool uses `paramiko.AutoAddPolicy()` which automatically accepts unknown host keys without verification (lines 33, 59)
- **Security warning**: This automatic host key acceptance creates a man-in-the-middle (MITM) vulnerability. Users should verify host keys manually for production use

### OpenAI API Data Sharing

The AI mentor feature sends the following data to OpenAI API (reference `src/ai_mentor.py` lines 114-125):

- Current Bandit level number
- Last 5 commands entered by the user
- Last 500 characters of terminal output
- User's chat messages and conversation history

**Important notes**:

- OpenAI's data usage policy applies to all transmitted data
- API key is read from environment variable `OPENAI_API_KEY` and is never logged
- AI mentor can be disabled by not setting the API key
- Users should review what data is sent before enabling this feature

### Environment Variables

Sensitive environment variables from `.env.example`:

- `OPENAI_API_KEY` (sensitive - never commit)
- `OPENAI_MODEL`
- SSH configuration variables

**Security practice**: `.env` is included in `.gitignore` to prevent accidental commits of sensitive data.

## Security Best Practices for Users

- **API keys**: Always use `.env` file for API keys, never hardcode them in source code
- **Data awareness**: Review what data is sent to OpenAI before enabling AI mentor
- **Sensitive information**: Be cautious when entering sensitive information in terminal (it may be sent to OpenAI)
- **Password security**: Use strong, unique passwords for Bandit levels
- **Host verification**: Verify SSH host keys when connecting to new servers
- **Dependencies**: Keep dependencies updated with `pip install --upgrade -r requirements.txt`

## Known Security Considerations

- **Host key policy**: `paramiko.AutoAddPolicy()` automatically trusts all host keys (MITM risk)
- **Input validation**: No input sanitization for SSH commands (by design for learning purposes)
- **Data transmission**: Terminal output is sent to OpenAI API (privacy consideration)
- **Local storage**: No encryption for local cache files in `~/.bandit_cli/cache`

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
