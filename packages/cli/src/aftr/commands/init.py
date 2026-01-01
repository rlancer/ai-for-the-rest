"""Init command - scaffold a new Python data project."""

from pathlib import Path

import typer
from rich import print
from rich.panel import Panel


def init(
    name: str = typer.Argument(..., help="Name of the project to create"),
    path: Path = typer.Option(
        Path("."), "--path", "-p", help="Parent directory for the project"
    ),
) -> None:
    """Scaffold a new Python data project with UV, mise, and papermill."""
    project_path = path / name

    if project_path.exists():
        print(f"[red]Error:[/red] Directory '{project_path}' already exists")
        raise typer.Exit(1)

    print(Panel(f"Creating project [cyan]{name}[/cyan]", title="aftr init"))

    # Create directory structure
    project_path.mkdir(parents=True)
    (project_path / "notebooks").mkdir()
    (project_path / "src" / name.replace("-", "_")).mkdir(parents=True)
    (project_path / "data").mkdir()
    (project_path / "outputs").mkdir()

    # Create pyproject.toml
    pyproject_content = f'''[project]
name = "{name}"
version = "0.1.0"
description = ""
requires-python = ">=3.11"
dependencies = [
    "polars>=1.0.0",
    "duckdb>=1.0.0",
    "playwright>=1.40.0",
    "jupyter>=1.0.0",
    "papermill>=2.6.0",
]

[tool.uv]
dev-dependencies = [
    "pytest>=8.0.0",
    "ruff>=0.1.0",
]
'''
    (project_path / "pyproject.toml").write_text(pyproject_content, encoding="utf-8")
    print("  [green]Created[/green] pyproject.toml")

    # Create .mise.toml
    mise_content = """[tools]
uv = "latest"

[settings]
python.uv_venv_auto = true
"""
    (project_path / ".mise.toml").write_text(mise_content, encoding="utf-8")
    print("  [green]Created[/green] .mise.toml")

    # Create .gitignore
    gitignore_content = """# Python
__pycache__/
*.py[cod]
*$py.class
.venv/
.env

# Jupyter
.ipynb_checkpoints/
*.ipynb_meta

# Data
data/
outputs/
*.csv
*.parquet
*.xlsx

# IDE
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db
"""
    (project_path / ".gitignore").write_text(gitignore_content, encoding="utf-8")
    print("  [green]Created[/green] .gitignore")

    # Create __init__.py
    module_name = name.replace("-", "_")
    (project_path / "src" / module_name / "__init__.py").write_text(
        f'"""{name} - A data analysis project."""\n\n__version__ = "0.1.0"\n',
        encoding="utf-8",
    )
    print(f"  [green]Created[/green] src/{module_name}/__init__.py")

    # Create example notebook
    notebook_content = (
        """{
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": ["# %s\\n", "\\n", "Example notebook for papermill."]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {
    "tags": ["parameters"]
   },
   "outputs": [],
   "source": ["# Parameters (tagged for papermill)\\n", "input_path = \\"data/input.csv\\"\\n", "output_path = \\"outputs/result.parquet\\""]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": ["import duckdb\\n", "import polars as pl"]
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3",
   "language": "python",
   "name": "python3"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 4
}"""
        % name
    )
    (project_path / "notebooks" / "example.ipynb").write_text(
        notebook_content, encoding="utf-8"
    )
    print("  [green]Created[/green] notebooks/example.ipynb")

    # Create README
    readme_content = f"""# {name}

A data analysis project scaffolded with [aftr](https://github.com/rlancer/ai-for-the-rest).

## Setup

```bash
# Install dependencies with UV
uv sync

# Activate the virtual environment
source .venv/bin/activate  # macOS/Linux
.venv\\Scripts\\activate     # Windows
```

## Running Notebooks

```bash
# Run a notebook with papermill
uv run papermill notebooks/example.ipynb outputs/example_output.ipynb
```

## Project Structure

```
{name}/
├── data/           # Input data (gitignored)
├── notebooks/      # Jupyter notebooks
├── outputs/        # Output files (gitignored)
├── src/{module_name}/  # Python source code
├── .mise.toml      # mise tool versions
└── pyproject.toml  # Project config
```
"""
    (project_path / "README.md").write_text(readme_content, encoding="utf-8")
    print("  [green]Created[/green] README.md")

    # Create CLAUDE.md
    claude_md_content = f"""# CLAUDE.md

This file provides guidance to Claude Code when working with this project.

## Project Overview

{name} is a data analysis project scaffolded with aftr. This project uses modern Python data tools optimized for performance and ease of use.

## Tech Stack & Best Practices

### Data Processing
- **DuckDB**: Primary tool for all data tasks. DuckDB is an in-process SQL OLAP database optimized for analytics.
  - Use DuckDB for data loading, transformation, and analysis
  - DuckDB can query Parquet, CSV, and JSON files directly without loading into memory
  - Convert DuckDB relations to Polars DataFrames using `.pl()` method

- **Polars**: Use whenever you need a DataFrame for data manipulation
  - Polars is faster and more memory-efficient than pandas
  - DuckDB and Polars integrate seamlessly: `duckdb.sql("SELECT * FROM table").pl()`
  - Use Polars for DataFrame operations, complex transformations, and lazy evaluation

### Browser Automation
- **Playwright**: Use for all browser automation tasks
  - Web scraping
  - Data collection from websites
  - Automated testing of web interfaces
  - Screenshot capture and PDF generation

### Playwright MCP Server
- This project includes a Playwright MCP server configuration (`.mcp.json`)
- The MCP server provides Claude Code with browser automation capabilities
- Use it for interactive web scraping and testing tasks

## Workflow

1. **Data Collection**: Use Playwright for web scraping if needed
2. **Data Storage**: Save data as Parquet files in `data/` directory
3. **Data Analysis**: Use DuckDB for SQL-based analysis
4. **DataFrame Operations**: Convert DuckDB results to Polars with `.pl()` when needed
5. **Outputs**: Save results to `outputs/` directory

## Example Usage

```python
import duckdb
import polars as pl

# Query data with DuckDB and convert to Polars
df = duckdb.sql("SELECT * FROM 'data/input.parquet' WHERE amount > 100").pl()

# Continue processing with Polars
result = df.group_by("category").agg(pl.col("amount").sum())
```

## Key Patterns

- Favor DuckDB for data queries and aggregations
- Use Polars DataFrames for complex transformations
- Use Playwright for any browser automation needs
- Keep notebooks in `notebooks/` directory
- Store raw data in `data/` directory (gitignored)
- Save outputs to `outputs/` directory (gitignored)
"""
    (project_path / "CLAUDE.md").write_text(claude_md_content, encoding="utf-8")
    print("  [green]Created[/green] CLAUDE.md")

    # Create .mcp.json
    mcp_json_content = """{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": [
        "@playwright/mcp@latest"
      ]
    }
  }
}
"""
    (project_path / ".mcp.json").write_text(mcp_json_content, encoding="utf-8")
    print("  [green]Created[/green] .mcp.json")

    print()
    print(
        Panel(
            f"""[green]Project created successfully![/green]

[cyan]Next steps:[/cyan]
  cd {name}
  uv sync
  uv run jupyter lab""",
            title="Done",
        )
    )
