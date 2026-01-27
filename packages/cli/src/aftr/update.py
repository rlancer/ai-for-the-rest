"""Update checking functionality for aftr CLI."""

import httpx
from packaging.version import Version, InvalidVersion
from rich.console import Console
from rich.panel import Panel

from aftr import __version__

console = Console()


def get_installed_version() -> str:
    """Return the currently installed version."""
    return __version__


def get_latest_version(timeout: float = 3.0) -> str | None:
    """Query PyPI for the latest version of aftr.

    Args:
        timeout: Request timeout in seconds.

    Returns:
        Latest version string or None if request fails.
    """
    try:
        response = httpx.get(
            "https://pypi.org/pypi/aftr/json",
            timeout=timeout,
            follow_redirects=True,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("info", {}).get("version")
    except (httpx.HTTPError, KeyError, ValueError):
        return None


def check_for_update(timeout: float = 3.0) -> dict | None:
    """Check if an update is available.

    Args:
        timeout: Request timeout in seconds.

    Returns:
        Dict with 'status' ('update_available' or 'up_to_date'),
        'current' version, and 'latest' version if check succeeded.
        None if network request failed.
    """
    current = get_installed_version()
    latest = get_latest_version(timeout=timeout)

    if not latest:
        return None

    try:
        current_ver = Version(current)
        latest_ver = Version(latest)

        if latest_ver > current_ver:
            return {"status": "update_available", "current": current, "latest": latest}
        else:
            return {"status": "up_to_date", "current": current, "latest": latest}
    except InvalidVersion:
        return None


def show_update_banner(update_info: dict) -> None:
    """Display an update notification or up-to-date confirmation.

    Args:
        update_info: Dict containing 'status', 'current', and 'latest' version strings.
    """
    current = update_info["current"]
    status = update_info.get("status", "update_available")

    if status == "update_available":
        latest = update_info["latest"]
        console.print(
            Panel(
                f"[bold cyan]New version:[/bold cyan] {latest} [dim](current: {current})[/dim]\n"
                f"[bold]Run:[/bold] [green]uv tool upgrade aftr[/green]",
                title="[bold yellow]Update Available[/bold yellow]",
                border_style="yellow",
                padding=(0, 1),
            )
        )
        console.print()
    else:
        console.print(f"[dim green]v{current}[/dim green] [dim](up to date)[/dim]")
        console.print()
