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
    "pandas>=2.0.0",
    "polars>=1.0.0",
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
python = "3.12"
uv = "latest"
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
   "source": ["import pandas as pd\\n", "import polars as pl"]
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
