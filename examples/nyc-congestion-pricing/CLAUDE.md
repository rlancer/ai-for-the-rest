# CLAUDE.md

This file provides guidance to Claude Code when working with this project.

## Project Overview

nyc-congestion-pricing is a data analysis project scaffolded with aftr. This project uses modern Python data tools optimized for performance and ease of use.

## Tech Stack & Best Practices

### Data Processing
- **DuckDB**: Primary tool for all data tasks. DuckDB is an in-process SQL OLAP database optimized for analytics.
  - Use DuckDB for data loading, transformation, and analysis
  - DuckDB can query Parquet, CSV, and JSON files directly without loading into memory
  - Convert DuckDB relations to Polars DataFrames using `.pl()` method

- **Polars**: Use whenever you need a DataFrame for data manipulation
  - Polars is faster and more memory-efficient than pandas
  - DuckDB and Polars integrate seamlessly: `duckdb.sql("SELECT * FROM table").pl()`
  - Use Polars for DataFrame operations, complex transformations, and lazy evaluation

### Browser Automation
- **Playwright**: Use for all browser automation tasks
  - Web scraping
  - Data collection from websites
  - Automated testing of web interfaces
  - Screenshot capture and PDF generation

### Playwright MCP Server
- This project includes a Playwright MCP server configuration (`.mcp.json`)
- The MCP server provides Claude Code with browser automation capabilities
- Use it for interactive web scraping and testing tasks

## Workflow

1. **Data Collection**: Use Playwright for web scraping if needed
2. **Data Storage**: Save data as Parquet files in `data/` directory
3. **Data Analysis**: Use DuckDB for SQL-based analysis
4. **DataFrame Operations**: Convert DuckDB results to Polars with `.pl()` when needed
5. **Outputs**: Save results to `outputs/` directory

## Example Usage

```python
import duckdb
import polars as pl

# Query data with DuckDB and convert to Polars
df = duckdb.sql("SELECT * FROM 'data/input.parquet' WHERE amount > 100").pl()

# Continue processing with Polars
result = df.group_by("category").agg(pl.col("amount").sum())
```

## Key Patterns

- Favor DuckDB for data queries and aggregations
- Use Polars DataFrames for complex transformations
- Use Playwright for any browser automation needs
- Keep notebooks in `notebooks/` directory
- Store raw data in `data/` directory (gitignored)
- Save outputs to `outputs/` directory (gitignored)
