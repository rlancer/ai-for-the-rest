# AI for the Rest - Environment Setup

Setup scripts to install a development environment with AI coding assistants on Windows and macOS.

## Quick Install

### Windows

**Option 1: Win+R (Run dialog)**

Press `Win+R` and paste:

```
powershell -ep Bypass -c "irm https://raw.githubusercontent.com/rlancer/dangerous-ai/main/scripts/setup.ps1 | iex"
```

**Option 2: PowerShell**

Open PowerShell and run:

```powershell
irm https://raw.githubusercontent.com/rlancer/dangerous-ai/main/scripts/setup.ps1 | iex
```

### macOS

Open Terminal and run:

```bash
curl -fsSL https://raw.githubusercontent.com/rlancer/dangerous-ai/main/scripts/setup.sh | bash
```

## Requirements

### Windows
- Windows 10/11
- Classic PowerShell (not PowerShell Core)

### macOS
- macOS 10.15 (Catalina) or later
- Homebrew (will be installed automatically if not present)

## What Gets Installed

### Windows (via Scoop)

| Package | Description |
|---------|-------------|
| duckdb | In-process SQL OLAP database |
| Hack-NF | Hack Nerd Font |
| mise | Polyglot runtime manager |
| pwsh | PowerShell Core |
| starship | Cross-shell prompt |
| touch | Create files |
| vscode | Visual Studio Code |
| which | Locate commands |
| windows-terminal | Modern terminal |

### macOS (via Homebrew)

| Package | Description |
|---------|-------------|
| duckdb | In-process SQL OLAP database |
| font-hack-nerd-font | Hack Nerd Font |
| iterm2 | Terminal emulator |
| mise | Polyglot runtime manager |
| starship | Cross-shell prompt |
| visual-studio-code | Visual Studio Code |

### Via Mise (Both Platforms)

| Package | Description |
|---------|-------------|
| bun | Fast JavaScript runtime |

### AI CLI Tools (via Bun, Both Platforms)

| Package | Command | Description |
|---------|---------|-------------|
| @anthropic-ai/claude-code | `claude` | Anthropic's CLI for Claude |
| @openai/codex | `codex` | OpenAI's Codex CLI |
| @google/gemini-cli | `gemini` | Google's Gemini CLI |

## Post-Setup

The scripts automatically configure shell profiles for mise and starship.

### Windows

1. Open Windows Terminal
2. (Optional) Configure Starship by creating `~/.config/starship.toml`
3. Set your API keys:
   ```powershell
   $env:ANTHROPIC_API_KEY = "your-key"
   $env:OPENAI_API_KEY = "your-key"
   $env:GEMINI_API_KEY = "your-key"
   ```
4. Run `claude`, `codex`, or `gemini` to start coding with AI

### macOS

1. Open a new terminal (or run `source ~/.zshrc`)
2. (Optional) Configure Starship by creating `~/.config/starship.toml`
3. Set your API keys:
   ```bash
   export ANTHROPIC_API_KEY="your-key"
   export OPENAI_API_KEY="your-key"
   export GEMINI_API_KEY="your-key"
   ```
   Or add them to your `~/.zshrc` for persistence.
4. Run `claude`, `codex`, or `gemini` to start coding with AI
