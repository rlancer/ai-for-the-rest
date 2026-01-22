"""Config command group - manage project templates."""

from pathlib import Path
from typing import Optional

import httpx
import typer
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from aftr import config
from aftr import template as template_module

console = Console()

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
