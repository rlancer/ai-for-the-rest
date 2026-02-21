"""Refs command group — manage shared markdown reference sources."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from InquirerPy import inquirer
from InquirerPy.utils import get_style
from rich import print as rprint
from rich.console import Console
from rich.table import Table

from aftr import refs as refs_module

console = Console()

refs_app = typer.Typer(
    name="refs",
    help="Manage shared markdown reference sources",
    no_args_is_help=True,
)

_PROMPT_STYLE = get_style(
    {
        "questionmark": "#E91E63 bold",
        "pointer": "#00BCD4 bold",
        "highlighted": "#00BCD4 bold",
        "selected": "#4CAF50 bold",
        "answer": "#00BCD4 bold",
    }
)


def _find_project_dir() -> Path:
    """Return cwd as the project root (where .aftr/ will be placed)."""
    return Path.cwd()


@refs_app.command("add")
def add_source(
    url: Optional[str] = typer.Option(None, "--url", help="Git repository URL"),
    path: Optional[str] = typer.Option(
        None, "--path", help="Path inside the repo to sync (e.g. docs/guides)"
    ),
    branch: Optional[str] = typer.Option(
        None, "--branch", help="Branch to sync from (default: main)"
    ),
    name: Optional[str] = typer.Option(
        None, "--name", help="Short name for this source"
    ),
    local_dir: Optional[str] = typer.Option(
        None,
        "--local-dir",
        help="Local subdirectory under .aftr/ (default: same as name)",
    ),
) -> None:
    """Register a git repository as a shared reference source.

    When called without options, launches an interactive prompt.
    """
    project_dir = _find_project_dir()

    # Interactive mode when any required field is missing
    if not url:
        url = inquirer.text(
            message="Git repository URL:",
            validate=lambda x: len(x.strip()) > 0,
            invalid_message="URL cannot be empty",
            style=_PROMPT_STYLE,
        ).execute()

    if not path:
        path = inquirer.text(
            message="Path inside repo to sync (e.g. docs/guides):",
            validate=lambda x: len(x.strip()) > 0,
            invalid_message="Path cannot be empty",
            style=_PROMPT_STYLE,
        ).execute()

    if not name:
        # Suggest a default from the path
        default_name = Path(path).name if path else ""
        name = inquirer.text(
            message="Short name for this source:",
            default=default_name,
            validate=lambda x: len(x.strip()) > 0,
            invalid_message="Name cannot be empty",
            style=_PROMPT_STYLE,
        ).execute()

    if not branch:
        branch = inquirer.text(
            message="Branch:",
            default="main",
            style=_PROMPT_STYLE,
        ).execute()

    # Normalise
    url = (url or "").strip()
    path = (path or "").strip()
    name = (name or "").strip()
    branch = (branch or "main").strip()
    effective_local_dir = (local_dir or name).strip()

    # Check for duplicate name
    sources = refs_module.load_refs_config(project_dir)
    if any(s.name == name for s in sources):
        rprint(f"[red]Error:[/red] A source named '{name}' already exists.")
        rprint(f"  Use [cyan]aftr refs remove {name}[/cyan] first, or choose a different name.")
        raise typer.Exit(1)

    new_source = refs_module.RefsSource(
        name=name,
        url=url,
        path=path,
        branch=branch,
        local_dir=effective_local_dir,
    )
    sources.append(new_source)
    refs_module.save_refs_config(project_dir, sources)
    refs_module.ensure_gitignore(project_dir)

    rprint(f"[green]Source '{name}' added.[/green]")
    rprint(f"  Run [cyan]aftr refs sync {name}[/cyan] to fetch the files.")


@refs_app.command("sync")
def sync_sources(
    name: Optional[str] = typer.Argument(
        None, help="Name of the source to sync (omit to sync all)"
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Re-sync even if already up to date"
    ),
) -> None:
    """Sync reference files from registered sources.

    Omit NAME to sync all sources.
    """
    project_dir = _find_project_dir()
    sources = refs_module.load_refs_config(project_dir)

    if not sources:
        rprint(
            "[yellow]No sources registered.[/yellow] "
            "Add one with [cyan]aftr refs add[/cyan]."
        )
        raise typer.Exit(0)

    if name:
        targets = [s for s in sources if s.name == name]
        if not targets:
            rprint(f"[red]Error:[/red] Source '{name}' not found.")
            raise typer.Exit(1)
    else:
        targets = sources

    any_error = False
    for source in targets:
        rprint(f"[cyan]Syncing[/cyan] {source.name} …")
        result = refs_module.sync_source(project_dir, source, force=force)

        if result.status == "up_to_date":
            rprint(f"  [dim]Already up to date[/dim] ({result.commit[:8] if result.commit else '?'})")
        elif result.status == "updated":
            short = result.commit[:8] if result.commit else "?"
            rprint(f"  [green]Updated[/green] → {short}")
        else:
            rprint(f"  [red]Error:[/red] {result.message}")
            any_error = True

    if any_error:
        raise typer.Exit(1)


@refs_app.command("list")
def list_sources() -> None:
    """List registered reference sources."""
    project_dir = _find_project_dir()
    sources = refs_module.load_refs_config(project_dir)

    if not sources:
        rprint(
            "[yellow]No sources registered.[/yellow] "
            "Add one with [cyan]aftr refs add[/cyan]."
        )
        return

    state = refs_module.load_refs_state(project_dir)
    source_states = state.get("sources", {})

    table = Table(title="Registered Reference Sources")
    table.add_column("Name", style="cyan")
    table.add_column("URL")
    table.add_column("Path")
    table.add_column("Branch")
    table.add_column("Local Dir")
    table.add_column("Last Synced")

    for src in sources:
        src_state = source_states.get(src.name, {})
        last_synced = src_state.get("synced_at", "—")
        # Shorten ISO timestamp for display
        if last_synced and last_synced != "—":
            last_synced = last_synced[:19].replace("T", " ")
        url_display = src.url if len(src.url) <= 50 else src.url[:47] + "..."
        table.add_row(
            src.name,
            url_display,
            src.path,
            src.branch,
            src.local_dir,
            last_synced,
        )

    console.print(table)


@refs_app.command("remove")
def remove_source(
    name: str = typer.Argument(..., help="Name of the source to remove"),
    delete_files: bool = typer.Option(
        False,
        "--delete-files",
        help="Also delete the synced files from .aftr/<local_dir>/",
    ),
) -> None:
    """Remove a registered reference source."""
    project_dir = _find_project_dir()
    sources = refs_module.load_refs_config(project_dir)

    target = next((s for s in sources if s.name == name), None)
    if target is None:
        rprint(f"[red]Error:[/red] Source '{name}' not found.")
        raise typer.Exit(1)

    if not typer.confirm(f"Remove source '{name}'?"):
        raise typer.Exit(0)

    if delete_files:
        local_path = project_dir / refs_module.AFTR_DIR / target.local_dir
        if local_path.exists():
            import shutil
            shutil.rmtree(local_path)
            rprint(f"  [dim]Deleted[/dim] {local_path}")

    updated = [s for s in sources if s.name != name]
    refs_module.save_refs_config(project_dir, updated)

    # Clean up state entry
    state = refs_module.load_refs_state(project_dir)
    state.get("sources", {}).pop(name, None)
    refs_module.save_refs_state(project_dir, state)

    rprint(f"[green]Source '{name}' removed.[/green]")
