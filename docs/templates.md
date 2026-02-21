# Project Templates

Templates let you define reusable project structures with custom dependencies, files, and configurations. They're useful for standardizing data science projects across a team or organization.

## The Default Template

aftr ships with a built-in `default` template. It creates a project with:

- **DuckDB** for SQL-based data analytics
- **Polars** for DataFrame operations
- **Playwright** for browser automation
- **Jupyter** and **papermill** for notebooks
- **pytest** and **ruff** for testing and linting
- A `CLAUDE.md` with AI guidance for the project
- An `.mcp.json` configuring Playwright as an MCP server

To see the full default template:

```bash
aftr config export-default --print
```

---

## Template Format

Templates are TOML files. Here's a complete annotated example:

```toml
[template]
name = "My Template"           # Display name (required)
description = "A description"  # Short description
version = "1.0.0"              # Template version

[project]
requires-python = ">=3.11"

[project.dependencies]
# Standard package specifiers — same format as pyproject.toml
polars = ">=1.0.0"
duckdb = ">=1.0.0"
my-internal-package = ">=2.0.0"

[project.optional-dependencies]
dev = ["pytest>=8.0.0", "ruff>=0.1.0"]

[mise]
# Tool versions managed by mise
uv = "latest"
# python = "3.12"  # Uncomment to pin Python version

[directories]
# Extra directories beyond the default (data/, notebooks/, outputs/, src/)
include = ["config", "scripts", "reports"]

[notebook]
include_example = true         # Generate an example.ipynb
imports = ["duckdb", "polars as pl", "my_package"]  # Pre-imported in the example notebook

# Custom files: key is the relative file path
[files."CLAUDE.md"]
content = '''
# CLAUDE.md

This file provides guidance to Claude Code for {{project_name}}.

## Stack

- DuckDB for analytics
- Polars for DataFrames
'''

[files."config/settings.toml"]
content = '''
[database]
host = "internal.company.com"
port = 5432
'''

[files."scripts/run.sh"]
content = '''#!/bin/bash
uv run papermill notebooks/example.ipynb outputs/example_output.ipynb
'''
```

### Placeholders

Use these in any file `content` value:

| Placeholder | Replaced With |
|-------------|---------------|
| `{{project_name}}` | The project name as given (e.g., `my-project`) |
| `{{module_name}}` | The Python module name (hyphens converted to underscores, e.g., `my_project`) |

---

## Managing Templates

### List Available Templates

```bash
aftr config list
```

### Register a Template from a URL

Templates can be hosted as raw TOML files anywhere accessible by HTTP — a GitHub repo, internal server, etc.

```bash
aftr config add https://raw.githubusercontent.com/myorg/templates/main/acme.toml
```

The template is fetched and stored locally. Its source URL is saved in the registry.

### Update a Template

Re-fetch a template from its original URL:

```bash
aftr config update acme
```

### Show a Template

Display the full template content:

```bash
aftr config show acme
```

### Remove a Template

```bash
aftr config remove acme
```

---

## Creating a Template from an Existing Project

If you already have a project with the structure you want, generate a template directly from it:

```bash
aftr config create-from-project ./my-project -o my-template.toml
```

Preview what it would generate before saving:

```bash
aftr config create-from-project ./my-project --print
```

### What gets included

- All files not excluded by `.gitignore`
- All files not excluded by `.aftrignore` (template-specific excludes)
- Project name and module name occurrences are replaced with `{{project_name}}` and `{{module_name}}`

### Limits

| Limit | Value |
|-------|-------|
| Max files | 50 |
| Max per file | 100 KB |
| Max total | 500 KB |

If your project exceeds these limits, add patterns to `.aftrignore` to exclude large or generated files.

### `.aftrignore`

Create a `.aftrignore` file in your project root to exclude files from template generation (uses the same pattern syntax as `.gitignore`):

```
# .aftrignore
*.parquet
data/
outputs/
.venv/
notebooks/.ipynb_checkpoints/
```

---

## Using a Template

Specify the template name when creating a project:

```bash
aftr init my-project --template acme
```

Or in interactive mode, you'll be prompted to select from available templates.

---

## Sharing Templates with a Team

The recommended workflow for team templates:

1. **Create** a template from a reference project or from scratch
2. **Host** it as a raw file in a shared Git repository (e.g., GitHub, GitLab, internal Gitea)
3. **Register** it on each team member's machine:
   ```bash
   aftr config add https://your-git-host/org/templates/raw/main/team-template.toml
   ```
4. **Update** when the template changes:
   ```bash
   aftr config update team-template
   ```

Since the source URL is stored in the registry, team members can pull the latest version with a single `aftr config update` command.

---

## Template Storage

| Platform | Location |
|----------|----------|
| macOS / Linux | `~/.config/aftr/templates/` |
| Windows | `%LOCALAPPDATA%\aftr\templates\` |

The registry file that tracks template names and source URLs:

| Platform | Location |
|----------|----------|
| macOS / Linux | `~/.config/aftr/registry.toml` |
| Windows | `%LOCALAPPDATA%\aftr\registry.toml` |
