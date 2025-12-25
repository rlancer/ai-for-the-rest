# AI for the Rest - Environment Setup

A simple PowerShell script to set up a development environment on Windows.

## Requirements

- Windows 10/11
- Classic PowerShell (not PowerShell Core)

## Usage

Open PowerShell and run:

```powershell
.\setup.ps1
```

## What Gets Installed

The script installs [Scoop](https://scoop.sh/) and the following packages:

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
| which | Locate commands |
| windows-terminal | Modern terminal |

Additionally, the script installs via mise:

| Package | Description |
|---------|-------------|
| bun | Fast JavaScript runtime |
| claude-code | Anthropic's CLI for Claude |

## Post-Setup

After installation, you may want to:

1. Open Windows Terminal
2. Configure Starship by creating `~/.config/starship.toml`
3. Set your Anthropic API key: `$env:ANTHROPIC_API_KEY = "your-key"`
4. Run `claude` to start using Claude Code
