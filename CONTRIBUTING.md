# Contributing to BanditCLI

## Welcome and Project Overview

Welcome to BanditCLI! We're excited to have you contribute to this educational terminal-based interface for the OverTheWire Bandit wargame.

BanditCLI is designed to help users learn cybersecurity concepts through hands-on practice in a controlled, educational environment. We value all contributions, whether they're code, documentation, bug reports, or feature suggestions.

## Code of Conduct

We are committed to providing a welcoming and inclusive environment for all contributors. Please be respectful, collaborative, and constructive in all interactions.

## Getting Started

### Development Setup

1. Fork the repository on GitHub
2. Clone your fork locally
3. Create virtual environment: `python -m venv venv`
4. Activate virtual environment
5. Install dependencies: `pip install -r requirements.txt`
6. Copy `.env.example` to `.env` and configure
7. Run tests: `pytest` to verify setup

### Project Structure

- `src/`: Main application code
- `tests/`: Unit and integration tests
- `docs/`: Documentation files
- `_DEV_/`: Development notes (not for production)

## Code Style and Standards

### Python Style Guidelines

- Follow PEP 8 style guide
- Use 4 spaces for indentation (no tabs)
- Maximum line length: 100 characters (flexible for readability)
- Use meaningful variable and function names

### Type Hints

- Required for all public functions and methods
- Use `typing` module: `Optional`, `List`, `Dict`, `Callable`, etc.
- Example: `def connect(self) -> bool:`

### Docstrings

- Required for all public classes, methods, and functions
- Use Google-style or NumPy-style docstrings consistently
- Include: Description, Args, Returns, Raises (if applicable)

### Import Organization

- Standard library imports first
- Third-party imports second
- Local imports last
- Alphabetically sorted within each group

### Error Handling

- Use try-except blocks for external operations (SSH, API calls, file I/O)
- Provide meaningful error messages via `notify_callback`

## Testing Requirements

### Test Coverage

- All new features must include tests
- Aim for 80%+ code coverage
- Use pytest framework

### Test Structure

- Place tests in `tests/` directory
- Name test files: `test_<module_name>.py`
- Use class-based organization: `class Test<ClassName>:`
- Test method naming: `test_<functionality>`
- Include docstrings for test classes and methods

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_config.py

# Run specific test
pytest tests/test_config.py::TestConfigManager::test_init_with_default_config
```

### Test Fixtures

- Use pytest fixtures for common setup
- Use `tmp_path` fixture for file operations

### Mocking

- Mock external services (SSH connections, OpenAI API)
- Use `unittest.mock` or `pytest-mock`
- Example: Mock `litellm.completion` for AI mentor tests

## Pull Request Process

### Before Submitting

1. Create a feature branch: `git checkout -b feature/your-feature-name`
2. Make your changes following code style guidelines
3. Add/update tests for your changes
4. Run tests locally: `pytest`
5. Update documentation if needed (README, docstrings)
6. Commit with clear, descriptive messages

### Commit Message Format

- Use present tense: "Add feature" not "Added feature"
- First line: Brief summary (50 chars or less)
- Blank line, then detailed description if needed
- Reference issues: "Fixes #123" or "Relates to #456"

### Submitting Pull Request

1. Push to your fork: `git push origin feature/your-feature-name`
2. Open PR against `main` branch
3. Fill out PR template (if available)
4. Describe what changed and why
5. Link related issues
6. Request review from maintainers

### PR Review Process

- Maintainers will review within 3-5 business days
- Address feedback by pushing new commits to your branch
- Once approved, maintainers will merge
- PR may be closed if inactive for 30+ days

## Types of Contributions

### Bug Reports

- Use GitHub Issues
- Include: Steps to reproduce, expected vs actual behavior, environment details
- Check existing issues first to avoid duplicates

### Feature Requests

- Use GitHub Issues with "enhancement" label
- Describe the problem and proposed solution
- Discuss before implementing large features

### Documentation

- Improvements to README, docstrings, or docs/ files
- Fixing typos, clarifying instructions
- Adding examples or tutorials

### Code Contributions

- Bug fixes
- New features (discuss first for large changes)
- Performance improvements
- Test coverage improvements

## Development Guidelines

### Dependencies

- Avoid adding new dependencies unless necessary
- If adding dependency, justify in PR description
- Ensure license compatibility (prefer MIT, Apache 2.0, BSD)
- Update `requirements.txt` with pinned versions

### Backwards Compatibility

<<<<<<< HEAD
- Maintain compatibility with Python 3.8+
=======
- Maintain compatibility with Python 3.9+

>>>>>>> 6be3a2c628ef45c26c051eaa8287e7ee264bfd30
- Avoid breaking changes to public APIs
- Deprecate features before removing (with warnings)

### Performance

- Consider caching for expensive operations
- Avoid blocking the UI thread (use threading for I/O)
- Profile code for performance bottlenecks if needed

## Questions and Support

- GitHub Discussions for questions
- GitHub Issues for bugs and features
- Check existing issues and discussions first
- Be patient and respectful when asking for help

## Recognition

- Contributors will be recognized in release notes
- Significant contributions may be highlighted in README
- Thank you for contributing to BanditCLI!
