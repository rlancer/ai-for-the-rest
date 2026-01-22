"""Main CLI entry point for aftr."""

from pathlib import Path
from typing import Optional

import typer
from InquirerPy import inquirer
from InquirerPy.utils import get_style
from rich.console import Console
from rich.panel import Panel

from aftr import __version__
from aftr.commands.config_cmd import config_app
from aftr.commands.init import init
from aftr.commands.setup import setup
from aftr.update import check_for_update, show_update_banner

console = Console()

LOGO = """
[bold bright_magenta]    ___    ________________[/]
[bold magenta]   /   |  / ____/_  __/ __ \\\\[/]
[bold blue]  / /| | / /_    / / / /_/ /[/]
[bold cyan] / ___ |/ __/   / / / _, _/[/]
[bold bright_cyan]/_/  |_/_/     /_/ /_/ |_|[/]

[dim white]===============================[/]
  [bold cyan]A I   f o r   T h e   R e s t[/]
[dim white]===============================[/]
"""


def show_banner() -> None:
    """Display the ASCII art banner."""
    console.print(LOGO)


def templates_submenu() -> None:
    """Show the templates management submenu."""
    from aftr.commands.config_cmd import (
        add_template,
        create_from_project,
        export_default,
        list_templates,
        remove_template,
        show_template,
        update_template,
    )
    from aftr import template as template_module

    choices = [
        {"name": "List Templates", "value": "list"},
        {"name": "Show Template Details", "value": "show"},
        {"name": "Add Template from URL", "value": "add"},
        {"name": "Update Template", "value": "update"},
        {"name": "Remove Template", "value": "remove"},
        {"name": "Export Default Template", "value": "export"},
        {"name": "Create from Project", "value": "create"},
        {"name": "Back", "value": "back"},
    ]

    action = inquirer.select(
        message="Manage Templates:",
        choices=choices,
        default="list",
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

    if action == "list":
        list_templates()

    elif action == "show":
        templates = template_module.list_available_templates()
        if not templates:
            console.print("[yellow]No templates available[/yellow]")
            return

        template_name = inquirer.select(
            message="Select template to show:",
            choices=templates,
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

        console.print()
        show_template(template_name)

    elif action == "add":
        url = inquirer.text(
            message="Template URL (raw TOML file):",
            validate=lambda x: len(x) > 0,
            invalid_message="URL cannot be empty",
            style=get_style(
                {
                    "questionmark": "#E91E63 bold",
                    "answer": "#00BCD4 bold",
                }
            ),
        ).execute()

        if url:
            console.print()
            add_template(url=url, name=None)

    elif action == "update":
        templates = [
            t for t in template_module.list_available_templates() if t != "default"
        ]
        if not templates:
            console.print("[yellow]No user templates to update[/yellow]")
            return

        template_name = inquirer.select(
            message="Select template to update:",
            choices=templates,
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

        console.print()
        update_template(template_name)

    elif action == "remove":
        templates = [
            t for t in template_module.list_available_templates() if t != "default"
        ]
        if not templates:
            console.print("[yellow]No user templates to remove[/yellow]")
            return

        template_name = inquirer.select(
            message="Select template to remove:",
            choices=templates,
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

        console.print()
        remove_template(template_name)

    elif action == "export":
        output_path = inquirer.text(
            message="Output file path:",
            default="template.toml",
            style=get_style(
                {
                    "questionmark": "#E91E63 bold",
                    "answer": "#00BCD4 bold",
                }
            ),
        ).execute()

        if output_path:
            console.print()
            export_default(output=Path(output_path))

    elif action == "create":
        source_path = inquirer.text(
            message="Project directory path:",
            default=".",
            validate=lambda x: Path(x).is_dir(),
            invalid_message="Must be a valid directory",
            style=get_style(
                {
                    "questionmark": "#E91E63 bold",
                    "answer": "#00BCD4 bold",
                }
            ),
        ).execute()

        if source_path:
            console.print()
            create_from_project(
                source=Path(source_path).resolve(),
                name=None,
                description="",
                force=False,
            )

    elif action == "back":
        return


def interactive_menu(update_info: dict | None = None) -> None:
    """Show the interactive menu when no arguments provided."""
    show_banner()
    if update_info:
        show_update_banner(update_info)
    console.print()

    choices = [
        {"name": "New Project", "value": "new"},
        {"name": "Environment Setup", "value": "setup"},
        {"name": "Manage Templates", "value": "templates"},
        {"name": "Help", "value": "help"},
        {"name": "Exit", "value": "exit"},
    ]

    action = inquirer.select(
        message="What would you like to do?",
        choices=choices,
        default="new",
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

    if action == "new":
        console.print()
        project_name = inquirer.text(
            message="Project name:",
            validate=lambda x: len(x) > 0,
            invalid_message="Project name cannot be empty",
            style=get_style(
                {
                    "questionmark": "#E91E63 bold",
                    "answer": "#00BCD4 bold",
                }
            ),
        ).execute()

        if project_name:
            console.print()
            init(name=project_name, path=Path("."), template=None)

    elif action == "setup":
        console.print()
        setup()

    elif action == "templates":
        console.print()
        templates_submenu()

    elif action == "help":
        console.print()
        console.print(
            Panel(
                "[cyan]aftr[/cyan] - Bootstrap Python data projects\n\n"
                "[bold]Usage:[/bold]\n"
                "  aftr                         Interactive mode\n"
                "  aftr init <name>             Create a new project\n"
                "  aftr init <name> -t acme    Use a specific template\n"
                "  aftr setup                   Configure AI tools and SSH keys\n"
                "  aftr config list             List available templates\n"
                "  aftr config add <url>        Register template from URL\n"
                "  aftr config show <name>      Show template details\n\n"
                "[bold]Created project includes:[/bold]\n"
                "  - UV for fast package management\n"
                "  - mise for tool version management\n"
                "  - Jupyter & papermill for notebooks\n"
                "  - DuckDB & Polars for data analysis",
                title="[bold magenta]Help[/bold magenta]",
                border_style="cyan",
            )
        )

    elif action == "exit":
        console.print("[dim]Goodbye![/dim]")
        raise typer.Exit(0)


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        console.print(f"aftr version {__version__}")
        raise typer.Exit()


app = typer.Typer(
    name="aftr",
    help="CLI for bootstrapping Python data projects with UV, mise, and papermill",
    no_args_is_help=False,
    invoke_without_command=True,
)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    """AFTR - AI for The Rest. Bootstrap Python data projects."""
    # Check for updates (silently fails on network errors)
    update_info = check_for_update()

    if ctx.invoked_subcommand is None:
        interactive_menu(update_info=update_info)
    elif update_info:
        show_update_banner(update_info)


app.command()(init)
app.command()(setup)
app.add_typer(config_app)


if __name__ == "__main__":
    app()
