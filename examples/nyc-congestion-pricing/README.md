# nyc-congestion-pricing

A data analysis project scaffolded with [aftr](https://github.com/rlancer/ai-for-the-rest).

## Setup

```bash
# Install dependencies with UV
uv sync

# Activate the virtual environment
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate     # Windows
```

## Running Notebooks

```bash
# Run a notebook with papermill
uv run papermill notebooks/example.ipynb outputs/example_output.ipynb
```

## Project Structure

```
nyc-congestion-pricing/
├── data/           # Input data (gitignored)
├── notebooks/      # Jupyter notebooks
├── outputs/        # Output files (gitignored)
├── src/nyc_congestion_pricing/  # Python source code
├── .mise.toml      # mise tool versions
└── pyproject.toml  # Project config
```
