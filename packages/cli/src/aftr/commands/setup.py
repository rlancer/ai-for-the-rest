"""Setup command - configure AI tools and SSH keys after environment setup."""

import json
import platform
import subprocess
from pathlib import Path

import typer
from InquirerPy import inquirer
from InquirerPy.utils import get_style
from rich import print
from rich.panel import Panel

# Claude Code config files
CLAUDE_CONFIG_FILE = Path.home() / ".claude.json"
CLAUDE_SETTINGS_DIR = Path.home() / ".claude"
CLAUDE_SETTINGS_FILE = CLAUDE_SETTINGS_DIR / "settings.json"

from aftr.commands.ssh import (
    SSH_PUB_KEY,
    discover_ssh_keys,
    get_ssh_agent_status,
    view_public_key,
    generate_ssh_key,
)


def _check_windows_ssh_agent() -> None:
    """Check if Windows SSH agent is running and provide instructions if not."""
    if platform.system() != "Windows":
        return

    status = get_ssh_agent_status()

    if status["status"] == "running":
        print()
        print("[green]+[/green] Windows SSH agent is running")
        print()
        print("[yellow]To add your key to the agent, run:[/yellow]")
        print("  [cyan]ssh-add ~/.ssh/id_ed25519[/cyan]")
    elif status["status"] == "stopped":
        print()
        print("[yellow]! Windows SSH agent is not running[/yellow]")
        print()
        print("[yellow]To enable SSH agent (requires Administrator):[/yellow]")
        print("  [cyan]Set-Service ssh-agent -StartupType Automatic[/cyan]")
        print("  [cyan]Start-Service ssh-agent[/cyan]")
        print()
        print("[yellow]Then add your key to the agent:[/yellow]")
        print("  [cyan]ssh-add ~/.ssh/id_ed25519[/cyan]")
    elif status["status"] == "not_installed":
        print()
        print("[yellow]! Windows SSH agent service not found[/yellow]")
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


def _is_claude_config_complete() -> bool:
    """Check if Claude Code config exists and has completed onboarding."""
    if not CLAUDE_CONFIG_FILE.exists():
        return False

    try:
        config = json.loads(CLAUDE_CONFIG_FILE.read_text())
        return config.get("hasCompletedOnboarding", False)
    except (json.JSONDecodeError, OSError):
        return False


def _get_claude_api_key() -> str | None:
    """Get the currently configured Anthropic API key from settings.json."""
    if not CLAUDE_SETTINGS_FILE.exists():
        return None

    try:
        settings = json.loads(CLAUDE_SETTINGS_FILE.read_text())
        return settings.get("env", {}).get("ANTHROPIC_API_KEY")
    except (json.JSONDecodeError, OSError):
        return None


def _save_claude_api_key(api_key: str) -> bool:
    """Save the Anthropic API key to ~/.claude/settings.json.

    Returns True if saved successfully.
    """
    try:
        # Create .claude directory if it doesn't exist
        CLAUDE_SETTINGS_DIR.mkdir(mode=0o700, exist_ok=True)

        # Read existing settings or start fresh
        if CLAUDE_SETTINGS_FILE.exists():
            try:
                settings = json.loads(CLAUDE_SETTINGS_FILE.read_text())
            except json.JSONDecodeError:
                settings = {}
        else:
            settings = {}

        # Ensure env dict exists and add API key
        if "env" not in settings:
            settings["env"] = {}
        settings["env"]["ANTHROPIC_API_KEY"] = api_key

        # Write back with proper formatting
        CLAUDE_SETTINGS_FILE.write_text(json.dumps(settings, indent=2) + "\n")
        return True

    except OSError as e:
        print(f"[red]x[/red] Failed to save API key: {e}")
        return False


def _setup_claude_api_key() -> bool:
    """Set up Claude Code API key by prompting user and saving to settings.

    Returns True if setup was successful.
    """
    print()
    print("[yellow]Claude Code API Key Setup[/yellow]")
    print()

    # Check if Claude Code is installed
    if not _is_claude_code_installed():
        print("[yellow]![/yellow] Claude Code is not installed")
        print("[dim]Install Claude Code first, then run setup again[/dim]")
        return False

    # Check if API key is already configured
    existing_key = _get_claude_api_key()
    if existing_key:
        # Mask the key for display (show first 8 and last 4 chars)
        if len(existing_key) > 16:
            masked = existing_key[:8] + "..." + existing_key[-4:]
        else:
            masked = "****"
        print(f"[green]+[/green] API key already configured: [dim]{masked}[/dim]")

        update_key = inquirer.confirm(
            message="Would you like to update the API key?",
            default=False,
            style=get_style(
                {
                    "questionmark": "#E91E63 bold",
                    "answer": "#00BCD4 bold",
                }
            ),
        ).execute()

        if not update_key:
            return True

    # Prompt for API key
    print()
    print("[dim]Get your API key from: https://console.anthropic.com/settings/keys[/dim]")
    print()

    api_key = inquirer.secret(
        message="Paste your Anthropic API key:",
        validate=lambda x: len(x) > 0 and x.startswith("sk-"),
        invalid_message="API key should start with 'sk-'",
        style=get_style(
            {
                "questionmark": "#E91E63 bold",
                "answer": "#00BCD4 bold",
            }
        ),
    ).execute()

    if not api_key:
        print("[dim]Skipping API key setup[/dim]")
        return False

    # Save the API key
    if _save_claude_api_key(api_key):
        print("[green]+[/green] API key saved to ~/.claude/settings.json")
    else:
        return False

    # Also mark onboarding complete in .claude.json
    try:
        # Read existing config or start fresh
        if CLAUDE_CONFIG_FILE.exists():
            try:
                config = json.loads(CLAUDE_CONFIG_FILE.read_text())
            except json.JSONDecodeError:
                config = {}
        else:
            config = {}

        # Add hasCompletedOnboarding flag
        config["hasCompletedOnboarding"] = True

        # Write back
        CLAUDE_CONFIG_FILE.write_text(json.dumps(config, indent=2) + "\n")
        print("[green]+[/green] Claude Code onboarding marked complete")

    except OSError as e:
        print(f"[yellow]![/yellow] Could not update onboarding status: {e}")

    return True


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
                    print("  [green]+[/green] Claude Code already installed")
                    continue
                # Use official native installer for Claude Code
                print("  Installing Claude Code (native installer)...")
                if _install_claude_code():
                    print("  [green]+[/green] Claude Code installed successfully")
                else:
                    print("  [red]x[/red] Failed to install Claude Code")
            else:
                # Use bun for other tools
                package = bun_packages[tool_name]
                print(f"  Installing {package}...")
                success, error = _install_bun_package(package)
                if success:
                    print(f"  [green]+[/green] {tool_name} installed successfully")
                elif error == "bun not found":
                    print(
                        "  [red]x[/red] bun not found. Please ensure bun is installed and in your PATH."
                    )
                    break
                else:
                    print(f"  [red]x[/red] Failed to install {tool_name}: {error}")
    else:
        print("[dim]No AI CLI tools selected[/dim]")

    # Claude Code API key setup (if Claude Code is installed)
    if _is_claude_code_installed():
        if not non_interactive:
            setup_api = inquirer.confirm(
                message="Would you like to configure Claude Code API key?",
                default=True,
                style=get_style(
                    {
                        "questionmark": "#E91E63 bold",
                        "answer": "#00BCD4 bold",
                    }
                ),
            ).execute()

            if setup_api:
                _setup_claude_api_key()
        else:
            # In non-interactive mode, just mark onboarding complete if config exists
            if CLAUDE_CONFIG_FILE.exists() and not _is_claude_config_complete():
                try:
                    config = json.loads(CLAUDE_CONFIG_FILE.read_text())
                    config["hasCompletedOnboarding"] = True
                    CLAUDE_CONFIG_FILE.write_text(json.dumps(config, indent=2) + "\n")
                    print("[green]+[/green] Claude Code onboarding marked complete")
                except (json.JSONDecodeError, OSError):
                    pass

    # SSH key setup
    print()
    print("[yellow]SSH Key Setup[/yellow]")
    print()

    if non_interactive:
        print("[dim]Skipping SSH key setup in non-interactive mode[/dim]")
        return

    # Discover existing SSH keys
    existing_keys = discover_ssh_keys()
    keys_with_pub = [k for k in existing_keys if k["has_public"]]

    if keys_with_pub:
        # Show what keys were found
        print(f"[dim]Found {len(keys_with_pub)} SSH key(s):[/dim]")
        for key in keys_with_pub:
            key_type = f" ({key['key_type']})" if key["key_type"] else ""
            hosts = f" [hosts: {', '.join(key['hosts'])}]" if key["hosts"] else ""
            print(f"  [dim]• {key['name']}{key_type}{hosts}[/dim]")
        print()

        show_key = inquirer.confirm(
            message="Would you like to view a public key?",
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
            message="No SSH keys found. Would you like to create one for GitHub?",
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
