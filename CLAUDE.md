# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository is organized into two main components:

1. **Environment Tools** (`/scripts`, `/config`, `/tests`) - Cross-platform setup scripts to install development environments with AI coding assistants (Claude, Codex, Gemini) on Windows and macOS
2. **Project Tools** (`/packages/cli`) - Python CLI (`aftr`) for scaffolding data science projects with best practices

## Architecture

### Environment Tools

Hybrid shell + TypeScript approach: shell scripts bootstrap the package manager and bun, then hand off to a cross-platform TypeScript script.

- **config/config.json**: Central configuration file defining all packages for both platforms.
- **scripts/setup.ps1**: Windows bootstrap (PowerShell). Installs Scoop, git, packages, bun, then calls setup.ts. Supports `irm URL | iex` remote execution.
- **scripts/setup.sh**: macOS bootstrap (Bash). Installs Homebrew, packages, bun, then calls setup.ts. Requires jq for JSON parsing.
- **scripts/setup.ts**: Cross-platform TypeScript (runs via bun). Handles mise tools, bun globals, shell profiles, and SSH key setup.
- **scripts/setup-github.ts**: GitHub configuration script (TypeScript with bun). Sets up branch protection, required reviews, status checks, and secrets for publishing.
- **tests/test-setup.ps1**: Test runner using Windows Sandbox to validate setup.ps1 in isolation.

### Project Tools

Python-based CLI tool built with Typer, Rich, and InquirerPy.

- **packages/cli/src/aftr/cli.py**: Main entry point with interactive menu and ASCII art banner.
- **packages/cli/src/aftr/commands/init.py**: Project scaffolding logic.
- **packages/cli/tests/test_init.py**: 14 tests covering CLI behavior.

## Commands

### Environment Tools

#### Run Setup Locally

```powershell
# Windows
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1

# macOS
bash scripts/setup.sh
```

#### Configure GitHub Repository

```bash
# Set up branch protection, status checks, and secrets
bun run scripts/setup-github.ts
```

#### Test in Windows Sandbox

```powershell
# Enable sandbox feature (requires restart)
.\tests\test-setup.ps1 -EnableSandbox

# Run test
.\tests\test-setup.ps1 -RunTest
```

### Project Tools

#### Install aftr

```bash
uv tool install aftr
```

#### Create a New Project

```bash
# Interactive mode
aftr

# Direct creation
aftr init my-project
aftr init my-project --path /custom/path
```

#### Develop aftr

```bash
cd packages/cli
uv sync
uv run pytest tests/ -v
```

## Package Managers

### Environment Tools
- **Windows**: Scoop (buckets: extras, nerd-fonts)
- **macOS**: Homebrew (tap: homebrew/cask-fonts)
- **Both**: Bun for global npm packages (claude-code, codex, gemini-cli)

### Project Tools
- **Both**: UV for Python packages (aftr CLI)

## Key Patterns

### Environment Tools
- Scripts are idempotent - check if packages/configs already exist before installing
- Config changes cascade to both platforms - edit config.json, not the scripts
- Remote execution supported on Windows via config fetch from GitHub
- Test artifacts (test-sandbox.wsb, test-wrapper.ps1) are gitignored and generated at runtime

### Project Tools
- Project scaffolding follows opinionated structure: data/, notebooks/, outputs/, src/
- Hyphenated project names convert to underscores for Python modules
- All generated projects include .mise.toml for reproducible environments
- Notebooks include papermill parameter tags for automated execution
