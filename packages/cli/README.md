# aftr

CLI for bootstrapping Python data projects with UV, mise, and papermill.

## Installation

```bash
# Install globally with UV
uv tool install aftr

# Or run directly with uvx
uvx aftr init my-project
```

## Usage

### Initialize a new project

```bash
aftr init my-data-project
```

This creates a new directory with:
- `pyproject.toml` - UV project config with pandas, polars, jupyter, papermill
- `.mise.toml` - mise tool versions (Python, UV)
- `notebooks/` - Jupyter notebooks directory with example
- `src/` - Python source code
- `data/` - Input data (gitignored)
- `outputs/` - Output files (gitignored)

## Development

```bash
cd packages/cli
uv sync
uv run aftr --help
```
