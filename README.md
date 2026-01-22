# AI for the Rest of Us

```
    ___    ________________
   /   |  / ____/_  __/ __ \
  / /| | / /_    / / / /_/ /
 / ___ |/ __/   / / / _, _/
/_/  |_/_/     /_/ /_/ |_|

===============================
  A I   f o r   T h e   R e s t
===============================
```

One-command setup to supercharge your work with AI coding tools - no programming experience required.

## Who Is This For?

You're not a software developer, but you have real problems to solve at work. You need to analyze messy data, automate repetitive tasks, or build tools that don't exist yet. This project sets you up with AI assistants that can do the technical heavy lifting while you focus on the problem.

## What Can You Actually Do?

With AI coding tools, non-programmers can tackle tasks that used to require hiring a developer:

- **Data Analysis** - Query large datasets, find patterns, generate reports
- **Data Cleaning** - Transform messy CSVs, deduplicate records, standardize formats
- **Browser Automation** - Scrape websites, fill forms, automate repetitive web tasks
- **File Processing** - Batch rename, convert formats, extract information from PDFs
- **Custom Tools** - Build small apps tailored to your specific workflow
- **API Integrations** - Connect services together, pull data from various sources

## Why "The Rest of Us"?

This phrase comes from Apple's 1984 Macintosh slogan: "The computer for the rest of us." It meant computers weren't just for programmers anymore. The same shift is happening now with AI coding tools - you don't need to be a developer to build software. You describe what you need, and AI writes the code.

## Why CLI Tools Over Chat Interfaces?

AI coding assistants like Claude Code, Codex, and Gemini CLI run directly in your terminal. They're fundamentally different from chatting with AI in a browser:

| CLI Tools | Chat Interfaces |
|-----------|-----------------|
| Read and write files directly on your machine | Copy-paste code back and forth |
| Execute commands and see real output | Guess at what might work |
| Understand your entire project context | Limited to what you paste in |
| Process your actual data files | Work with toy examples |
| Run scripts and fix errors automatically | Manual iteration loop |
| Works with your local files | Everything lives in the browser |

The CLI tools turn AI from a "coding assistant you talk to" into a "coding partner that works alongside you" - it can see your files, run code, and iterate until the job is done.

## Quick Install

This repository provides two main components:
1. **Environment Setup** - One-command installation of development tools and AI assistants
2. **Project Tools** - CLI for scaffolding data science projects

### Environment Setup

#### Windows

Open PowerShell and run:

```powershell
irm https://raw.githubusercontent.com/rlancer/ai-for-the-rest/main/scripts/setup.ps1 | iex
```

#### macOS

Open Terminal and run:

```bash
curl -fsSL https://raw.githubusercontent.com/rlancer/ai-for-the-rest/main/scripts/setup.sh | bash
```

**After setup completes:**

1. Open a new terminal window (Windows Terminal on Windows, iTerm2/Terminal.app on macOS)
2. Run: `aftr setup`
   - This will prompt you to select which AI CLI tools to install
   - Optionally configure SSH keys

Or for non-interactive setup with defaults (Claude Code only, skip SSH):
```bash
aftr setup --non-interactive
```

### Project Scaffolding with aftr

After environment setup, use the `aftr` CLI to create data science projects with `uvx` (no installation required):

```bash
# Interactive mode
uvx aftr

# Create a new project directly
uvx aftr init my-project
uvx aftr init my-project --path /custom/path
```

**What aftr creates:**
```
my-project/
├── data/              # Input data (gitignored)
├── notebooks/         # Jupyter notebooks with example.ipynb
├── outputs/           # Output files (gitignored)
├── src/my_project/    # Python module (hyphens → underscores)
├── .gitignore
├── .mise.toml         # Python 3.12, UV latest
├── pyproject.toml     # pandas, polars, jupyter, papermill
└── README.md
```

**Custom templates:** aftr supports custom project templates with different dependencies and files. See the [template documentation](packages/cli/README.md#project-templates) for details on creating and managing templates.

## Requirements

### Windows
- Windows 10/11
- Classic PowerShell (not PowerShell Core)

### macOS
- macOS 10.15 (Catalina) or later
- Homebrew (will be installed automatically if not present)

## What Gets Installed

### Environment Tools

#### Windows (via Scoop)

| Package | Description |
|---------|-------------|
| duckdb | In-process SQL OLAP database |
| Hack-NF | Hack Nerd Font |
| mise | Polyglot runtime manager |
| pwsh | PowerShell Core |
| starship | Cross-shell prompt |
| touch | Create files |
| uv | Fast Python package manager |
| vscode | Visual Studio Code |
| which | Locate commands |
| windows-terminal | Modern terminal |

#### macOS (via Homebrew)

| Package | Description |
|---------|-------------|
| bun | Fast JavaScript runtime |
| duckdb | In-process SQL OLAP database |
| font-hack-nerd-font | Hack Nerd Font |
| iterm2 | Terminal emulator |
| mise | Polyglot runtime manager |
| starship | Cross-shell prompt |
| uv | Fast Python package manager |
| visual-studio-code | Visual Studio Code |

#### AI CLI Tools

Selected interactively during `aftr setup`:

| Tool | Command | Installation | Platforms |
|------|---------|--------------|-----------|
| Claude Code | `claude` | Native installer | Windows, macOS |
| Codex | `codex` | Bun global | macOS only |
| Gemini CLI | `gemini` | Bun global | macOS only |

**Note:** Claude Code (recommended) uses Anthropic's official native installer and works on both platforms. Codex and Gemini CLI require Bun, which is only installed on macOS.

### Project Tools

#### aftr CLI (via uvx)

The `aftr` project scaffolding tool runs directly with `uvx` - no installation needed:

| Command | Description |
|---------|-------------|
| `uvx aftr` | Interactive project creation menu |
| `uvx aftr init <name>` | Create a new data science project |
| `uvx aftr init <name> -p <path>` | Create project at custom path |

**Included in scaffolded projects:**
- pandas & polars for data analysis
- jupyter & papermill for notebooks
- pytest & ruff for testing and linting
- mise for tool version management
- UV for fast Python package management

## Post-Setup

### Environment Configuration

The setup scripts automatically:
- Configure shell profiles for mise and starship
- Install base tools (Python, UV, aftr)

You then complete the configuration by running `aftr setup` to select AI tools.

#### Windows

1. Open a new Windows Terminal window
2. Run `aftr setup` to select AI CLI tools (Claude Code, Codex, and/or Gemini)
3. (Optional) Configure Starship by creating `~/.config/starship.toml`
4. Set your API keys:
   ```powershell
   $env:ANTHROPIC_API_KEY = "your-key"
   $env:OPENAI_API_KEY = "your-key"      # If you selected Codex
   $env:GEMINI_API_KEY = "your-key"      # If you selected Gemini
   ```
5. Run `claude`, `codex`, or `gemini` (depending on what you installed) to start coding with AI

#### macOS

1. Open a new terminal window (iTerm2, Terminal.app, etc.)
2. Run `aftr setup` to select AI CLI tools (Claude Code, Codex, and/or Gemini)
3. (Optional) Configure Starship by creating `~/.config/starship.toml`
4. Set your API keys:
   ```bash
   export ANTHROPIC_API_KEY="your-key"
   export OPENAI_API_KEY="your-key"      # If you selected Codex
   export GEMINI_API_KEY="your-key"      # If you selected Gemini
   ```
   Or add them to your `~/.zshrc` for persistence.
5. Run `claude`, `codex`, or `gemini` (depending on what you installed) to start coding with AI
