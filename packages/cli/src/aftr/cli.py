"""Main CLI entry point for aftr."""

import typer
from InquirerPy import inquirer
from InquirerPy.utils import get_style
from rich.console import Console
from rich.panel import Panel

from aftr.commands.init import init

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


def interactive_menu() -> None:
    """Show the interactive menu when no arguments provided."""
    show_banner()
    console.print()

    choices = [
        {"name": "New Project", "value": "new"},
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
            init(name=project_name)

    elif action == "help":
        console.print()
        console.print(
            Panel(
                "[cyan]aftr[/cyan] - Bootstrap Python data projects\n\n"
                "[bold]Usage:[/bold]\n"
                "  aftr                    Interactive mode\n"
                "  aftr init <name>        Create a new project\n"
                "  aftr init <name> -p .   Create in current directory\n\n"
                "[bold]Created project includes:[/bold]\n"
                "  - UV for fast package management\n"
                "  - mise for tool version management\n"
                "  - Jupyter & papermill for notebooks\n"
                "  - pandas & polars for data analysis",
                title="[bold magenta]Help[/bold magenta]",
                border_style="cyan",
            )
        )

    elif action == "exit":
        console.print("[dim]Goodbye![/dim]")
        raise typer.Exit(0)


app = typer.Typer(
    name="aftr",
    help="CLI for bootstrapping Python data projects with UV, mise, and papermill",
    no_args_is_help=False,
    invoke_without_command=True,
)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """AFTR - AI for The Rest. Bootstrap Python data projects."""
    if ctx.invoked_subcommand is None:
        interactive_menu()


app.command()(init)


if __name__ == "__main__":
    app()
