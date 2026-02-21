# Architecture Overview

This document describes how the project is structured for contributors and developers.

## Repository Layout

```
ai-for-the-rest/
├── config/
│   └── config.json          # Central package config for both platforms
├── docs/                    # Documentation (this folder)
├── examples/                # Example scaffolded projects
│   └── nyc-congestion-pricing/
├── packages/
│   └── cli/                 # aftr Python CLI tool
│       ├── src/aftr/
│       ├── tests/
│       └── pyproject.toml
├── scripts/
│   ├── setup.ps1            # Windows bootstrap
│   ├── setup.sh             # macOS bootstrap
│   ├── setup.ts             # Cross-platform TypeScript setup
│   ├── setup-github.ts      # GitHub repo configuration
│   └── publish.ts           # Release publishing
├── tests/
│   └── test-setup.ps1       # Windows Sandbox test runner
├── .github/workflows/       # CI/CD pipelines
├── CLAUDE.md                # AI assistant guidance
└── README.md
```

## Two-Component Design

The project is split into two independent but complementary parts:

### 1. Environment Tools (`/scripts`, `/config`)

Shell scripts that bootstrap a development environment from scratch. Their goal is to go from a bare machine to a fully configured dev environment in one command.

**Setup flow:**

```
User runs setup.ps1 / setup.sh
         │
         ▼
Shell script installs package manager
(Scoop on Windows, Homebrew on macOS)
         │
         ▼
Package manager installs tools
(git, uv, mise, duckdb, starship, VS Code, etc.)
         │
         ▼
Shell script runs: bun run scripts/setup.ts
         │
         ▼
TypeScript handles cross-platform work:
- Installs uv tools (aftr)
- Configures shell profiles (PATH)
- Shows "run aftr setup" instructions
         │
         ▼
User opens new terminal → runs: aftr setup
         │
         ▼
aftr setup installs AI CLI tools interactively
(Claude Code, Codex, Gemini)
```

**Key design decisions:**

- The split between shell scripts and `setup.ts` is intentional. Shell scripts do what only shell can do (install package managers, modify environment for the current session). TypeScript handles everything else for cross-platform consistency.
- Scripts are **idempotent** — re-running them is safe. Each step checks if it's already done.
- `config/config.json` is the single source of truth for which packages are installed on each platform. The scripts read from it, so changes to the package list only require editing one file.
- Claude Code is installed during `setup.ps1` on Windows because it requires the same PowerShell execution context as Scoop. On macOS, it's installed by `aftr setup`.
- Remote execution is supported on Windows via `irm URL | iex` — the script fetches `config.json` from GitHub during execution.

### 2. Project Tools (`/packages/cli`)

`aftr` is a standalone Python CLI that handles:
- Project scaffolding from templates
- Post-install AI tool configuration
- Template management

It is intentionally separate from the environment setup scripts so it can be installed independently with `uv tool install aftr` or run without installation via `uvx aftr`.

---

## aftr CLI Internals

### Entry Point

`packages/cli/src/aftr/cli.py` — Typer app with subcommands. Displays the ASCII banner and routes to subcommands. The interactive main menu (choosing between "New Project", "Setup", "Help") is driven by InquirerPy.

### Commands

| File | Command | Responsibility |
|------|---------|---------------|
| `commands/init.py` | `aftr init` | Scaffold a new project from a template |
| `commands/setup.py` | `aftr setup` | Configure AI tools and SSH keys |
| `commands/config_cmd.py` | `aftr config *` | Template management (list/add/remove/show/update/export/create) |
| `commands/ssh.py` | (called by setup) | SSH key generation and display |

### Template System

Templates are TOML files. The system has two layers:

1. **Built-in default** — `src/aftr/templates/default.toml`. Compiled into the package.
2. **User templates** — Stored in the platform config directory (via `platformdirs`) and tracked in a registry file at `~/.config/aftr/registry.toml`.

Template lifecycle:

```
TOML file (URL or local)
         │
         ▼
aftr config add <url>     ← fetches via httpx, stores locally
         │
         ▼
registry.toml updated     ← records name, path, source URL
         │
         ▼
aftr init --template name ← template.py loads and parses TOML
         │
         ▼
scaffold.py renders files ← replaces {{project_name}}, {{module_name}}
```

Key files:
- `template.py` — `Template` dataclass, TOML parsing, placeholder substitution
- `scaffold.py` — Creates directories, writes files, runs `uv init`
- `config.py` — Locates config directory, reads/writes registry

### `create-from-project` Command

The `aftr config create-from-project` command reverses the scaffolding process — it reads an existing project and generates a template from it. Key behaviors:

- Respects `.gitignore` patterns via `pathspec`
- Supports `.aftrignore` for template-specific exclusions
- Enforces limits: 50 files max, 100 KB per file, 500 KB total
- Replaces occurrences of the project name and module name with `{{project_name}}` and `{{module_name}}` placeholders

---

## Configuration File (`config/config.json`)

Central definition of all packages for both platforms:

```json
{
  "scoop": {
    "packages": [...],
    "fonts": [...],
    "buckets": [...]
  },
  "homebrew": {
    "packages": [...],
    "casks": [...],
    "taps": [...]
  },
  "uv_tools": ["aftr"],
  "mise_tools": {},
  "bun_globals": []
}
```

AI CLI tools are **not** in this file — they're selected interactively by `aftr setup`.

---

## CI/CD Workflows

| Workflow | Trigger | What it does |
|----------|---------|-------------|
| `ci.yml` | Push / PR | Runs pytest on Windows + macOS, Python 3.11-3.12, ruff linting |
| `publish.yml` | Tag push (`v*`) | Publishes aftr to PyPI |
| `test-environment-setup.yml` | Push / PR | Tests `setup.sh` end-to-end on macOS runner |
| `generate-demo.yml` | Manual | Generates demo recordings |

### Publishing a Release

Releases are handled by `scripts/publish.ts` (run with Bun):

1. Bumps version in `pyproject.toml`
2. Builds the package with `uv build`
3. Publishes to PyPI with `uv publish`
4. Creates a git tag

---

## Development Setup

```bash
# Clone the repo
git clone https://github.com/rlancer/ai-for-the-rest
cd ai-for-the-rest/packages/cli

# Install dependencies
uv sync

# Run tests
uv run pytest tests/ -v

# Run the CLI locally
uv run aftr --help
```

### Adding a New Command

1. Create `packages/cli/src/aftr/commands/mycommand.py`
2. Define a Typer app: `app = typer.Typer()`
3. Register it in `cli.py`: `app.add_typer(mycommand.app, name="mycommand")`
4. Add tests in `tests/`

### Modifying the Default Template

Edit `packages/cli/src/aftr/templates/default.toml`. The template TOML schema is defined in `template.py`.

### Adding a Package to Environment Setup

Edit `config/config.json` and add the package to the appropriate section (`scoop.packages`, `homebrew.packages`, etc.). Both setup scripts read from this file.
