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
- 🔧 **Environment Configuration**: Interactive setup for AI coding assistants (Claude Code, Codex, Gemini)
- 🔑 **SSH Key Management**: Generate and configure GitHub SSH keys
- 📊 **Data Science Ready**: Pre-configured with pandas, polars, Jupyter, and papermill
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

# Create in current directory
aftr init my-data-project --path .
```

**Generated project structure:**
```
my-data-project/
├── pyproject.toml          # UV project config with pandas, polars, jupyter, papermill
├── .mise.toml              # Tool versions (Python, UV)
├── notebooks/
│   └── 01_example.ipynb   # Sample notebook with papermill parameter tags
├── src/
│   └── my_data_project/   # Python source code (hyphenated names → underscores)
├── data/                   # Input data (gitignored)
└── outputs/                # Results and artifacts (gitignored)
```

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
