# Getting Started

This guide walks you through setting up AI coding tools on your machine — no programming experience required.

## What You're Installing

This setup gives you two things:

1. **A development environment** — the tools AI needs to actually work on your files (package managers, Python, a good terminal)
2. **AI coding assistants** — CLI tools like Claude Code that live in your terminal and can read/write files, run code, and iterate on your behalf

## Before You Begin

### Windows

- Windows 10 or 11
- Classic PowerShell (the one that opens from the Start menu — not PowerShell Core)
- An internet connection

### macOS

- macOS 10.15 (Catalina) or later
- An internet connection

---

## Step 1: Run the Setup Script

Open your terminal and paste the command for your operating system.

### Windows

1. Press **Win + X** and choose **Windows PowerShell** (not "PowerShell Core" or "Terminal")
2. Paste and press Enter:

```powershell
irm https://raw.githubusercontent.com/rlancer/ai-for-the-rest/main/scripts/setup.ps1 | iex
```

This will install: Scoop, git, DuckDB, uv, mise, starship, VS Code, Windows Terminal, and Claude Code.

### macOS

1. Open **Terminal** (press Cmd+Space and type "Terminal")
2. Paste and press Enter:

```bash
curl -fsSL https://raw.githubusercontent.com/rlancer/ai-for-the-rest/main/scripts/setup.sh | bash
```

This will install: Homebrew, git, DuckDB, uv, bun, mise, starship, VS Code, and iTerm2.

The setup takes a few minutes. You'll see progress messages as tools are installed.

---

## Step 2: Open a New Terminal Window

After setup completes, **close your current terminal and open a new one**. This ensures the new tools are available in your PATH.

- **Windows**: Open the new **Windows Terminal** that was just installed
- **macOS**: Open a new **iTerm2** window (or a new tab in Terminal.app)

---

## Step 3: Configure AI Tools

In the new terminal, run:

```bash
aftr setup
```

You'll be prompted to choose which AI coding assistants to install:

| Tool | Command | Notes |
|------|---------|-------|
| Claude Code | `claude` | Recommended. Works on Windows and macOS |
| Codex | `codex` | macOS only |
| Gemini CLI | `gemini` | macOS only |

Select one or more, and the setup will install them for you.

You'll also have the option to generate an SSH key for GitHub authentication.

### Non-interactive mode (skip the prompts)

If you want Claude Code with default settings and no SSH setup:

```bash
aftr setup --non-interactive
```

---

## Step 4: Set Your API Keys

AI tools require API keys to authenticate. Set them as environment variables:

### Windows (PowerShell)

```powershell
$env:ANTHROPIC_API_KEY = "your-key-here"
```

To make this permanent, add it to your PowerShell profile:

```powershell
notepad $PROFILE
```

Add the line above, save, and restart your terminal.

### macOS (zsh)

```bash
export ANTHROPIC_API_KEY="your-key-here"
```

To make this permanent, add it to `~/.zshrc`:

```bash
echo 'export ANTHROPIC_API_KEY="your-key-here"' >> ~/.zshrc
```

**Getting your API keys:**
- **Claude Code**: [console.anthropic.com](https://console.anthropic.com)
- **Codex**: [platform.openai.com](https://platform.openai.com)
- **Gemini**: [aistudio.google.com](https://aistudio.google.com)

---

## Step 5: Start a New Project

Use `aftr` to scaffold a data science project:

```bash
aftr init my-first-project
```

This creates a ready-to-use project folder:

```
my-first-project/
├── data/           # Put your input files here (CSVs, etc.)
├── notebooks/      # Jupyter notebooks for analysis
├── outputs/        # Results and generated files
├── src/            # Python source code
├── pyproject.toml  # Project dependencies
└── .mise.toml      # Tool version pinning
```

---

## Step 6: Use an AI Coding Assistant

Navigate into your project and start Claude Code:

```bash
cd my-first-project
claude
```

Claude can now see all your files. Try describing what you want to do:

> "I have a CSV in the data/ folder with sales records. Can you write a script to calculate total sales by region and save the output to outputs/?"

Claude will read your files, write the code, run it, and fix any errors — all without you needing to write a single line of code.

---

## Common Workflows

### Analyzing Data

1. Put your CSV/Excel file in `data/`
2. Run `claude` in your project directory
3. Describe what analysis you need

### Running a Notebook

```bash
cd my-first-project
uv run jupyter lab
```

Open a notebook in your browser, then describe changes you want to Claude.

### Installing Additional Python Packages

```bash
uv add pandas-profiling  # or any package you need
```

---

## Troubleshooting

### "aftr: command not found"

The `~/.local/bin` directory isn't in your PATH. Try:

```bash
# macOS/Linux
export PATH="$HOME/.local/bin:$PATH"

# Then add it permanently to ~/.zshrc
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
```

On Windows, uv tools are added to `%USERPROFILE%\.local\bin` — check that this is in your System PATH.

### "claude: command not found"

Re-run `aftr setup` and select Claude Code when prompted.

### Setup script fails on Windows

Make sure you're running classic PowerShell (not PowerShell Core). Right-click the Start button and choose **Windows PowerShell**.

---

## Next Steps

- [aftr CLI Reference](./aftr-cli-reference.md) — All available commands
- [Template Guide](./templates.md) — Create reusable project templates for your team
- [Architecture Overview](./architecture.md) — How the project is structured (for contributors)
