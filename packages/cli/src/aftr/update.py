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
        Dict with 'current' and 'latest' versions if update available,
        None otherwise.
    """
    current = get_installed_version()
    latest = get_latest_version(timeout=timeout)

    if not latest:
        return None

    try:
        current_ver = Version(current)
        latest_ver = Version(latest)

        if latest_ver > current_ver:
            return {"current": current, "latest": latest}
    except InvalidVersion:
        return None

    return None


def show_update_banner(update_info: dict) -> None:
    """Display an update notification banner.

    Args:
        update_info: Dict containing 'current' and 'latest' version strings.
    """
    current = update_info["current"]
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
