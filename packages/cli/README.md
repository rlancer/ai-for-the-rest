# aftr

```
    ___    ________________
   /   |  / ____/_  __/ __ \
  / /| | / /_    / / / /_/ /
 / ___ |/ __/   / / / _, _/
/_/  |_/_/     /_/ /_/ |_|

===============================
  A I   f o r   T h e   R e s t
===============================
```

**aftr** (AI for The Rest) is a CLI tool for bootstrapping Python data science projects with modern best practices. It combines UV for blazing-fast package management, mise for reproducible tool versions, and papermill for notebook automation.

## ✨ Features

- 🚀 **Fast Setup**: Initialize production-ready data projects in seconds
- 📋 **Custom Templates**: Create and share project templates with custom dependencies and files
- 🔧 **Environment Configuration**: Interactive setup for AI coding assistants (Claude Code, Codex, Gemini)
- 🔑 **SSH Key Management**: Generate and configure GitHub SSH keys
- 📊 **Data Science Ready**: Pre-configured with DuckDB, Polars, Jupyter, and papermill
- 🎯 **Opinionated Structure**: Clean project layout with data/, notebooks/, src/, and outputs/
- 🔄 **Reproducible Environments**: mise.toml ensures consistent tool versions across machines

## Installation

```bash
# Install globally with UV
uv tool install aftr

# Or run directly with uvx
uvx aftr init my-project
```

## Usage

### Interactive Mode

Simply run `aftr` to access the interactive menu:

```bash
aftr
```

Choose from:
- **New Project** - Create a scaffolded data science project
- **Environment Setup** - Configure AI CLI tools and SSH keys
- **Help** - View usage information

### Create a New Project

```bash
# Interactive prompt for project name
aftr

# Direct project creation
aftr init my-data-project

# Use a specific template
aftr init my-data-project --template garda

# Create in current directory
aftr init my-data-project --path .
```

**Generated project structure:**
```
my-data-project/
├── pyproject.toml          # UV project config with DuckDB, Polars, Jupyter, papermill
├── .mise.toml              # Tool versions (Python, UV)
├── .mcp.json               # MCP server config (Playwright)
├── CLAUDE.md               # AI assistant guidance
├── notebooks/
│   └── example.ipynb       # Sample notebook with papermill parameter tags
├── src/
│   └── my_data_project/    # Python source code (hyphenated names → underscores)
├── data/                   # Input data (gitignored)
└── outputs/                # Results and artifacts (gitignored)
```

### Project Templates

Templates let you customize project scaffolding with different dependencies, files, and configurations. Perfect for team standards or internal packages.

#### Managing Templates

```bash
# List available templates
aftr config list

# Show template details
aftr config show default

# Export default template as a starting point
aftr config export-default -o my-template.toml

# Register a template from a URL
aftr config add https://git.internal.com/templates/garda-py.toml

# Update a template from its source URL
aftr config update garda

# Remove a registered template
aftr config remove garda
```

#### Template Format (TOML)

Templates use TOML format with `{{project_name}}` and `{{module_name}}` placeholders:

```toml
[template]
name = "My Team Template"
description = "Internal data science template"
version = "1.0.0"

[project]
requires-python = ">=3.11"

[project.dependencies]
polars = ">=1.0.0"
internal-utils = ">=0.5.0"  # Internal packages work too

[project.optional-dependencies]
dev = ["pytest>=8.0.0", "ruff>=0.1.0"]

[mise]
uv = "latest"

[directories]
include = ["config", "scripts"]  # Extra directories beyond defaults

[notebook]
include_example = true
imports = ["duckdb", "polars as pl", "internal_utils"]

[files."CLAUDE.md"]
content = '''
# CLAUDE.md
Custom guidance for {{project_name}}...
'''

[files."config/settings.toml"]
content = '''
[database]
host = "internal.db.com"
'''
```

#### Template Storage

Templates are stored in platform-specific config directories:
- **Linux/macOS**: `~/.config/aftr/templates/`
- **Windows**: `%LOCALAPPDATA%\aftr\templates\`

### Environment Setup

Configure your development environment after installation:

```bash
# Interactive configuration
aftr setup

# Non-interactive mode (defaults: Claude Code only, skip SSH)
aftr setup --non-interactive
```

**Setup mode features:**
- **AI CLI Selection**: Install coding assistants via bun (Claude Code, Codex, Gemini)
- **SSH Key Generation**: Create ed25519 keys for GitHub authentication
- **Key Display**: View and copy existing SSH keys for GitHub setup

Perfect for running after environment bootstrap scripts to complete your dev setup!

## Why aftr?

Modern data science projects need more than just a requirements.txt. **aftr** provides:

1. **UV Package Management**: 10-100x faster than pip, with built-in virtual environment handling
2. **mise Tool Versioning**: Pin Python and UV versions in `.mise.toml` for team consistency
3. **Papermill Integration**: Notebooks with parameter tags for automated execution
4. **AI-Ready Environment**: One command to install coding assistants like Claude Code
5. **Clean Conventions**: Opinionated structure that just works™

## Development

```bash
cd packages/cli
uv sync
uv run pytest tests/ -v
uv run aftr --help
```

## License

MIT

## Links

- [GitHub Repository](https://github.com/rlancer/ai-for-the-rest)
- [Issue Tracker](https://github.com/rlancer/ai-for-the-rest/issues)
