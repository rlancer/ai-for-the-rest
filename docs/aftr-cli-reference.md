# aftr CLI Reference

Complete reference for all `aftr` commands.

## Installation

```bash
# Install globally (recommended)
uv tool install aftr

# Run without installing
uvx aftr <command>
```

---

## `aftr` (interactive mode)

Running `aftr` with no arguments opens the interactive menu.

```bash
aftr
```

Menu options:
- **New Project** — prompts for a project name and creates it
- **Environment Setup** — runs `aftr setup`
- **Help** — shows usage information

---

## `aftr init`

Create a new data science project.

```bash
aftr init <project-name> [OPTIONS]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `project-name` | Name of the project to create |

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `--path`, `-p` | Current directory | Directory where the project folder will be created |
| `--template`, `-t` | `default` | Template name to use for scaffolding |

### Examples

```bash
# Create in the current directory
aftr init sales-analysis

# Create at a specific path
aftr init sales-analysis --path ~/projects

# Use a custom template
aftr init sales-analysis --template acme
```

### Generated Project Structure

```
<project-name>/
├── pyproject.toml          # Dependencies and project metadata
├── .mise.toml              # Tool versions (Python 3.12, uv latest)
├── .mcp.json               # MCP server config (Playwright browser automation)
├── CLAUDE.md               # AI assistant guidance for the project
├── README.md               # Project readme
├── .gitignore
├── notebooks/
│   └── example.ipynb       # Sample notebook with papermill parameter tags
├── src/
│   └── <module_name>/      # Python source (hyphens converted to underscores)
│       └── __init__.py
├── data/                   # Input data (gitignored)
└── outputs/                # Results and artifacts (gitignored)
```

### Default Dependencies

Projects scaffolded with the default template include:

| Package | Purpose |
|---------|---------|
| duckdb | In-process SQL analytics |
| polars | Fast DataFrame library |
| pandas | Data manipulation |
| jupyter | Notebook environment |
| papermill | Notebook parameterization and execution |
| pytest | Testing framework |
| ruff | Linter and formatter |

---

## `aftr setup`

Configure your development environment after installation. Installs AI coding assistants and optionally sets up SSH keys.

```bash
aftr setup [OPTIONS]
```

### Options

| Option | Description |
|--------|-------------|
| `--non-interactive` | Skip prompts; install Claude Code only, skip SSH setup |

### What it does

In interactive mode, `aftr setup`:

1. Prompts you to select AI tools to install (checkbox selection)
2. Installs selected tools
3. Optionally generates an SSH key for GitHub authentication

**AI tools available:**

| Tool | Command | Platform |
|------|---------|----------|
| Claude Code | `claude` | Windows, macOS |
| Codex | `codex` | macOS only |
| Gemini CLI | `gemini` | macOS only |

Claude Code is installed via Anthropic's native installer. Codex and Gemini use `bun` global install (requires Bun, which is macOS-only in this environment).

`aftr setup` detects if a tool is already installed and skips reinstallation.

---

## `aftr config`

Manage project templates.

### `aftr config list`

List all available templates.

```bash
aftr config list
```

Output includes the built-in `default` template and any registered user templates.

---

### `aftr config show`

Display the full contents of a template.

```bash
aftr config show <name>
```

### Options

| Option | Description |
|--------|-------------|
| `--print` | Print template to stdout without saving |

---

### `aftr config add`

Register a template from a URL.

```bash
aftr config add <url>
```

The URL should point to a raw TOML file (e.g., a GitHub raw file URL).

```bash
aftr config add https://raw.githubusercontent.com/myorg/templates/main/acme.toml
```

The template is fetched via HTTP and stored locally in the user config directory. Its source URL is saved in the registry so it can be updated later.

---

### `aftr config remove`

Remove a registered template.

```bash
aftr config remove <name>
```

Removes the template file and its registry entry. The built-in `default` template cannot be removed.

---

### `aftr config update`

Re-fetch a template from its source URL.

```bash
aftr config update <name>
```

Useful when a shared team template has been updated at its source URL.

---

### `aftr config export-default`

Export the built-in default template as a starting point for creating your own.

```bash
aftr config export-default [OPTIONS]
```

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `--output`, `-o` | `./default.toml` | Path to save the exported template |
| `--print` | — | Print to stdout instead of saving |

```bash
# Export to a file
aftr config export-default -o my-template.toml

# Preview in the terminal
aftr config export-default --print
```

---

### `aftr config create-from-project`

Generate a template from an existing project directory.

```bash
aftr config create-from-project <project-path> [OPTIONS]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `project-path` | Path to the existing project |

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `--output`, `-o` | `./template.toml` | Path to save the generated template |
| `--print` | — | Print to stdout instead of saving |

### How it works

- Scans the project directory recursively
- Respects `.gitignore` patterns (excluded files are not included in the template)
- Respects `.aftrignore` for template-specific exclusions
- Replaces the project name and module name with `{{project_name}}` and `{{module_name}}` placeholders
- Enforces limits: max 50 files, 100 KB per file, 500 KB total

```bash
# Create template from a project
aftr config create-from-project ./my-project -o team-template.toml

# Preview before saving
aftr config create-from-project ./my-project --print
```

---

## Global Options

| Option | Description |
|--------|-------------|
| `--help` | Show help for any command |
| `--version` | Show aftr version |

```bash
aftr --help
aftr init --help
aftr config --help
```

---

## Template Storage Locations

User templates are stored in platform-specific config directories:

| Platform | Path |
|----------|------|
| macOS / Linux | `~/.config/aftr/templates/` |
| Windows | `%LOCALAPPDATA%\aftr\templates\` |

The template registry is at:

| Platform | Path |
|----------|------|
| macOS / Linux | `~/.config/aftr/registry.toml` |
| Windows | `%LOCALAPPDATA%\aftr\registry.toml` |
