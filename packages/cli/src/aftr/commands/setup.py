"""Setup command - configure AI tools and SSH keys after environment setup."""

import platform
import subprocess
from pathlib import Path

import typer
from InquirerPy import inquirer
from InquirerPy.utils import get_style
from rich import print
from rich.panel import Panel


def _check_windows_ssh_agent() -> None:
    """Check if Windows SSH agent is running and provide instructions if not."""
    if platform.system() != "Windows":
        return

    try:
        # Check if ssh-agent service exists and is running
        result = subprocess.run(
            [
                "powershell",
                "-Command",
                "(Get-Service ssh-agent -ErrorAction SilentlyContinue).Status",
            ],
            capture_output=True,
            text=True,
        )
        status = result.stdout.strip()

        if status == "Running":
            print()
            print("[green]✓[/green] Windows SSH agent is running")
            print()
            print("[yellow]To add your key to the agent, run:[/yellow]")
            print("  [cyan]ssh-add ~/.ssh/id_ed25519[/cyan]")
        elif status in ("Stopped", ""):
            print()
            print("[yellow]⚠ Windows SSH agent is not running[/yellow]")
            print()
            print("[yellow]To enable SSH agent (requires Administrator):[/yellow]")
            print("  [cyan]Set-Service ssh-agent -StartupType Automatic[/cyan]")
            print("  [cyan]Start-Service ssh-agent[/cyan]")
            print()
            print("[yellow]Then add your key to the agent:[/yellow]")
            print("  [cyan]ssh-add ~/.ssh/id_ed25519[/cyan]")
        else:
            # Service might not exist (older Windows or OpenSSH not installed)
            print()
            print("[yellow]⚠ Windows SSH agent service not found[/yellow]")
            print()
            print("[dim]OpenSSH may not be installed. You can install it via:[/dim]")
            print("  [cyan]Settings > Apps > Optional Features > OpenSSH Client[/cyan]")

    except (subprocess.CalledProcessError, FileNotFoundError):
        # PowerShell not available or other error - skip silently
        pass


def _install_claude_code() -> bool:
    """Install Claude Code using the official native installer.

    Returns True if installation succeeded, False otherwise.
    """
    system = platform.system()

    if system == "Windows":
        # Use PowerShell with the official installer
        result = subprocess.run(
            ["powershell", "-Command", "irm https://claude.ai/install.ps1 | iex"],
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

    home = Path.home()
    ssh_dir = home / ".ssh"
    ssh_key = ssh_dir / "id_ed25519"
    ssh_pub_key = ssh_dir / "id_ed25519.pub"

    if non_interactive:
        print("[dim]Skipping SSH key setup in non-interactive mode[/dim]")
        return

    if ssh_pub_key.exists():
        setup_ssh = inquirer.confirm(
            message="An SSH key already exists. Do you want to view it?",
            default=True,
            style=get_style(
                {
                    "questionmark": "#E91E63 bold",
                    "answer": "#00BCD4 bold",
                }
            ),
        ).execute()

        if setup_ssh:
            pub_key = ssh_pub_key.read_text().strip()
            print()
            print("[cyan]" + "=" * 60 + "[/cyan]")
            print("[yellow]Your SSH public key (copy this to GitHub):[/yellow]")
            print("[cyan]" + "=" * 60 + "[/cyan]")
            print()
            print(f"[white]{pub_key}[/white]")
            print()
            print("[cyan]" + "=" * 60 + "[/cyan]")
            print()
            print("[yellow]To add this key to GitHub:[/yellow]")
            print("  [dim]1. Go to https://github.com/settings/keys[/dim]")
            print("  [dim]2. Click 'New SSH key'[/dim]")
            print("  [dim]3. Paste the key above and save[/dim]")

            _check_windows_ssh_agent()
    else:
        setup_ssh = inquirer.confirm(
            message="Would you like to set up an SSH key for GitHub?",
            default=True,
            style=get_style(
                {
                    "questionmark": "#E91E63 bold",
                    "answer": "#00BCD4 bold",
                }
            ),
        ).execute()

        if setup_ssh:
            email = inquirer.text(
                message="Enter your email for the SSH key:",
                validate=lambda x: len(x) > 0 and "@" in x,
                invalid_message="Please enter a valid email address",
                style=get_style(
                    {
                        "questionmark": "#E91E63 bold",
                        "answer": "#00BCD4 bold",
                    }
                ),
            ).execute()

            if email:
                print()
                print("[yellow]Generating SSH key (ed25519)...[/yellow]")

                # Create .ssh directory if it doesn't exist
                ssh_dir.mkdir(mode=0o700, exist_ok=True)

                try:
                    subprocess.run(
                        [
                            "ssh-keygen",
                            "-t",
                            "ed25519",
                            "-C",
                            email,
                            "-f",
                            str(ssh_key),
                            "-N",
                            "",
                        ],
                        check=True,
                        capture_output=True,
                        text=True,
                    )
                    print("[green]✓[/green] SSH key generated!")

                    # Display the public key
                    if ssh_pub_key.exists():
                        pub_key = ssh_pub_key.read_text().strip()
                        print()
                        print("[cyan]" + "=" * 60 + "[/cyan]")
                        print(
                            "[yellow]Your SSH public key (copy this to GitHub):[/yellow]"
                        )
                        print("[cyan]" + "=" * 60 + "[/cyan]")
                        print()
                        print(f"[white]{pub_key}[/white]")
                        print()
                        print("[cyan]" + "=" * 60 + "[/cyan]")
                        print()
                        print("[yellow]To add this key to GitHub:[/yellow]")
                        print("  [dim]1. Go to https://github.com/settings/keys[/dim]")
                        print("  [dim]2. Click 'New SSH key'[/dim]")
                        print("  [dim]3. Paste the key above and save[/dim]")

                        _check_windows_ssh_agent()

                except subprocess.CalledProcessError as e:
                    print(f"[red]✗[/red] Failed to generate SSH key: {e.stderr}")
                except FileNotFoundError:
                    print("[red]✗[/red] ssh-keygen not found. Please install OpenSSH.")
        else:
            print("[dim]Skipping SSH key setup[/dim]")

    print()
    print("[green]Setup complete![/green]")
