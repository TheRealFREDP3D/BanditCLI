# _DEV_ Directory

This directory contains development artifacts and design documentation for the BanditCLI project.

## Purpose

The `_DEV_` directory serves as a workspace for development-related documents that are not part of the final product but are valuable for understanding the project's evolution and design decisions.

## Structure

### Active Documentation

- `app_design.md` - Core design documentation that remains relevant to active development
- `v0.2-Review.md` - Version 0.2 review document with implementation feedback

### Archived Documentation  

- `archive/` - Historical development artifacts that may have reference value but are not actively used
  - `BanditCLI-Gemini Review.md` - Review document from external assessment

### Gitignored Files

The following files are tracked in `.gitignore` and should not be committed:
- `CONVERSION_SUMMARY.md` - Migration documentation
- `Refining points for v0.2.md` - Version planning notes  
- `sample_config.json` - Example configuration
- `v0.2_*` files - Version-specific implementation documentation

## Guidelines

- **Active docs**: Keep in root `_DEV_/` directory (e.g., `app_design.md`)
- **Historical docs**: Move to `archive/` subdirectory
- **Draft files**: Use `.draft` extension (automatically gitignored)
- **Work in progress**: Use `.wip` extension (automatically gitignored)

## What Belongs Here vs docs/

- `_DEV_/` - Development artifacts, design discussions, implementation notes
- `docs/` - User-facing documentation, API docs, user guides
