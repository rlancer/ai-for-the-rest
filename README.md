# AI for the Rest - Environment Setup

A simple PowerShell script to set up a development environment on Windows with AI coding assistants.

## Project Structure

```
ai-for-the-rest/
├── config/
│   └── config.json      # Package definitions for all platforms
├── scripts/
│   ├── setup.ps1        # Windows setup script
│   └── setup.sh         # macOS setup script
├── tests/
│   ├── test-setup.ps1   # Test runner for Windows Sandbox
│   ├── test-wrapper.ps1 # Script that runs inside sandbox
│   ├── sandbox.wsb      # Basic sandbox config
│   └── test-sandbox.wsb # Test sandbox config
└── README.md
```

## Quick Install

Open PowerShell and run:

```powershell
irm https://raw.githubusercontent.com/rlancer/dangerous-ai/main/scripts/setup.ps1 | iex
```

## Requirements

- Windows 10/11
- Classic PowerShell (not PowerShell Core)

## What Gets Installed

### Via Scoop

| Package | Description |
|---------|-------------|
| 7zip | File archiver |
| antigravity | Python package manager helper |
| duckdb | In-process SQL OLAP database |
| git | Version control |
| Hack-NF | Hack Nerd Font |
| innounp | Inno Setup unpacker |
| mise | Polyglot runtime manager |
| pwsh | PowerShell Core |
| slack | Team communication |
| starship | Cross-shell prompt |
| touch | Create files |
| vcredist2022 | Visual C++ Redistributable |
| vscode | Visual Studio Code |
| which | Locate commands |
| windows-terminal | Modern terminal |

### Via Mise

| Package | Description |
|---------|-------------|
| bun | Fast JavaScript runtime |

### AI CLI Tools (via Bun)

| Package | Command | Description |
|---------|---------|-------------|
| @anthropic-ai/claude-code | `claude` | Anthropic's CLI for Claude |
| @openai/codex | `codex` | OpenAI's Codex CLI |
| @google/gemini-cli | `gemini` | Google's Gemini CLI |

## Post-Setup

The script automatically configures PowerShell profiles for mise and starship. After installation:

1. Open Windows Terminal
2. (Optional) Configure Starship by creating `~/.config/starship.toml`
3. Set your API keys:
   ```powershell
   $env:ANTHROPIC_API_KEY = "your-key"
   $env:OPENAI_API_KEY = "your-key"
   $env:GEMINI_API_KEY = "your-key"
   ```
4. Run `claude`, `codex`, or `gemini` to start coding with AI
