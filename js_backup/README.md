# Steam Price Fetcher (Python Version)

A Python utility for fetching game prices from Steam and converting them between currencies.

## Features

- Fetches the complete list of Steam games (~200,000 titles)
- Retrieves pricing information in JPY
- Converts prices to USD, EUR, GBP and other currencies
- Processes games in batches of 1,000 to avoid rate limiting
- Generates reports on price distribution and discounts
- Uses modern Python tools (uv, ruff, pyproject.toml)

## Setup

1. Make sure you have Python 3.8+ installed
2. Install uv package manager:
   ```
   pip install uv
   ```
3. Install the package with development dependencies:
   ```
   uv pip install -e ".[dev]"
   ```
4. (Optional) Create a `.env` file for API keys if needed

## Usage

You can run the main script to fetch all data and generate reports:

```
python main.py
```

Or use the provided Makefile:

```
# Run the main script
make run

# Format code with ruff
make format

# Lint code with ruff
make lint

# Auto-fix linting issues
make fix
```

The script will:
1. Download the complete list of Steam apps
2. Fetch current exchange rates
3. Process games in batches, fetching price information
4. Save results to the `output` directory
5. Generate a price distribution report and list of biggest discounts

## Output Files

- `output/apps.json` - Complete list of Steam apps
- `output/prices.json` - Price data for all apps
- `output/exchange_rates.json` - Current exchange rates

## Development

This project uses:
- `pyproject.toml` for dependencies and project configuration
- `uv` for fast package installation and management
- `ruff` for linting and formatting
- Type annotations for better code quality

VS Code integration is provided via the `.vscode/settings.json` file, which configures automatic formatting and linting on save.

## Notes

- This project uses unofficial Steam API endpoints that may change
- The script implements rate limiting to avoid being blocked
- Fetching all prices may take several hours due to Steam's rate limits