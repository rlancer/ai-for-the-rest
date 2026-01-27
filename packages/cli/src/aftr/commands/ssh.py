"""SSH key and agent management command."""

import platform
import re
import subprocess
from pathlib import Path

import typer
from InquirerPy import inquirer
from InquirerPy.utils import get_style
from rich import print
from rich.panel import Panel

# Default SSH key paths (used for generation)
SSH_DIR = Path.home() / ".ssh"
SSH_KEY = SSH_DIR / "id_ed25519"
SSH_PUB_KEY = SSH_DIR / "id_ed25519.pub"

# Common SSH key names to look for (private key names, without .pub)
COMMON_KEY_NAMES = [
    "id_ed25519",
    "id_rsa",
    "id_ecdsa",
    "id_ed25519_sk",
    "id_ecdsa_sk",
    "id_dsa",
]


def discover_ssh_keys() -> list[dict]:
    """Discover all SSH keys in ~/.ssh directory.

    Returns list of dicts with:
        - name: Key filename (without path)
        - private_path: Path to private key
        - public_path: Path to public key (if exists)
        - has_public: Whether public key exists
        - key_type: Type of key (ed25519, rsa, etc.) if detectable
        - comment: Key comment from public key (usually email)
        - hosts: List of hosts this key is configured for in ssh config
    """
    keys = []

    if not SSH_DIR.exists():
        return keys

    # Find all potential private keys (files without .pub extension that have a .pub counterpart
    # or are in the common key names list)
    for item in SSH_DIR.iterdir():
        if not item.is_file():
            continue

        # Skip public keys, known_hosts, config, etc.
        if item.suffix in (".pub", ".old"):
            continue
        if item.name in ("known_hosts", "config", "authorized_keys", "environment"):
            continue

        # Check if this looks like a private key
        pub_path = item.with_suffix(item.suffix + ".pub") if item.suffix else SSH_DIR / f"{item.name}.pub"

        # Either has a .pub counterpart or is a known key name
        if pub_path.exists() or item.name in COMMON_KEY_NAMES:
            key_info = {
                "name": item.name,
                "private_path": item,
                "public_path": pub_path if pub_path.exists() else None,
                "has_public": pub_path.exists(),
                "key_type": None,
                "comment": None,
                "hosts": [],
            }

            # Try to extract key type and comment from public key
            if pub_path.exists():
                try:
                    pub_content = pub_path.read_text().strip()
                    parts = pub_content.split(None, 2)
                    if len(parts) >= 1:
                        # Key type is the first part (ssh-ed25519, ssh-rsa, etc.)
                        key_type = parts[0].replace("ssh-", "")
                        key_info["key_type"] = key_type
                    if len(parts) >= 3:
                        key_info["comment"] = parts[2]
                except (OSError, IndexError):
                    pass

            keys.append(key_info)

    # Parse SSH config to find which hosts use which keys
    config_path = SSH_DIR / "config"
    if config_path.exists():
        try:
            config_content = config_path.read_text()
            # Parse Host blocks and their IdentityFile settings
            current_hosts = []
            for line in config_content.splitlines():
                line = line.strip()
                if line.lower().startswith("host "):
                    current_hosts = line[5:].split()
                elif line.lower().startswith("identityfile "):
                    identity_file = line[13:].strip()
                    # Expand ~ to home directory
                    identity_file = identity_file.replace("~", str(Path.home()))
                    identity_path = Path(identity_file)
                    # Match this identity file to our discovered keys
                    for key in keys:
                        if key["private_path"] == identity_path or key["private_path"].name == identity_path.name:
                            key["hosts"].extend(current_hosts)
        except OSError:
            pass

    return keys


def get_default_key() -> dict | None:
    """Get the default SSH key (id_ed25519 or first available).

    Returns key info dict or None if no keys found.
    """
    keys = discover_ssh_keys()
    if not keys:
        return None

    # Prefer id_ed25519
    for key in keys:
        if key["name"] == "id_ed25519":
            return key

    # Fall back to first key with a public key
    for key in keys:
        if key["has_public"]:
            return key

    # Fall back to any key
    return keys[0] if keys else None

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
        - uses_windows_openssh: True if configured to use Windows native OpenSSH
        - issues: List of potential issues found
    """
    result = {
        "configured": True,
        "ssh_command": None,
        "uses_windows_openssh": False,
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
        # Check if using Windows native OpenSSH
        windows_ssh = "C:/Windows/System32/OpenSSH/ssh.exe"
        if result["ssh_command"] and windows_ssh.lower() in result["ssh_command"].lower():
            result["uses_windows_openssh"] = True
        elif not result["ssh_command"]:
            # No custom SSH command - git will use whatever ssh is in PATH
            # This may be Git Bash's ssh which doesn't work with Windows agent
            result["issues"].append("git not configured to use Windows OpenSSH (may not work with Windows SSH agent)")

    return result


def configure_git_windows_openssh() -> bool:
    """Configure git to use Windows native OpenSSH.

    This allows git to work with the Windows SSH agent service.

    Returns True if configuration was successful.
    """
    system = platform.system()

    if system != "Windows":
        print("[dim]This configuration is only needed on Windows[/dim]")
        return False

    windows_ssh = "C:/Windows/System32/OpenSSH/ssh.exe"

    # Check if Windows OpenSSH exists
    if not Path(windows_ssh).exists():
        print("[red]x[/red] Windows OpenSSH not found at expected location")
        print("[dim]Install OpenSSH via: Settings > Apps > Optional Features > OpenSSH Client[/dim]")
        return False

    print("[yellow]Configuring git to use Windows native OpenSSH...[/yellow]")

    try:
        result = subprocess.run(
            ["git", "config", "--global", "core.sshCommand", windows_ssh],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            print("[green]+[/green] Git configured to use Windows OpenSSH")
            print(f"  [dim]core.sshCommand = {windows_ssh}[/dim]")
            print()
            print("[dim]This allows git to work with the Windows SSH agent service.[/dim]")
            return True
        else:
            print("[red]x[/red] Failed to configure git")
            if result.stderr:
                print(f"  [dim]{result.stderr.strip()}[/dim]")
            return False

    except FileNotFoundError:
        print("[red]x[/red] git command not found")
        return False


def view_public_key(key_path: Path | None = None) -> bool:
    """Display the SSH public key for copying.

    Args:
        key_path: Path to the public key file. If None, discovers keys and prompts user.

    Returns True if key was displayed, False if no key exists.
    """
    # If no specific key provided, discover available keys
    if key_path is None:
        keys = discover_ssh_keys()
        keys_with_pub = [k for k in keys if k["has_public"]]

        if not keys_with_pub:
            print("[yellow]No SSH public keys found in ~/.ssh/[/yellow]")
            print("[dim]Use 'Generate SSH Key' to create one[/dim]")
            return False

        if len(keys_with_pub) == 1:
            # Only one key, use it
            key_path = keys_with_pub[0]["public_path"]
            key_name = keys_with_pub[0]["name"]
        else:
            # Multiple keys, let user choose
            choices = []
            for key in keys_with_pub:
                label = key["name"]
                if key["key_type"]:
                    label += f" ({key['key_type']})"
                if key["comment"]:
                    label += f" - {key['comment']}"
                if key["hosts"]:
                    label += f" [hosts: {', '.join(key['hosts'])}]"
                choices.append({"name": label, "value": key})

            print()
            selected = inquirer.select(
                message="Which key would you like to view?",
                choices=choices,
                pointer=">",
                style=PROMPT_STYLE,
            ).execute()

            key_path = selected["public_path"]
            key_name = selected["name"]
    else:
        key_name = key_path.stem

    if not key_path.exists():
        print(f"[yellow]Public key not found: {key_path}[/yellow]")
        return False

    pub_key = key_path.read_text().strip()
    print()
    print("[cyan]" + "=" * 60 + "[/cyan]")
    print(f"[yellow]SSH public key: {key_name}[/yellow]")
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
        print("[green]+[/green] SSH key generated!")
        print()
        view_public_key()
        return True

    except subprocess.CalledProcessError as e:
        print(f"[red]x[/red] Failed to generate SSH key: {e.stderr}")
        return False
    except FileNotFoundError:
        print("[red]x[/red] ssh-keygen not found. Please install OpenSSH.")
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
                print("[green]+[/green] SSH agent started!")
                return True
            else:
                print("[red]x[/red] Failed to start SSH agent")
                print()
                print("[yellow]Run these commands as Administrator:[/yellow]")
                print("  [cyan]Start-Service ssh-agent[/cyan]")
                if result.stderr:
                    print(f"  [dim]Error: {result.stderr.strip()}[/dim]")
                return False
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("[red]x[/red] Could not start SSH agent")
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
                print("[green]+[/green] SSH agent started!")
                print()
                print("[yellow]Run this in your shell to use the agent:[/yellow]")
                print(f"  [cyan]eval $(ssh-agent -s)[/cyan]")
                return True
            else:
                print("[red]x[/red] Failed to start SSH agent")
                return False
        except FileNotFoundError:
            print("[red]x[/red] ssh-agent not found")
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
                print("[green]+[/green] SSH agent configured to start automatically!")
                return True
            else:
                print("[red]x[/red] Failed to configure auto-start")
                print()
                print("[yellow]Run this command as Administrator:[/yellow]")
                print("  [cyan]Set-Service ssh-agent -StartupType Automatic[/cyan]")
                if result.stderr:
                    print(f"  [dim]Error: {result.stderr.strip()}[/dim]")
                return False
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("[red]x[/red] Could not configure auto-start")
            return False

    elif system == "Darwin":  # macOS
        print("[green]+[/green] macOS SSH agent auto-starts via system LaunchAgent")
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


def add_key_to_agent(key_path: Path | None = None) -> bool:
    """Add SSH key to the agent.

    Args:
        key_path: Path to the private key. If None, discovers keys and prompts user.

    Returns True if key was added successfully.
    """
    # If no specific key provided, discover available keys
    if key_path is None:
        keys = discover_ssh_keys()

        if not keys:
            print("[yellow]No SSH keys found in ~/.ssh/[/yellow]")
            print("[dim]Use 'Generate SSH Key' to create one[/dim]")
            return False

        if len(keys) == 1:
            # Only one key, use it
            key_path = keys[0]["private_path"]
            key_name = keys[0]["name"]
        else:
            # Multiple keys, let user choose
            choices = []
            for key in keys:
                label = key["name"]
                if key["key_type"]:
                    label += f" ({key['key_type']})"
                if key["comment"]:
                    label += f" - {key['comment']}"
                if key["hosts"]:
                    label += f" [hosts: {', '.join(key['hosts'])}]"
                choices.append({"name": label, "value": key})

            print()
            selected = inquirer.select(
                message="Which key would you like to add to the agent?",
                choices=choices,
                pointer=">",
                style=PROMPT_STYLE,
            ).execute()

            key_path = selected["private_path"]
            key_name = selected["name"]
    else:
        key_name = key_path.name

    if not key_path.exists():
        print(f"[yellow]Private key not found: {key_path}[/yellow]")
        return False

    system = platform.system()

    print(f"[yellow]Adding {key_name} to SSH agent...[/yellow]")

    # On Windows, use the Windows OpenSSH ssh-add to work with the Windows agent
    if system == "Windows":
        ssh_add_cmd = "C:/Windows/System32/OpenSSH/ssh-add.exe"
        # Fall back to PATH if Windows OpenSSH not found
        if not Path(ssh_add_cmd).exists():
            ssh_add_cmd = "ssh-add"
    else:
        ssh_add_cmd = "ssh-add"

    try:
        if system == "Darwin":  # macOS
            # Use Apple keychain for persistence
            result = subprocess.run(
                [ssh_add_cmd, "--apple-use-keychain", str(key_path)],
                capture_output=True,
                text=True,
            )
        else:
            result = subprocess.run(
                [ssh_add_cmd, str(key_path)],
                capture_output=True,
                text=True,
            )

        if result.returncode == 0:
            print(f"[green]+[/green] {key_name} added to agent!")
            if system == "Darwin":
                print("[dim]Key will persist across reboots via Keychain[/dim]")
            return True
        else:
            print("[red]x[/red] Failed to add key to agent")
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
        print("[red]x[/red] ssh-add not found. Please install OpenSSH.")
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
            print("[green]+[/green] SSH connection to GitHub successful!")
            # Extract username if present
            if "Hi " in output:
                username = output.split("Hi ")[1].split("!")[0]
                print(f"  [dim]Authenticated as: {username}[/dim]")
            return True
        elif "permission denied" in output.lower():
            print("[red]x[/red] Permission denied - SSH key not recognized by GitHub")
            print()
            print("[yellow]Make sure you've added your public key to GitHub:[/yellow]")
            print("  [dim]https://github.com/settings/keys[/dim]")
            return False
        else:
            print(f"[yellow]Connection result:[/yellow]")
            print(f"  [dim]{output.strip()}[/dim]")
            return False

    except subprocess.TimeoutExpired:
        print("[red]x[/red] Connection timed out")
        return False
    except FileNotFoundError:
        print("[red]x[/red] ssh command not found. Please install OpenSSH.")
        return False


def show_status() -> None:
    """Show comprehensive SSH status."""
    print(Panel("[cyan]SSH Status[/cyan]"))
    print()

    # Discover all SSH keys
    keys = discover_ssh_keys()

    # SSH Key status
    print("[yellow]SSH Keys:[/yellow]")
    if keys:
        for key in keys:
            status_icon = "[green]+[/green]" if key["has_public"] else "[yellow]![/yellow]"
            key_type = f" ({key['key_type']})" if key["key_type"] else ""
            print(f"  {status_icon} {key['name']}{key_type}")

            # Show comment (usually email)
            if key["comment"]:
                print(f"      [dim]Comment: {key['comment']}[/dim]")

            # Show hosts this key is configured for
            if key["hosts"]:
                print(f"      [dim]Hosts: {', '.join(key['hosts'])}[/dim]")

            # Show fingerprint if public key exists
            if key["has_public"]:
                try:
                    result = subprocess.run(
                        ["ssh-keygen", "-l", "-f", str(key["public_path"])],
                        capture_output=True,
                        text=True,
                    )
                    if result.returncode == 0:
                        print(f"      [dim]Fingerprint: {result.stdout.strip()}[/dim]")
                except (subprocess.CalledProcessError, FileNotFoundError):
                    pass

            if not key["has_public"]:
                print(f"      [dim]No public key found (.pub file missing)[/dim]")
    else:
        print("  [red]x[/red] No SSH keys found in ~/.ssh/")

    print()

    # SSH Agent status
    print("[yellow]SSH Agent:[/yellow]")
    status = get_ssh_agent_status()

    if status["status"] == "running":
        print(f"  [green]+[/green] {status['message']}")
    elif status["status"] == "stopped":
        print(f"  [yellow]![/yellow] {status['message']}")
    elif status["status"] == "not_installed":
        print(f"  [red]x[/red] {status['message']}")
    else:
        print(f"  [dim]{status['message']}[/dim]")

    if status["auto_start"] is not None:
        if status["auto_start"]:
            print("  [green]+[/green] Auto-start: Enabled")
        else:
            print("  [yellow]![/yellow] Auto-start: Disabled")

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
            if "not configured to use Windows OpenSSH" in issue:
                print(f"  [yellow]![/yellow] {issue}")
            else:
                print(f"  [red]x[/red] {issue}")
    else:
        print("  [green]+[/green] Git is available")

    if git_config["ssh_command"]:
        if git_config["uses_windows_openssh"]:
            print(f"  [green]+[/green] Using Windows native OpenSSH")
        print(f"  [dim]core.sshCommand: {git_config['ssh_command']}[/dim]")
    elif platform.system() == "Windows":
        print("  [dim]Using default SSH (may not work with Windows agent)[/dim]")
    else:
        print("  [dim]Using default SSH[/dim]")


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
        ]

        # Add Windows-specific option
        if platform.system() == "Windows":
            choices.append({"name": "Configure Git for Windows OpenSSH", "value": "gitconfig"})

        choices.append({"name": "Back", "value": "back"})

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

        elif action == "gitconfig":
            configure_git_windows_openssh()

        elif action == "back":
            return


def ssh(
    action: str = typer.Argument(
        None,
        help="Action: status, view, generate, add, start, autostart, test, gitconfig"
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
    gitconfig - Configure git to use Windows native OpenSSH (Windows only)
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
    elif action == "gitconfig":
        configure_git_windows_openssh()
    else:
        print(f"[red]Unknown action: {action}[/red]")
        print("[dim]Valid actions: status, view, generate, add, start, autostart, test, gitconfig[/dim]")
        raise typer.Exit(1)
