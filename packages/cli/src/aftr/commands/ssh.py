"""SSH key and agent management command."""

import platform
import subprocess
from pathlib import Path

import typer
from InquirerPy import inquirer
from InquirerPy.utils import get_style
from rich import print
from rich.panel import Panel

# Default SSH key paths
SSH_DIR = Path.home() / ".ssh"
SSH_KEY = SSH_DIR / "id_ed25519"
SSH_PUB_KEY = SSH_DIR / "id_ed25519.pub"

# Styling for InquirerPy
PROMPT_STYLE = get_style(
    {
        "questionmark": "#E91E63 bold",
        "pointer": "#00BCD4 bold",
        "highlighted": "#00BCD4 bold",
        "selected": "#4CAF50 bold",
        "answer": "#00BCD4 bold",
    }
)


def _run_powershell(command: str, check: bool = False) -> subprocess.CompletedProcess:
    """Run a PowerShell Core command."""
    return subprocess.run(
        ["pwsh", "-Command", command],
        capture_output=True,
        text=True,
        check=check,
    )


def _run_bash(command: str, check: bool = False) -> subprocess.CompletedProcess:
    """Run a bash command."""
    return subprocess.run(
        ["bash", "-c", command],
        capture_output=True,
        text=True,
        check=check,
    )


def get_ssh_agent_status() -> dict:
    """Get SSH agent status across platforms.

    Returns dict with:
        - status: "running", "stopped", "not_installed", or "unknown"
        - auto_start: True/False/None
        - message: Human-readable status
        - identities: List of loaded identities (if agent is running)
    """
    system = platform.system()
    result = {
        "status": "unknown",
        "auto_start": None,
        "message": "",
        "identities": [],
    }

    if system == "Windows":
        try:
            # Check service status
            status_result = _run_powershell(
                "(Get-Service ssh-agent -ErrorAction SilentlyContinue).Status"
            )
            status = status_result.stdout.strip()

            # Check startup type
            startup_result = _run_powershell(
                "(Get-Service ssh-agent -ErrorAction SilentlyContinue).StartType"
            )
            startup_type = startup_result.stdout.strip()

            if status == "Running":
                result["status"] = "running"
                result["message"] = "SSH agent is running"
                result["auto_start"] = startup_type == "Automatic"
            elif status in ("Stopped", ""):
                if status == "":
                    result["status"] = "not_installed"
                    result["message"] = "SSH agent service not found - OpenSSH may not be installed"
                else:
                    result["status"] = "stopped"
                    result["message"] = "SSH agent is stopped"
                    result["auto_start"] = startup_type == "Automatic"
            else:
                result["status"] = "unknown"
                result["message"] = f"SSH agent status: {status}"

        except (subprocess.CalledProcessError, FileNotFoundError):
            result["status"] = "unknown"
            result["message"] = "Could not determine SSH agent status"

    else:  # macOS/Linux
        try:
            # Check if SSH_AUTH_SOCK is set (agent is available)
            import os
            auth_sock = os.environ.get("SSH_AUTH_SOCK")

            if auth_sock and Path(auth_sock).exists():
                result["status"] = "running"
                result["message"] = "SSH agent is running"
                # macOS SSH agent auto-starts via LaunchAgent
                result["auto_start"] = True if system == "Darwin" else None
            else:
                result["status"] = "stopped"
                result["message"] = "SSH agent not running (SSH_AUTH_SOCK not set)"
                result["auto_start"] = True if system == "Darwin" else None

        except Exception:
            result["status"] = "unknown"
            result["message"] = "Could not determine SSH agent status"

    # Get loaded identities if agent is running
    if result["status"] == "running":
        try:
            list_result = subprocess.run(
                ["ssh-add", "-l"],
                capture_output=True,
                text=True,
            )
            if list_result.returncode == 0:
                lines = list_result.stdout.strip().split("\n")
                result["identities"] = [line for line in lines if line]
            # returncode 1 means "no identities" - that's okay
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

    return result


def check_git_ssh_config() -> dict:
    """Check if git is configured to use SSH properly.

    Returns dict with:
        - configured: True if SSH is likely configured correctly
        - ssh_command: The GIT_SSH_COMMAND if set
        - issues: List of potential issues found
    """
    result = {
        "configured": True,
        "ssh_command": None,
        "issues": [],
    }

    system = platform.system()

    # Check GIT_SSH_COMMAND environment variable
    try:
        import os
        ssh_command = os.environ.get("GIT_SSH_COMMAND")
        if ssh_command:
            result["ssh_command"] = ssh_command
    except Exception:
        pass

    # Check git config for core.sshCommand
    try:
        git_ssh_result = subprocess.run(
            ["git", "config", "--global", "core.sshCommand"],
            capture_output=True,
            text=True,
        )
        if git_ssh_result.returncode == 0 and git_ssh_result.stdout.strip():
            result["ssh_command"] = git_ssh_result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        result["issues"].append("git command not found")
        result["configured"] = False
        return result

    if system == "Windows":
        # On Windows, git should use the Windows OpenSSH to work with ssh-agent
        # Check if git is using the correct ssh
        if result["ssh_command"]:
            # Custom SSH command set - might be intentional
            pass
        else:
            # No custom SSH - that's usually fine if OpenSSH is in PATH
            pass

    return result


def view_public_key() -> bool:
    """Display the SSH public key for copying.

    Returns True if key was displayed, False if no key exists.
    """
    if not SSH_PUB_KEY.exists():
        print("[yellow]No SSH public key found at ~/.ssh/id_ed25519.pub[/yellow]")
        print("[dim]Use 'Generate SSH Key' to create one[/dim]")
        return False

    pub_key = SSH_PUB_KEY.read_text().strip()
    print()
    print("[cyan]" + "=" * 60 + "[/cyan]")
    print("[yellow]Your SSH public key (copy this to your Git provider):[/yellow]")
    print("[cyan]" + "=" * 60 + "[/cyan]")
    print()
    print(f"[white]{pub_key}[/white]")
    print()
    print("[cyan]" + "=" * 60 + "[/cyan]")
    print()
    print("[yellow]Add this key to:[/yellow]")
    print("  [dim]GitHub:    https://github.com/settings/keys[/dim]")
    print("  [dim]GitLab:    https://gitlab.com/-/user_settings/ssh_keys[/dim]")
    print("  [dim]Bitbucket: https://bitbucket.org/account/settings/ssh-keys/[/dim]")
    return True


def generate_ssh_key(email: str | None = None) -> bool:
    """Generate a new SSH key.

    Args:
        email: Email to use for the key comment. If None, will prompt.

    Returns True if key was generated successfully.
    """
    # Check if key already exists
    if SSH_KEY.exists():
        overwrite = inquirer.confirm(
            message="An SSH key already exists. Overwrite it?",
            default=False,
            style=PROMPT_STYLE,
        ).execute()

        if not overwrite:
            print("[dim]Keeping existing key[/dim]")
            return False

    # Get email if not provided
    if not email:
        email = inquirer.text(
            message="Enter your email for the SSH key:",
            validate=lambda x: len(x) > 0 and "@" in x,
            invalid_message="Please enter a valid email address",
            style=PROMPT_STYLE,
        ).execute()

        if not email:
            return False

    print()
    print("[yellow]Generating SSH key (ed25519)...[/yellow]")

    # Create .ssh directory if it doesn't exist
    SSH_DIR.mkdir(mode=0o700, exist_ok=True)

    try:
        subprocess.run(
            [
                "ssh-keygen",
                "-t", "ed25519",
                "-C", email,
                "-f", str(SSH_KEY),
                "-N", "",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        print("[green]✓[/green] SSH key generated!")
        print()
        view_public_key()
        return True

    except subprocess.CalledProcessError as e:
        print(f"[red]✗[/red] Failed to generate SSH key: {e.stderr}")
        return False
    except FileNotFoundError:
        print("[red]✗[/red] ssh-keygen not found. Please install OpenSSH.")
        return False


def start_ssh_agent() -> bool:
    """Start the SSH agent service.

    Returns True if agent is now running.
    """
    system = platform.system()

    if system == "Windows":
        print("[yellow]Starting SSH agent (requires Administrator)...[/yellow]")
        print()

        # Try to start the service
        try:
            result = _run_powershell("Start-Service ssh-agent")
            if result.returncode == 0:
                print("[green]✓[/green] SSH agent started!")
                return True
            else:
                print("[red]✗[/red] Failed to start SSH agent")
                print()
                print("[yellow]Run these commands as Administrator:[/yellow]")
                print("  [cyan]Start-Service ssh-agent[/cyan]")
                if result.stderr:
                    print(f"  [dim]Error: {result.stderr.strip()}[/dim]")
                return False
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("[red]✗[/red] Could not start SSH agent")
            return False

    else:  # macOS/Linux
        print("[yellow]Starting SSH agent...[/yellow]")
        try:
            # Start ssh-agent and get the environment variables
            result = subprocess.run(
                ["ssh-agent", "-s"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                print("[green]✓[/green] SSH agent started!")
                print()
                print("[yellow]Run this in your shell to use the agent:[/yellow]")
                print(f"  [cyan]eval $(ssh-agent -s)[/cyan]")
                return True
            else:
                print("[red]✗[/red] Failed to start SSH agent")
                return False
        except FileNotFoundError:
            print("[red]✗[/red] ssh-agent not found")
            return False


def enable_auto_start() -> bool:
    """Configure SSH agent to start automatically.

    Returns True if auto-start was configured.
    """
    system = platform.system()

    if system == "Windows":
        print("[yellow]Configuring SSH agent auto-start (requires Administrator)...[/yellow]")
        print()

        try:
            result = _run_powershell("Set-Service ssh-agent -StartupType Automatic")
            if result.returncode == 0:
                print("[green]✓[/green] SSH agent configured to start automatically!")
                return True
            else:
                print("[red]✗[/red] Failed to configure auto-start")
                print()
                print("[yellow]Run this command as Administrator:[/yellow]")
                print("  [cyan]Set-Service ssh-agent -StartupType Automatic[/cyan]")
                if result.stderr:
                    print(f"  [dim]Error: {result.stderr.strip()}[/dim]")
                return False
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("[red]✗[/red] Could not configure auto-start")
            return False

    elif system == "Darwin":  # macOS
        print("[green]✓[/green] macOS SSH agent auto-starts via system LaunchAgent")
        print()
        print("[dim]To persist keys across reboots, add them with:[/dim]")
        print("  [cyan]ssh-add --apple-use-keychain ~/.ssh/id_ed25519[/cyan]")
        return True

    else:  # Linux
        print("[yellow]SSH agent auto-start on Linux depends on your desktop environment.[/yellow]")
        print()
        print("[dim]Common approaches:[/dim]")
        print("  - GNOME/KDE: Usually handled automatically")
        print("  - Add to ~/.bashrc: [cyan]eval $(ssh-agent -s)[/cyan]")
        print("  - Use systemd user service for ssh-agent")
        return False


def add_key_to_agent() -> bool:
    """Add SSH key to the agent.

    Returns True if key was added successfully.
    """
    if not SSH_KEY.exists():
        print("[yellow]No SSH key found at ~/.ssh/id_ed25519[/yellow]")
        print("[dim]Use 'Generate SSH Key' to create one[/dim]")
        return False

    system = platform.system()

    print("[yellow]Adding SSH key to agent...[/yellow]")

    try:
        if system == "Darwin":  # macOS
            # Use Apple keychain for persistence
            result = subprocess.run(
                ["ssh-add", "--apple-use-keychain", str(SSH_KEY)],
                capture_output=True,
                text=True,
            )
        else:
            result = subprocess.run(
                ["ssh-add", str(SSH_KEY)],
                capture_output=True,
                text=True,
            )

        if result.returncode == 0:
            print("[green]✓[/green] SSH key added to agent!")
            if system == "Darwin":
                print("[dim]Key will persist across reboots via Keychain[/dim]")
            return True
        else:
            print("[red]✗[/red] Failed to add key to agent")
            if "Could not open a connection to your authentication agent" in result.stderr:
                print()
                print("[yellow]SSH agent is not running. Start it first:[/yellow]")
                if system == "Windows":
                    print("  [cyan]Start-Service ssh-agent[/cyan]")
                else:
                    print("  [cyan]eval $(ssh-agent -s)[/cyan]")
            elif result.stderr:
                print(f"  [dim]{result.stderr.strip()}[/dim]")
            return False

    except FileNotFoundError:
        print("[red]✗[/red] ssh-add not found. Please install OpenSSH.")
        return False


def test_github_connection() -> bool:
    """Test SSH connection to GitHub.

    Returns True if connection is successful.
    """
    print("[yellow]Testing SSH connection to GitHub...[/yellow]")
    print()

    try:
        result = subprocess.run(
            ["ssh", "-T", "git@github.com", "-o", "StrictHostKeyChecking=accept-new"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # GitHub returns exit code 1 even on success (it doesn't provide shell access)
        # Success message contains "successfully authenticated"
        output = result.stdout + result.stderr

        if "successfully authenticated" in output.lower():
            print("[green]✓[/green] SSH connection to GitHub successful!")
            # Extract username if present
            if "Hi " in output:
                username = output.split("Hi ")[1].split("!")[0]
                print(f"  [dim]Authenticated as: {username}[/dim]")
            return True
        elif "permission denied" in output.lower():
            print("[red]✗[/red] Permission denied - SSH key not recognized by GitHub")
            print()
            print("[yellow]Make sure you've added your public key to GitHub:[/yellow]")
            print("  [dim]https://github.com/settings/keys[/dim]")
            return False
        else:
            print(f"[yellow]Connection result:[/yellow]")
            print(f"  [dim]{output.strip()}[/dim]")
            return False

    except subprocess.TimeoutExpired:
        print("[red]✗[/red] Connection timed out")
        return False
    except FileNotFoundError:
        print("[red]✗[/red] ssh command not found. Please install OpenSSH.")
        return False


def show_status() -> None:
    """Show comprehensive SSH status."""
    print(Panel("[cyan]SSH Status[/cyan]"))
    print()

    # SSH Key status
    print("[yellow]SSH Key:[/yellow]")
    if SSH_PUB_KEY.exists():
        print(f"  [green]✓[/green] Key exists at {SSH_KEY}")
        # Show key fingerprint
        try:
            result = subprocess.run(
                ["ssh-keygen", "-l", "-f", str(SSH_PUB_KEY)],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                print(f"  [dim]Fingerprint: {result.stdout.strip()}[/dim]")
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
    else:
        print(f"  [red]✗[/red] No key found at {SSH_KEY}")

    print()

    # SSH Agent status
    print("[yellow]SSH Agent:[/yellow]")
    status = get_ssh_agent_status()

    if status["status"] == "running":
        print(f"  [green]✓[/green] {status['message']}")
    elif status["status"] == "stopped":
        print(f"  [yellow]⚠[/yellow] {status['message']}")
    elif status["status"] == "not_installed":
        print(f"  [red]✗[/red] {status['message']}")
    else:
        print(f"  [dim]{status['message']}[/dim]")

    if status["auto_start"] is not None:
        if status["auto_start"]:
            print("  [green]✓[/green] Auto-start: Enabled")
        else:
            print("  [yellow]⚠[/yellow] Auto-start: Disabled")

    if status["identities"]:
        print()
        print("  [dim]Loaded identities:[/dim]")
        for identity in status["identities"]:
            print(f"    [dim]{identity}[/dim]")
    elif status["status"] == "running":
        print("  [dim]No identities loaded in agent[/dim]")

    print()

    # Git SSH config
    print("[yellow]Git SSH Config:[/yellow]")
    git_config = check_git_ssh_config()

    if git_config["issues"]:
        for issue in git_config["issues"]:
            print(f"  [red]✗[/red] {issue}")
    else:
        print("  [green]✓[/green] Git is available")
        if git_config["ssh_command"]:
            print(f"  [dim]Custom SSH command: {git_config['ssh_command']}[/dim]")
        else:
            print("  [dim]Using default SSH (recommended)[/dim]")


def ssh_menu() -> None:
    """Show the SSH management submenu."""
    from rich.console import Console
    console = Console()

    while True:
        console.print()
        console.print(Panel("[cyan]SSH & Git Configuration[/cyan]"))
        console.print()

        choices = [
            {"name": "View Status", "value": "status"},
            {"name": "View Public Key", "value": "view"},
            {"name": "Generate SSH Key", "value": "generate"},
            {"name": "Add Key to Agent", "value": "add"},
            {"name": "Start SSH Agent", "value": "start"},
            {"name": "Enable Auto-Start", "value": "autostart"},
            {"name": "Test GitHub Connection", "value": "test"},
            {"name": "Back", "value": "back"},
        ]

        action = inquirer.select(
            message="SSH Options:",
            choices=choices,
            default="status",
            pointer=">",
            style=PROMPT_STYLE,
        ).execute()

        console.print()

        if action == "status":
            show_status()

        elif action == "view":
            view_public_key()

        elif action == "generate":
            generate_ssh_key()

        elif action == "add":
            add_key_to_agent()

        elif action == "start":
            start_ssh_agent()

        elif action == "autostart":
            enable_auto_start()

        elif action == "test":
            test_github_connection()

        elif action == "back":
            return


def ssh(
    action: str = typer.Argument(
        None,
        help="Action: status, view, generate, add, start, autostart, test"
    ),
) -> None:
    """Manage SSH keys and agent for Git authentication.

    Run without arguments for interactive menu, or specify an action:

    \b
    status    - Show SSH key, agent, and git configuration status
    view      - Display your public key for copying to Git providers
    generate  - Create a new SSH key
    add       - Add your key to the SSH agent
    start     - Start the SSH agent service
    autostart - Configure SSH agent to start automatically
    test      - Test SSH connection to GitHub
    """
    if action is None:
        ssh_menu()
        return

    action = action.lower()

    if action == "status":
        show_status()
    elif action == "view":
        view_public_key()
    elif action == "generate":
        generate_ssh_key()
    elif action == "add":
        add_key_to_agent()
    elif action == "start":
        start_ssh_agent()
    elif action == "autostart":
        enable_auto_start()
    elif action == "test":
        test_github_connection()
    else:
        print(f"[red]Unknown action: {action}[/red]")
        print("[dim]Valid actions: status, view, generate, add, start, autostart, test[/dim]")
        raise typer.Exit(1)
