# Changelog

## v0.2.0 (2025-09-19)

### Added
- Comprehensive unit testing framework with 77 passing tests
- Command history functionality with up/down arrow navigation
- Persistent command history storage
- Session management with creation, persistence, and switching
- Offline mode for working without internet connection
- Performance optimizations through intelligent caching
- Enhanced error handling and input validation
- Configuration file system with loading and saving
- Keyboard shortcut for toggling offline mode ('o')

### Changed
- Improved SSH connection error messages with specific failure types
- Enhanced input validation for SSH credentials and port numbers
- Added command length validation (max 1000 characters)
- Added AI mentor message length validation (max 1000 characters)
- Improved terminal output rendering with auto-scrolling
- Enhanced level navigation with bounds checking
- Updated UI to show offline mode status in subtitle
- Improved configuration management with default values and validation

### Fixed
- SSH connection error handling for various failure types
- Command history deduplication
- Session persistence and management
- Cache expiration and persistence
- Level information formatting and display
- AI mentor response handling and error recovery

### Security
- Added input sanitization for SSH credentials
- Added validation for dangerous commands
- Implemented graceful degradation for failed components

### Performance
- Added caching for level information, AI hints, and command explanations
- Optimized terminal output rendering
- Improved configuration loading with lazy loading
- Added file-based caching system with expiration

## v0.1.0 (2025-09-15)

### Added
- Initial release with basic SSH terminal interface
- Level information display
- AI mentor system with OpenAI integration
- Tabbed interface for navigation
- Basic error handling