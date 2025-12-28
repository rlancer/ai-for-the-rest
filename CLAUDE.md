# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository provides cross-platform setup scripts to install a development environment with AI coding assistants (Claude, Codex, Gemini) on Windows and macOS.

## Architecture

Hybrid shell + TypeScript approach: shell scripts bootstrap the package manager and bun, then hand off to a cross-platform TypeScript script.

- **config/config.json**: Central configuration file defining all packages for both platforms.
- **scripts/setup.ps1**: Windows bootstrap (PowerShell). Installs Scoop, git, packages, bun, then calls setup.ts. Supports `irm URL | iex` remote execution.
- **scripts/setup.sh**: macOS bootstrap (Bash). Installs Homebrew, packages, bun, then calls setup.ts. Requires jq for JSON parsing.
- **scripts/setup.ts**: Cross-platform TypeScript (runs via bun). Handles mise tools, bun globals, shell profiles, and SSH key setup.
- **scripts/setup-github.ts**: GitHub configuration script (TypeScript with bun). Sets up branch protection, required reviews, status checks, and secrets for publishing.
- **tests/test-setup.ps1**: Test runner using Windows Sandbox to validate setup.ps1 in isolation.

## Commands

### Run Setup Locally

```powershell
# Windows
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1

# macOS
bash scripts/setup.sh
```

### Configure GitHub Repository

```bash
# Set up branch protection, status checks, and secrets
bun run scripts/setup-github.ts
```

### Test in Windows Sandbox

```powershell
# Enable sandbox feature (requires restart)
.\tests\test-setup.ps1 -EnableSandbox

# Run test
.\tests\test-setup.ps1 -RunTest
```

## Package Managers

- **Windows**: Scoop (buckets: extras, nerd-fonts)
- **macOS**: Homebrew (tap: homebrew/cask-fonts)
- **Both**: Bun for global npm packages (claude-code, codex, gemini-cli)

## Key Patterns

- Scripts are idempotent - check if packages/configs already exist before installing
- Config changes cascade to both platforms - edit config.json, not the scripts
- Remote execution supported on Windows via config fetch from GitHub
- Test artifacts (test-sandbox.wsb, test-wrapper.ps1) are gitignored and generated at runtime

## aftr CLI (packages/cli)

Python CLI tool for scaffolding data science projects. Built with Typer and Rich.

### Usage

```bash
# Install
uv tool install aftr

# Create a new project
aftr my-project
aftr my-project --path /custom/path
```

### What it creates

```
my-project/
├── data/              # Input data (gitignored)
├── notebooks/         # Jupyter notebooks with example.ipynb
├── outputs/           # Output files (gitignored)
├── src/my_project/    # Python module (hyphens → underscores)
├── .gitignore
├── .mise.toml         # Python 3.12, UV latest
├── pyproject.toml     # pandas, polars, jupyter, papermill
└── README.md
```

### Development

```bash
cd packages/cli
uv sync
uv run pytest tests/ -v
```

### Key files

- **packages/cli/src/aftr/cli.py**: Main entry point, registers init command
- **packages/cli/src/aftr/commands/init.py**: Project scaffolding logic
- **packages/cli/tests/test_init.py**: 14 tests covering CLI behavior
