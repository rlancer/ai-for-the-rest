"""Config command group - manage project templates."""

from pathlib import Path
from typing import Optional

import httpx
import pathspec
import tomlkit
import typer
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from aftr import config
from aftr import template as template_module

console = Console()

# Limits for template creation
MAX_FILES = 50
MAX_FILE_SIZE_KB = 100
MAX_TOTAL_SIZE_KB = 500

# Default patterns to always ignore (in addition to .gitignore/.aftrignore)
DEFAULT_IGNORE_PATTERNS = [
    ".git/",
    ".git",
    "__pycache__/",
    "*.pyc",
    "*.pyo",
    ".venv/",
    "venv/",
    ".env",
    "node_modules/",
    ".DS_Store",
    "Thumbs.db",
    "*.egg-info/",
    ".pytest_cache/",
    ".ruff_cache/",
    ".mypy_cache/",
    "dist/",
    "build/",
    "*.whl",
    "*.tar.gz",
]

config_app = typer.Typer(
    name="config",
    help="Manage project templates",
    no_args_is_help=True,
)


@config_app.command("list")
def list_templates() -> None:
    """List available project templates."""
    templates = template_module.list_available_templates()

    table = Table(title="Available Templates")
    table.add_column("Name", style="cyan")
    table.add_column("Description")
    table.add_column("Version")
    table.add_column("Source")

    for name in templates:
        info = template_module.get_template_info(name)
        if info:
            source = (
                "built-in" if info["is_builtin"] else (info["source_url"] or "local")
            )
            table.add_row(
                name,
                info["description"],
                info["version"],
                source[:50] + "..." if len(source) > 50 else source,
            )

    console.print(table)


@config_app.command("add")
def add_template(
    url: str = typer.Argument(..., help="URL to fetch the template from"),
    name: Optional[str] = typer.Option(
        None,
        "--name",
        "-n",
        help="Custom name for the template (default: from template)",
    ),
) -> None:
    """Register a template from a URL.

    The URL should point to a raw TOML file (e.g., GitHub raw URL).
    """
    rprint(f"[cyan]Fetching template from:[/cyan] {url}")

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, follow_redirects=True)
            response.raise_for_status()
            content = response.text
    except httpx.HTTPStatusError as e:
        rprint(
            f"[red]Error:[/red] HTTP {e.response.status_code} - {e.response.reason_phrase}"
        )
        raise typer.Exit(1)
    except httpx.RequestError as e:
        rprint(f"[red]Error:[/red] Failed to fetch URL: {e}")
        raise typer.Exit(1)

    # Parse the template to validate and get the name
    try:
        template = template_module.parse_template(content)
    except Exception as e:
        rprint(f"[red]Error:[/red] Invalid template format: {e}")
        raise typer.Exit(1)

    template_name = name or template.name.lower().replace(" ", "-")

    if template_name == "default":
        rprint("[red]Error:[/red] Cannot overwrite the built-in 'default' template")
        raise typer.Exit(1)

    # Check if template already exists
    if config.template_exists(template_name):
        existing_info = template_module.get_template_info(template_name)
        if existing_info:
            rprint(
                f"[yellow]Warning:[/yellow] Template '{template_name}' already exists"
            )
            if not typer.confirm("Do you want to overwrite it?"):
                raise typer.Exit(0)

    # Save the template
    template_module.save_template(template_name, content)
    config.register_template(template_name, url)

    rprint(
        Panel(
            f"[green]Template registered successfully![/green]\n\n"
            f"[cyan]Name:[/cyan] {template_name}\n"
            f"[cyan]Description:[/cyan] {template.description}\n"
            f"[cyan]Version:[/cyan] {template.version}",
            title="Template Added",
        )
    )


@config_app.command("remove")
def remove_template(
    name: str = typer.Argument(..., help="Name of the template to remove"),
) -> None:
    """Remove a registered template."""
    if name == "default":
        rprint("[red]Error:[/red] Cannot remove the built-in 'default' template")
        raise typer.Exit(1)

    if not config.template_exists(name):
        rprint(f"[red]Error:[/red] Template '{name}' not found")
        raise typer.Exit(1)

    # Confirm removal
    if not typer.confirm(f"Are you sure you want to remove template '{name}'?"):
        raise typer.Exit(0)

    # Remove the template file
    template_path = config.get_template_path(name)
    template_path.unlink()

    # Remove from registry
    config.unregister_template(name)

    rprint(f"[green]Template '{name}' removed successfully[/green]")


@config_app.command("show")
def show_template(
    name: str = typer.Argument(..., help="Name of the template to show"),
) -> None:
    """Show details about a template."""
    template = template_module.load_template(name)
    if template is None:
        rprint(f"[red]Error:[/red] Template '{name}' not found")
        raise typer.Exit(1)

    info = template_module.get_template_info(name)
    if not info:
        rprint("[red]Error:[/red] Could not load template info")
        raise typer.Exit(1)

    # Build dependencies table
    deps_table = Table(show_header=True, header_style="bold")
    deps_table.add_column("Package")
    deps_table.add_column("Version")

    for pkg, ver in template.dependencies.items():
        deps_table.add_row(pkg, ver)

    source = "built-in" if info["is_builtin"] else (info["source_url"] or "local")

    content = f"""[cyan]Name:[/cyan] {template.name}
[cyan]Description:[/cyan] {template.description}
[cyan]Version:[/cyan] {template.version}
[cyan]Source:[/cyan] {source}
[cyan]Requires Python:[/cyan] {template.requires_python}

[bold]Dependencies:[/bold]
"""

    console.print(Panel(content, title=f"Template: {name}"))
    console.print(deps_table)

    if template.extra_directories:
        rprint(
            f"\n[bold]Extra directories:[/bold] {', '.join(template.extra_directories)}"
        )

    if template.files:
        rprint(f"\n[bold]Custom files:[/bold] {', '.join(template.files.keys())}")

    if template.mise_tools:
        tools = ", ".join([f"{k}={v}" for k, v in template.mise_tools.items()])
        rprint(f"\n[bold]mise tools:[/bold] {tools}")


@config_app.command("update")
def update_template(
    name: str = typer.Argument(..., help="Name of the template to update"),
) -> None:
    """Refresh a template from its source URL."""
    if name == "default":
        rprint("[red]Error:[/red] Cannot update the built-in 'default' template")
        raise typer.Exit(1)

    source_url = config.get_template_source_url(name)
    if not source_url:
        rprint(
            f"[red]Error:[/red] Template '{name}' has no source URL. "
            "Use 'aftr config add <url>' to re-add it."
        )
        raise typer.Exit(1)

    rprint(f"[cyan]Updating template from:[/cyan] {source_url}")

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(source_url, follow_redirects=True)
            response.raise_for_status()
            content = response.text
    except httpx.HTTPStatusError as e:
        rprint(
            f"[red]Error:[/red] HTTP {e.response.status_code} - {e.response.reason_phrase}"
        )
        raise typer.Exit(1)
    except httpx.RequestError as e:
        rprint(f"[red]Error:[/red] Failed to fetch URL: {e}")
        raise typer.Exit(1)

    # Parse to validate
    try:
        template = template_module.parse_template(content)
    except Exception as e:
        rprint(f"[red]Error:[/red] Invalid template format: {e}")
        raise typer.Exit(1)

    # Save the updated template
    template_module.save_template(name, content)

    rprint(
        Panel(
            f"[green]Template updated successfully![/green]\n\n"
            f"[cyan]Name:[/cyan] {template.name}\n"
            f"[cyan]Version:[/cyan] {template.version}",
            title="Template Updated",
        )
    )


@config_app.command("export-default")
def export_default(
    output: Path = typer.Option(
        Path("template.toml"),
        "--output",
        "-o",
        help="Output file path",
    ),
) -> None:
    """Export the default template as a starting point for customization."""
    if output.exists():
        if not typer.confirm(f"File '{output}' already exists. Overwrite?"):
            raise typer.Exit(0)

    content = template_module.get_default_template_content()
    output.write_text(content, encoding="utf-8")

    rprint(
        Panel(
            f"[green]Default template exported to:[/green] {output}\n\n"
            "Edit this file to customize, then register it with:\n"
            f"  aftr config add file://{output.absolute()}",
            title="Template Exported",
        )
    )


def _load_ignore_patterns(project_path: Path) -> pathspec.PathSpec:
    """Load ignore patterns from .gitignore and .aftrignore files.

    Args:
        project_path: Root path of the project.

    Returns:
        PathSpec object with combined patterns.
    """
    patterns = list(DEFAULT_IGNORE_PATTERNS)

    # Load .gitignore
    gitignore_path = project_path / ".gitignore"
    if gitignore_path.exists():
        content = gitignore_path.read_text(encoding="utf-8")
        for line in content.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                patterns.append(line)

    # Load .aftrignore (takes precedence)
    aftrignore_path = project_path / ".aftrignore"
    if aftrignore_path.exists():
        content = aftrignore_path.read_text(encoding="utf-8")
        for line in content.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                patterns.append(line)

    return pathspec.PathSpec.from_lines("gitignore", patterns)


def _collect_project_files(
    project_path: Path, ignore_spec: pathspec.PathSpec
) -> tuple[list[tuple[Path, int]], list[str]]:
    """Collect all files in a project that aren't ignored.

    Args:
        project_path: Root path of the project.
        ignore_spec: PathSpec with ignore patterns.

    Returns:
        Tuple of (list of (file_path, size) tuples, list of warning messages).
    """
    files: list[tuple[Path, int]] = []
    warnings: list[str] = []

    for file_path in project_path.rglob("*"):
        if not file_path.is_file():
            continue

        # Get relative path for pattern matching
        try:
            rel_path = file_path.relative_to(project_path)
        except ValueError:
            continue

        rel_path_str = str(rel_path).replace("\\", "/")

        # Check if file should be ignored
        if ignore_spec.match_file(rel_path_str):
            continue

        # Get file size
        try:
            size = file_path.stat().st_size
        except OSError:
            warnings.append(f"Could not read size of: {rel_path_str}")
            continue

        files.append((file_path, size))

    return files, warnings


def _check_limits(
    files: list[tuple[Path, int]], project_path: Path
) -> tuple[bool, list[str]]:
    """Check if collected files are within limits.

    Args:
        files: List of (file_path, size) tuples.
        project_path: Root path of the project.

    Returns:
        Tuple of (is_within_limits, list of error messages).
    """
    errors: list[str] = []

    # Check file count
    if len(files) > MAX_FILES:
        errors.append(
            f"Too many files: {len(files)} files found (max: {MAX_FILES})\n"
            f"  Add patterns to .gitignore or .aftrignore to exclude files."
        )

    # Check individual file sizes and total size
    total_size = 0
    large_files: list[str] = []

    for file_path, size in files:
        total_size += size
        size_kb = size / 1024

        if size_kb > MAX_FILE_SIZE_KB:
            rel_path = file_path.relative_to(project_path)
            large_files.append(f"  - {rel_path} ({size_kb:.1f} KB)")

    if large_files:
        errors.append(
            f"Files exceed size limit ({MAX_FILE_SIZE_KB} KB):\n"
            + "\n".join(large_files)
            + "\n  Add these to .gitignore or .aftrignore to exclude them."
        )

    total_size_kb = total_size / 1024
    if total_size_kb > MAX_TOTAL_SIZE_KB:
        errors.append(
            f"Total size too large: {total_size_kb:.1f} KB (max: {MAX_TOTAL_SIZE_KB} KB)\n"
            f"  Add patterns to .gitignore or .aftrignore to exclude files."
        )

    return len(errors) == 0, errors


def _is_text_file(file_path: Path) -> bool:
    """Check if a file is likely a text file.

    Args:
        file_path: Path to the file.

    Returns:
        True if the file appears to be text.
    """
    # Common text extensions
    text_extensions = {
        ".py",
        ".toml",
        ".txt",
        ".md",
        ".json",
        ".yaml",
        ".yml",
        ".sh",
        ".ps1",
        ".ts",
        ".js",
        ".css",
        ".html",
        ".xml",
        ".ini",
        ".cfg",
        ".gitignore",
        ".env.example",
        ".editorconfig",
    }

    # Check extension
    if file_path.suffix.lower() in text_extensions:
        return True

    # Check for files without extension (common config files)
    if file_path.suffix == "" and file_path.name in {
        "Makefile",
        "Dockerfile",
        "LICENSE",
        ".gitignore",
        ".aftrignore",
        ".dockerignore",
    }:
        return True

    # Try to detect binary content
    try:
        with open(file_path, "rb") as f:
            chunk = f.read(8192)
            # Check for null bytes which indicate binary content
            if b"\x00" in chunk:
                return False
            return True
    except OSError:
        return False


def _extract_pyproject_info(project_path: Path) -> dict:
    """Extract project info from pyproject.toml.

    Args:
        project_path: Root path of the project.

    Returns:
        Dictionary with extracted info.
    """
    info: dict = {
        "requires_python": ">=3.11",
        "dependencies": {},
        "optional_dependencies": {},
        "uv_indexes": [],
        "uv_sources": {},
    }

    pyproject_path = project_path / "pyproject.toml"
    if not pyproject_path.exists():
        return info

    try:
        content = pyproject_path.read_text(encoding="utf-8")
        doc = tomlkit.parse(content)

        project = doc.get("project", {})
        info["requires_python"] = project.get("requires-python", ">=3.11")

        # Extract dependencies
        deps = project.get("dependencies", [])
        for dep in deps:
            # Parse dependency string like "polars>=1.0.0"
            dep_str = str(dep)
            # Find where version spec starts
            for i, char in enumerate(dep_str):
                if char in ">=<~!":
                    pkg = dep_str[:i].strip()
                    ver = dep_str[i:].strip()
                    info["dependencies"][pkg] = ver
                    break
            else:
                # No version spec found
                info["dependencies"][dep_str.strip()] = ""

        # Extract optional dependencies (dev group)
        opt_deps = project.get("optional-dependencies", {})
        for group, deps in opt_deps.items():
            info["optional_dependencies"][group] = list(deps)

        # Also check tool.uv sections
        tool = doc.get("tool", {})
        uv = tool.get("uv", {})
        dev_deps = uv.get("dev-dependencies", [])
        if dev_deps and "dev" not in info["optional_dependencies"]:
            info["optional_dependencies"]["dev"] = list(dev_deps)

        # Extract uv indexes ([[tool.uv.index]])
        uv_indexes = uv.get("index", [])
        for idx in uv_indexes:
            info["uv_indexes"].append({str(k): str(v) for k, v in idx.items()})

        # Extract uv sources ([tool.uv.sources])
        uv_sources = uv.get("sources", {})
        for pkg, src in uv_sources.items():
            info["uv_sources"][str(pkg)] = {str(k): str(v) for k, v in src.items()}

    except Exception:
        pass  # Return defaults if parsing fails

    return info


def _extract_mise_info(project_path: Path) -> dict[str, str]:
    """Extract mise tool versions from .mise.toml.

    Args:
        project_path: Root path of the project.

    Returns:
        Dictionary of tool -> version.
    """
    mise_path = project_path / ".mise.toml"
    if not mise_path.exists():
        return {}

    try:
        content = mise_path.read_text(encoding="utf-8")
        doc = tomlkit.parse(content)

        tools = doc.get("tools", {})
        return {str(k): str(v) for k, v in tools.items()}
    except Exception:
        return {}


def _detect_project_name(project_path: Path) -> str:
    """Detect project name from pyproject.toml or directory name.

    Args:
        project_path: Root path of the project.

    Returns:
        Project name string.
    """
    pyproject_path = project_path / "pyproject.toml"
    if pyproject_path.exists():
        try:
            content = pyproject_path.read_text(encoding="utf-8")
            doc = tomlkit.parse(content)
            project = doc.get("project", {})
            name = project.get("name", "")
            if name:
                return str(name)
        except Exception:
            pass

    # Fall back to directory name
    return project_path.name


def _replace_project_name_with_placeholders(
    content: str, project_name: str, module_name: str
) -> str:
    """Replace project name and module name with template placeholders.

    Args:
        content: File content.
        project_name: Original project name.
        module_name: Python module name (underscores).

    Returns:
        Content with placeholders.
    """
    # Replace module name first (more specific) then project name
    result = content.replace(module_name, "{{module_name}}")
    result = result.replace(project_name, "{{project_name}}")
    return result


def _generate_template_toml(
    template_name: str,
    description: str,
    pyproject_info: dict,
    mise_info: dict[str, str],
    files_content: dict[str, str],
    extra_directories: list[str],
) -> str:
    """Generate TOML template content.

    Args:
        template_name: Name for the template.
        description: Template description.
        pyproject_info: Extracted pyproject.toml info.
        mise_info: Extracted .mise.toml info.
        files_content: Dictionary of file_path -> content.
        extra_directories: List of extra directories to create.

    Returns:
        TOML template string.
    """
    doc = tomlkit.document()

    # Template metadata
    template = tomlkit.table()
    template.add("name", template_name)
    template.add("description", description)
    template.add("version", "1.0.0")
    doc.add("template", template)

    # Project configuration
    project = tomlkit.table()
    project.add("requires-python", pyproject_info.get("requires_python", ">=3.11"))
    doc.add("project", project)

    # Dependencies
    deps = pyproject_info.get("dependencies", {})
    if deps:
        dependencies = tomlkit.table()
        for pkg, ver in deps.items():
            dependencies.add(pkg, ver)
        doc["project"].add("dependencies", dependencies)

    # Optional dependencies
    opt_deps = pyproject_info.get("optional_dependencies", {})
    if opt_deps:
        optional_dependencies = tomlkit.table()
        for group, pkgs in opt_deps.items():
            optional_dependencies.add(group, pkgs)
        doc["project"].add("optional-dependencies", optional_dependencies)

    # uv configuration (indexes and sources)
    uv_indexes = pyproject_info.get("uv_indexes", [])
    uv_sources = pyproject_info.get("uv_sources", {})
    if uv_indexes or uv_sources:
        uv_section = tomlkit.table()
        if uv_indexes:
            indexes_aot = tomlkit.aot()
            for idx in uv_indexes:
                idx_table = tomlkit.table()
                for k, v in idx.items():
                    idx_table.add(k, v)
                indexes_aot.append(idx_table)
            uv_section.add("indexes", indexes_aot)
        if uv_sources:
            sources_table = tomlkit.table()
            for pkg, src in uv_sources.items():
                src_table = tomlkit.inline_table()
                for k, v in src.items():
                    src_table.append(k, v)
                sources_table.add(pkg, src_table)
            uv_section.add("sources", sources_table)
        doc.add("uv", uv_section)

    # mise tools
    if mise_info:
        mise = tomlkit.table()
        for tool, ver in mise_info.items():
            mise.add(tool, ver)
        doc.add("mise", mise)

    # Notebook section (disabled by default)
    notebook = tomlkit.table()
    notebook.add("include_example", False)
    doc.add("notebook", notebook)

    # Extra directories
    if extra_directories:
        directories = tomlkit.table()
        directories.add("include", extra_directories)
        doc.add("directories", directories)

    # Files
    if files_content:
        files = tomlkit.table()
        for file_path, content in sorted(files_content.items()):
            file_table = tomlkit.table()
            file_table.add("content", tomlkit.string(content, multiline=True))
            files.add(file_path, file_table)
        doc.add("files", files)

    return tomlkit.dumps(doc)


@config_app.command("create-from-project")
def create_from_project(
    source: Path = typer.Argument(
        ...,
        help="Path to existing project directory",
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
    ),
    name: Optional[str] = typer.Option(
        None,
        "--name",
        "-n",
        help="Custom name for the template (default: from project)",
    ),
    description: str = typer.Option(
        "",
        "--description",
        "-d",
        help="Template description",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing template without prompting",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Save template to this file path instead of the aftr config directory",
    ),
) -> None:
    """Create a template from an existing project.

    Respects .gitignore and .aftrignore files. Project name and module name
    are replaced with {{project_name}} and {{module_name}} placeholders.

    Limits:
    - Maximum 50 files
    - Maximum 100 KB per file
    - Maximum 500 KB total

    If limits are exceeded, add patterns to .gitignore or create .aftrignore.
    """
    rprint(f"[cyan]Analyzing project:[/cyan] {source}")

    # Detect project name
    project_name = _detect_project_name(source)
    module_name = project_name.replace("-", "_")

    rprint(f"[cyan]Project name:[/cyan] {project_name}")
    rprint(f"[cyan]Module name:[/cyan] {module_name}")

    # Load ignore patterns
    ignore_spec = _load_ignore_patterns(source)

    # Check for .aftrignore hint
    aftrignore_path = source / ".aftrignore"
    if not aftrignore_path.exists():
        rprint(
            "\n[dim]Tip: Create a .aftrignore file to exclude additional files "
            "from the template.[/dim]"
        )

    # Collect files
    files, warnings = _collect_project_files(source, ignore_spec)

    for warning in warnings:
        rprint(f"[yellow]Warning:[/yellow] {warning}")

    rprint(f"\n[cyan]Found {len(files)} files[/cyan]")

    # Check limits
    within_limits, errors = _check_limits(files, source)

    if not within_limits:
        rprint("\n[red]Cannot create template - limits exceeded:[/red]\n")
        for error in errors:
            rprint(f"[red]x[/red] {error}\n")

        # Show helpful message about .aftrignore
        rprint(
            Panel(
                "Create or update [cyan].aftrignore[/cyan] in your project root "
                "to exclude files.\n\n"
                "[bold]Example .aftrignore:[/bold]\n"
                "data/\n"
                "*.csv\n"
                "*.parquet\n"
                "large_file.json\n"
                "outputs/\n\n"
                "Then run this command again.",
                title="How to Fix",
            )
        )
        raise typer.Exit(1)

    # Extract project info
    rprint("\n[cyan]Extracting project configuration...[/cyan]")
    pyproject_info = _extract_pyproject_info(source)
    mise_info = _extract_mise_info(source)

    if pyproject_info["dependencies"]:
        rprint(
            f"  [green]Found[/green] {len(pyproject_info['dependencies'])} dependencies"
        )
    if mise_info:
        rprint(f"  [green]Found[/green] {len(mise_info)} mise tools")

    # Read and process file contents
    rprint("\n[cyan]Processing files...[/cyan]")
    files_content: dict[str, str] = {}
    skipped_binary: list[str] = []
    extra_directories: set[str] = set()

    # Standard directories that are always created by scaffold
    standard_dirs = {"data", "notebooks", "outputs", "src"}

    for file_path, size in files:
        rel_path = file_path.relative_to(source)
        rel_path_str = str(rel_path).replace("\\", "/")

        # Skip pyproject.toml and .mise.toml (generated from config)
        if rel_path_str in {"pyproject.toml", ".mise.toml"}:
            continue

        # Skip src/{module_name}/__init__.py (generated by scaffold)
        if rel_path_str == f"src/{module_name}/__init__.py":
            continue

        # Track extra directories
        parts = rel_path.parts
        if len(parts) > 1 and parts[0] not in standard_dirs:
            extra_directories.add(parts[0])

        # Check if text file
        if not _is_text_file(file_path):
            skipped_binary.append(rel_path_str)
            continue

        try:
            content = file_path.read_text(encoding="utf-8")
            # Replace project/module names with placeholders
            content = _replace_project_name_with_placeholders(
                content, project_name, module_name
            )
            files_content[rel_path_str] = content
            rprint(f"  [green]+[/green] {rel_path_str}")
        except Exception as e:
            rprint(f"  [yellow]![/yellow] Skipped {rel_path_str}: {e}")

    if skipped_binary:
        rprint(f"\n[dim]Skipped {len(skipped_binary)} binary files[/dim]")

    # Determine template name
    template_name = name or project_name.lower().replace(" ", "-")

    if template_name == "default":
        rprint("[red]Error:[/red] Cannot overwrite the built-in 'default' template")
        raise typer.Exit(1)

    # Check if template already exists
    if config.template_exists(template_name) and not force:
        rprint(f"\n[yellow]Warning:[/yellow] Template '{template_name}' already exists")
        if not typer.confirm("Do you want to overwrite it?"):
            raise typer.Exit(0)

    # Generate template TOML
    rprint(f"\n[cyan]Generating template:[/cyan] {template_name}")

    template_description = description or f"Template created from {project_name}"

    template_content = _generate_template_toml(
        template_name=template_name.title().replace("-", " "),
        description=template_description,
        pyproject_info=pyproject_info,
        mise_info=mise_info,
        files_content=files_content,
        extra_directories=sorted(extra_directories),
    )

    # Save template
    if output is not None:
        output.write_text(template_content, encoding="utf-8")
        saved_path = output.resolve()
    else:
        saved_path = template_module.save_template(template_name, template_content)
        config.register_template(template_name, "")  # No source URL for local creation

    # Summary
    rprint(
        Panel(
            f"[green]Template created successfully![/green]\n\n"
            f"[cyan]Name:[/cyan] {template_name}\n"
            f"[cyan]Description:[/cyan] {template_description}\n"
            f"[cyan]Files:[/cyan] {len(files_content)}\n"
            f"[cyan]Dependencies:[/cyan] {len(pyproject_info.get('dependencies', {}))}\n"
            f"[cyan]Saved to:[/cyan] {saved_path}\n\n"
            f"Use this template with:\n"
            f"  [bold]aftr init my-project --template {template_name}[/bold]",
            title="Template Created",
        )
    )
