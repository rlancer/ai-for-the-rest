"""Project scaffolding logic using templates."""

import json
from pathlib import Path

from rich import print as rprint

from aftr.template import Template


def render_template_string(content: str, project_name: str, module_name: str) -> str:
    """Render template placeholders in content.

    Args:
        content: String with {{placeholders}}.
        project_name: Name of the project.
        module_name: Python module name (underscores instead of hyphens).

    Returns:
        Content with placeholders replaced.
    """
    return content.replace("{{project_name}}", project_name).replace(
        "{{module_name}}", module_name
    )


def scaffold_project(project_path: Path, project_name: str, template: Template) -> None:
    """Scaffold a new project using the given template.

    Args:
        project_path: Path where the project will be created.
        project_name: Name of the project.
        template: Template to use for scaffolding.
    """
    module_name = project_name.replace("-", "_")

    # Create base directory structure
    project_path.mkdir(parents=True)
    (project_path / "notebooks").mkdir()
    (project_path / "src" / module_name).mkdir(parents=True)
    (project_path / "data").mkdir()
    (project_path / "outputs").mkdir()

    # Create extra directories from template
    for dir_path in template.extra_directories:
        (project_path / dir_path).mkdir(parents=True, exist_ok=True)
        rprint(f"  [green]Created[/green] {dir_path}/")

    # Generate pyproject.toml
    _create_pyproject_toml(project_path, project_name, template)
    rprint("  [green]Created[/green] pyproject.toml")

    # Generate .mise.toml
    _create_mise_toml(project_path, template)
    rprint("  [green]Created[/green] .mise.toml")

    # Create __init__.py
    init_content = f'"""{project_name} - A data analysis project."""\n\n__version__ = "0.1.0"\n'
    (project_path / "src" / module_name / "__init__.py").write_text(
        init_content, encoding="utf-8"
    )
    rprint(f"  [green]Created[/green] src/{module_name}/__init__.py")

    # Create example notebook if configured
    if template.notebook_include_example:
        _create_example_notebook(project_path, project_name, template)
        rprint("  [green]Created[/green] notebooks/example.ipynb")

    # Create additional files from template
    for file_path, content in template.files.items():
        rendered_content = render_template_string(content, project_name, module_name)
        full_path = project_path / file_path

        # Ensure parent directory exists
        full_path.parent.mkdir(parents=True, exist_ok=True)

        full_path.write_text(rendered_content, encoding="utf-8")
        rprint(f"  [green]Created[/green] {file_path}")


def _create_pyproject_toml(
    project_path: Path, project_name: str, template: Template
) -> None:
    """Create pyproject.toml from template configuration."""
    # Build dependencies list
    deps = []
    for pkg, ver in template.dependencies.items():
        deps.append(f'    "{pkg}{ver}",')
    deps_str = "\n".join(deps)

    # Build dev dependencies if present
    dev_deps_str = ""
    if "dev" in template.optional_dependencies:
        dev_deps = []
        for dep in template.optional_dependencies["dev"]:
            dev_deps.append(f'    "{dep}",')
        dev_deps_str = f"""
[tool.uv]
dev-dependencies = [
{chr(10).join(dev_deps)}
]
"""

    content = f'''[project]
name = "{project_name}"
version = "0.1.0"
description = ""
requires-python = "{template.requires_python}"
dependencies = [
{deps_str}
]
{dev_deps_str}'''

    (project_path / "pyproject.toml").write_text(content, encoding="utf-8")


def _create_mise_toml(project_path: Path, template: Template) -> None:
    """Create .mise.toml from template configuration."""
    tools = template.mise_tools or {"uv": "latest"}

    tools_lines = []
    for tool, version in tools.items():
        tools_lines.append(f'{tool} = "{version}"')

    content = f"""[tools]
{chr(10).join(tools_lines)}

[settings]
python.uv_venv_auto = true
"""

    (project_path / ".mise.toml").write_text(content, encoding="utf-8")


def _create_example_notebook(
    project_path: Path, project_name: str, template: Template
) -> None:
    """Create example notebook with configured imports."""
    # Build import statements
    imports = template.notebook_imports or ["duckdb", "polars as pl"]
    import_lines = [f'import {imp}' if " as " not in imp else f'import {imp}' for imp in imports]
    import_source = [f'{line}\\n' for line in import_lines[:-1]]
    if import_lines:
        import_source.append(f'{import_lines[-1]}')
    import_source_str = ", ".join([f'"{s}"' for s in import_source])

    notebook_content = f'''{{
 "cells": [
  {{
   "cell_type": "markdown",
   "metadata": {{}},
   "source": ["# {project_name}\\n", "\\n", "Example notebook for papermill."]
  }},
  {{
   "cell_type": "code",
   "execution_count": null,
   "metadata": {{
    "tags": ["parameters"]
   }},
   "outputs": [],
   "source": ["# Parameters (tagged for papermill)\\n", "input_path = \\"data/input.csv\\"\\n", "output_path = \\"outputs/result.parquet\\""]
  }},
  {{
   "cell_type": "code",
   "execution_count": null,
   "metadata": {{}},
   "outputs": [],
   "source": [{import_source_str}]
  }}
 ],
 "metadata": {{
  "kernelspec": {{
   "display_name": "Python 3",
   "language": "python",
   "name": "python3"
  }}
 }},
 "nbformat": 4,
 "nbformat_minor": 4
}}'''

    (project_path / "notebooks" / "example.ipynb").write_text(
        notebook_content, encoding="utf-8"
    )
