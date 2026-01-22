"""Init command - scaffold a new Python data project."""

from pathlib import Path
from typing import Optional

import typer
from InquirerPy import inquirer
from InquirerPy.utils import get_style
from rich import print as rprint
from rich.panel import Panel

from aftr import template as template_module
from aftr.scaffold import scaffold_project


def init(
    name: str = typer.Argument(..., help="Name of the project to create"),
    path: Path = typer.Option(
        Path("."), "--path", "-p", help="Parent directory for the project"
    ),
    template: Optional[str] = typer.Option(
        None, "--template", "-t", help="Template to use (default: prompts if multiple)"
    ),
) -> None:
    """Scaffold a new Python data project with UV, mise, and papermill."""
    project_path = path / name

    if project_path.exists():
        rprint(f"[red]Error:[/red] Directory '{project_path}' already exists")
        raise typer.Exit(1)

    # Get available templates
    available_templates = template_module.list_available_templates()

    # Determine which template to use
    template_name = template
    if template_name is None:
        if len(available_templates) == 1:
            # Only default template available, use it
            template_name = "default"
        else:
            # Multiple templates available, prompt user
            template_choices = []
            for tpl_name in available_templates:
                info = template_module.get_template_info(tpl_name)
                if info:
                    desc = (
                        info["description"][:40] + "..."
                        if len(info["description"]) > 40
                        else info["description"]
                    )
                    label = f"{tpl_name} - {desc}" if desc else tpl_name
                else:
                    label = tpl_name
                template_choices.append({"name": label, "value": tpl_name})

            template_name = inquirer.select(
                message="Select a template:",
                choices=template_choices,
                default="default",
                pointer=">",
                style=get_style(
                    {
                        "questionmark": "#E91E63 bold",
                        "pointer": "#00BCD4 bold",
                        "highlighted": "#00BCD4 bold",
                        "selected": "#4CAF50 bold",
                    }
                ),
            ).execute()

    # Load the template
    tpl = template_module.load_template(template_name)
    if tpl is None:
        rprint(f"[red]Error:[/red] Template '{template_name}' not found")
        rprint("Run 'aftr config list' to see available templates")
        raise typer.Exit(1)

    rprint(
        Panel(
            f"Creating project [cyan]{name}[/cyan] using template [magenta]{tpl.name}[/magenta]",
            title="aftr init",
        )
    )

    # Scaffold the project
    scaffold_project(project_path, name, tpl)

    name.replace("-", "_")
    rprint()
    rprint(
        Panel(
            f"""[green]Project created successfully![/green]

[cyan]Next steps:[/cyan]
  cd {name}
  uv sync
  uv run jupyter lab""",
            title="Done",
        )
    )
