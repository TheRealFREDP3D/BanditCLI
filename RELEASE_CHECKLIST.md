# Release Checklist for BanditCLI

Use this checklist when preparing a new release of BanditCLI.

## Pre-Release Preparation

### Code Quality

- [ ] All code formatted with Black: `python -m black src/ tests/`
- [ ] No linting errors: `python -m ruff check src/ tests/`
- [ ] Type checking passes: `python -m mypy src/`
- [ ] All critical tests pass: `python -m pytest tests/ -v`
- [ ] Test coverage ≥80%: `python -m pytest tests/ --cov=src --cov-report=term-missing`

### Version Management

- [ ] Version updated in `pyproject.toml`
- [ ] Version updated in `src/__init__.py`
- [ ] Version badge updated in `README.md`
- [ ] CHANGELOG.md updated with:
  - [ ] Release date
  - [ ] New features
  - [ ] Bug fixes
  - [ ] Breaking changes (if any)
  - [ ] Dependency updates

### Documentation

- [ ] README.md reviewed and up-to-date
- [ ] Installation instructions tested
- [ ] Usage examples verified
- [ ] Screenshots/GIFs current (if applicable)
- [ ] All links in documentation working
- [ ] API documentation updated (if changed)

### Security & Dependencies

- [ ] Security audit passed: `pip-audit -r requirements.txt`
- [ ] No known critical vulnerabilities
- [ ] Dependencies reviewed for updates
- [ ] SECURITY.md updated if needed

### Package Metadata

- [ ] Author email is valid and monitored
- [ ] License classifier present in `pyproject.toml`
- [ ] Project URLs populated (Homepage, Repository, Bug Tracker)
- [ ] All classifiers accurate

## Build & Test

### Local Build

- [ ] Clean previous builds: `rm -rf dist/ build/ *.egg-info`
- [ ] Build distributions: `python -m build`
- [ ] Verify artifacts created:
  - [ ] Source distribution (`.tar.gz`)
  - [ ] Wheel distribution (`.whl`)
- [ ] Package metadata valid: `python -m twine check dist/*`

### Installation Test

- [ ] Create fresh virtual environment
- [ ] Install from wheel: `pip install dist/bandit_cli-X.Y.Z-py3-none-any.whl`
- [ ] Verify entry point works: `bandit-cli --help` or `bandit-cli`
- [ ] Test core functionality:
  - [ ] Application launches
  - [ ] UI renders correctly
  - [ ] SSH connection works (if accessible)
  - [ ] AI Mentor responds (if API key configured)
  - [ ] Offline mode toggles correctly

## Publish

### Git Operations

- [ ] All changes committed
- [ ] Working directory clean: `git status`
- [ ] Create git tag: `git tag vX.Y.Z`
- [ ] Push commits: `git push origin main`
- [ ] Push tag: `git push origin vX.Y.Z`

### PyPI Upload

**First-time or major release:**

- [ ] Upload to TestPyPI: `python -m twine upload --repository testpypi dist/*`
- [ ] Test install from TestPyPI: `pip install --index-url https://test.pypi.org/simple/ bandit-cli`
- [ ] Verify TestPyPI installation works

**Production release:**

- [ ] Upload to PyPI: `python -m twine upload dist/*`
- [ ] Verify package appears on PyPI: <https://pypi.org/project/bandit-cli/>
- [ ] Test install from PyPI: `pip install bandit-cli`

### GitHub Release

- [ ] Create GitHub release from tag
- [ ] Copy CHANGELOG entry to release notes
- [ ] Attach distribution files (optional):
  - [ ] `.tar.gz` source distribution
  - [ ] `.whl` wheel distribution
- [ ] Publish release

## Post-Release

### Verification

- [ ] Install from PyPI in clean environment
- [ ] Run smoke tests
- [ ] Check PyPI project page renders correctly
- [ ] Verify documentation links work

### Communication

- [ ] Update project status badges (if needed)
- [ ] Announce release (if applicable):
  - [ ] Social media
  - [ ] Mailing list
  - [ ] Community forums

### Maintenance

- [ ] Update version to next development version (e.g., `X.Y.Z+1-dev`)
- [ ] Create new `[Unreleased]` section in CHANGELOG.md
- [ ] Close/update related GitHub issues
- [ ] Update project roadmap/milestones

## Notes

### TestPyPI vs PyPI

- **TestPyPI**: Use for testing the release process, especially for first-time releases or major changes
- **PyPI**: Production repository for stable releases

### Rollback Procedure

If issues are discovered post-release:

1. **DO NOT** delete the release from PyPI (it's immutable)
2. Immediately release a patch version (X.Y.Z+1) with fixes
3. Update documentation to note the issue
4. Consider yanking the problematic version: `pip install twine && twine upload --skip-existing dist/*`

### Version Numbering (Semantic Versioning)

- **Patch** (X.Y.Z+1): Backwards-compatible bug fixes
- **Minor** (X.Y+1.0): New backwards-compatible features
- **Major** (X+1.0.0): Breaking changes

## Quick Command Reference

```bash
# Code quality
black src/ tests/
ruff check src/ tests/
mypy src/

# Testing
pytest tests/ -v
pytest tests/ --cov=src --cov-report=term-missing

# Security
pip-audit -r requirements.txt

# Build
python -m build

# Validate
twine check dist/*

# Publish to TestPyPI
twine upload --repository testpypi dist/*

# Publish to PyPI
twine upload dist/*

# Git tagging
git tag vX.Y.Z
git push origin vX.Y.Z
```
