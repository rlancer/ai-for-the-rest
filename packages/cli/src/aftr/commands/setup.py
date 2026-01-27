"""Setup command - configure AI tools and SSH keys after environment setup."""

import platform
import subprocess

import typer
from InquirerPy import inquirer
from InquirerPy.utils import get_style
from rich import print
from rich.panel import Panel

from aftr.commands.ssh import (
    SSH_DIR,
    SSH_KEY,
    SSH_PUB_KEY,
    get_ssh_agent_status,
    view_public_key,
    generate_ssh_key,
    add_key_to_agent,
)


def _check_windows_ssh_agent() -> None:
    """Check if Windows SSH agent is running and provide instructions if not."""
    if platform.system() != "Windows":
        return

    status = get_ssh_agent_status()

    if status["status"] == "running":
        print()
        print("[green]✓[/green] Windows SSH agent is running")
        print()
        print("[yellow]To add your key to the agent, run:[/yellow]")
        print("  [cyan]ssh-add ~/.ssh/id_ed25519[/cyan]")
    elif status["status"] == "stopped":
        print()
        print("[yellow]⚠ Windows SSH agent is not running[/yellow]")
        print()
        print("[yellow]To enable SSH agent (requires Administrator):[/yellow]")
        print("  [cyan]Set-Service ssh-agent -StartupType Automatic[/cyan]")
        print("  [cyan]Start-Service ssh-agent[/cyan]")
        print()
        print("[yellow]Then add your key to the agent:[/yellow]")
        print("  [cyan]ssh-add ~/.ssh/id_ed25519[/cyan]")
    elif status["status"] == "not_installed":
        print()
        print("[yellow]⚠ Windows SSH agent service not found[/yellow]")
        print()
        print("[dim]OpenSSH may not be installed. You can install it via:[/dim]")
        print("  [cyan]Settings > Apps > Optional Features > OpenSSH Client[/cyan]")


def _is_claude_code_installed() -> bool:
    """Check if Claude Code is already installed."""
    try:
        result = subprocess.run(
            ["claude", "--version"],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def _install_claude_code() -> bool:
    """Install Claude Code using the official native installer.

    Returns True if installation succeeded, False otherwise.
    """
    system = platform.system()

    if system == "Windows":
        # Use PowerShell Core with the official installer
        result = subprocess.run(
            ["pwsh", "-Command", "irm https://claude.ai/install.ps1 | iex"],
            capture_output=True,
            text=True,
        )
    else:
        # macOS/Linux - use bash with the official installer
        result = subprocess.run(
            ["bash", "-c", "curl -fsSL https://claude.ai/install.sh | bash"],
            capture_output=True,
            text=True,
        )

    if result.returncode == 0:
        return True
    else:
        # Print stderr if available for debugging
        if result.stderr:
            print(f"    [dim]{result.stderr.strip()}[/dim]")
        return False


def _install_bun_package(package: str) -> tuple[bool, str]:
    """Install a package via bun global install.

    Returns (success, error_message).
    """
    try:
        subprocess.run(
            ["bun", "install", "-g", package],
            check=True,
            capture_output=True,
            text=True,
        )
        return True, ""
    except subprocess.CalledProcessError as e:
        return False, e.stderr
    except FileNotFoundError:
        return False, "bun not found"


def setup(
    non_interactive: bool = typer.Option(
        False, "--non-interactive", "-y", help="Skip all prompts and use defaults"
    ),
) -> None:
    """Configure AI tools and SSH keys after environment setup."""
    print(Panel("[cyan]AFTR Setup[/cyan] - Configure your development environment"))
    print()

    # AI CLI tools - Claude Code uses native installer, others use bun
    bun_packages = {
        "Codex": "@openai/codex",
        "Gemini CLI": "@google/gemini-cli",
    }

    if not non_interactive:
        print("[yellow]Select AI CLI tools to install[/yellow]")
        print()

        selected = inquirer.checkbox(
            message="Which AI CLI tools would you like to install?",
            choices=[
                {
                    "name": "Claude Code - Anthropic's official CLI (recommended)",
                    "value": "Claude Code",
                    "enabled": True,
                },
                {
                    "name": "Codex - OpenAI's code assistant",
                    "value": "Codex",
                    "enabled": False,
                },
                {
                    "name": "Gemini CLI - Google's AI assistant",
                    "value": "Gemini CLI",
                    "enabled": False,
                },
            ],
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
    else:
        # Default to Claude Code in non-interactive mode
        selected = ["Claude Code"]

    # Install selected AI CLIs
    if selected:
        print()
        print("[yellow]Installing selected AI CLI tools...[/yellow]")

        for tool_name in selected:
            if tool_name == "Claude Code":
                # Check if already installed (e.g., by setup.ps1 on Windows)
                if _is_claude_code_installed():
                    print("  [green]✓[/green] Claude Code already installed")
                    continue
                # Use official native installer for Claude Code
                print("  Installing Claude Code (native installer)...")
                if _install_claude_code():
                    print("  [green]✓[/green] Claude Code installed successfully")
                else:
                    print("  [red]✗[/red] Failed to install Claude Code")
            else:
                # Use bun for other tools
                package = bun_packages[tool_name]
                print(f"  Installing {package}...")
                success, error = _install_bun_package(package)
                if success:
                    print(f"  [green]✓[/green] {tool_name} installed successfully")
                elif error == "bun not found":
                    print(
                        "  [red]✗[/red] bun not found. Please ensure bun is installed and in your PATH."
                    )
                    break
                else:
                    print(f"  [red]✗[/red] Failed to install {tool_name}: {error}")
    else:
        print("[dim]No AI CLI tools selected[/dim]")

    # SSH key setup
    print()
    print("[yellow]SSH Key Setup[/yellow]")
    print()

    if non_interactive:
        print("[dim]Skipping SSH key setup in non-interactive mode[/dim]")
        return

    if SSH_PUB_KEY.exists():
        show_key = inquirer.confirm(
            message="An SSH key already exists. Do you want to view it?",
            default=True,
            style=get_style(
                {
                    "questionmark": "#E91E63 bold",
                    "answer": "#00BCD4 bold",
                }
            ),
        ).execute()

        if show_key:
            view_public_key()
            _check_windows_ssh_agent()
    else:
        create_key = inquirer.confirm(
            message="Would you like to set up an SSH key for GitHub?",
            default=True,
            style=get_style(
                {
                    "questionmark": "#E91E63 bold",
                    "answer": "#00BCD4 bold",
                }
            ),
        ).execute()

        if create_key:
            if generate_ssh_key():
                _check_windows_ssh_agent()
        else:
            print("[dim]Skipping SSH key setup[/dim]")

    print()
    print("[green]Setup complete![/green]")
