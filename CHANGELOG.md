# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.2] - 2026-01-18

### Added
- Performance monitoring system with real-time metrics tracking
- Response quality tracking in AI mentor for improved hint generation
- SSH connection pooling for better resource management
- Virtual scrolling with 50K line buffer for large terminal outputs
- Enhanced error handling with user-friendly error messages
- Legacy file migration system for command history and sessions
- Comprehensive documentation suite (GEMINI.md, QWEN.md, architecture.md, api.md)
- Advanced caching mechanisms with intelligent invalidation
- Integration test suite for end-to-end validation
- Input validation framework for enhanced security
- Performance profiling tools for development and debugging
- Code quality tools integration (Black, Ruff, MyPy)

### Changed
- Improved AI mentor response quality with enhanced context tracking
- Optimized terminal output rendering with virtual scrolling
- Enhanced SSH connection management with connection pooling
- Updated caching strategy for better performance
- Improved error messaging for better user experience
- Refactored command history storage for better reliability
- Enhanced session management with migration support

### Fixed
- Resolved memory leaks in long-running terminal sessions
- Fixed SSH connection timeout issues
- Corrected AI mentor context preservation problems
- Fixed command history persistence edge cases
- Resolved performance monitoring overhead issues
- Fixed validation errors in user input handling
- Corrected test coverage reporting accuracy

### Features
- Real-time SSH connection to bandit.labs.overthewire.org
- Interactive terminal with command history navigation
- Context-aware AI mentor responses
- Tabbed interface (Terminal, Level Info, AI Mentor)
- Keyboard shortcuts for navigation
- Security validation for user inputs
- Cross-platform compatibility

### Security
- Input validation for SSH credentials
- Safe command handling
- No sensitive data sent to AI services

### Documentation
- Comprehensive README with installation and usage instructions
- Security documentation
- Contributing guidelines
- API documentation

### Dependencies
- Textual 0.80.0 for terminal UI
- Paramiko 4.0.0 for SSH connections
- OpenAI 1.99.9 for AI mentor functionality
- LiteLLM 1.61.15 for AI model abstraction
- BeautifulSoup4 4.13.4 for web scraping
- Requests 2.32.4 for HTTP operations
- Python-dotenv 1.0.1 for environment management

## [Unreleased]

### Planned
- Support for additional Bandit levels (6-33)
- Enhanced AI mentor capabilities
- Performance monitoring dashboard
- Additional terminal emulators support
- Plugin system for custom mentors

---

## Version History

- **0.2.2** - Performance monitoring and enhanced error handling release
- **0.2.0** - Initial stable release with core functionality
- **0.1.x** - Development versions (not publicly released)
