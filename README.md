# Steam Price Fetcher

A Python application for fetching and analyzing Steam game prices across multiple regions.

## Features

- Fetches the complete list of Steam games (~250,000 titles)
- Retrieves pricing information for multiple regions/currencies
- Converts prices between different currencies
- Processes games in batches to avoid API rate limiting
- Analyzes price differences between regions
- Stores data in pandas DataFrames for advanced analysis
- Generates visualizations for price distributions and regional comparisons
- Uses modern Python tools (uv, ruff, pyproject.toml)
- Comprehensive logging system

## Setup

1. Make sure you have Python 3.9+ installed
2. Install uv package manager:
   ```
   pip install uv
   ```
3. Install the package with development dependencies:
   ```
   uv pip install -e ".[dev]"
   ```
4. (Optional) Create a `.env` file for API keys if needed

## Project Structure

- `steam_price/` - Main package directory
  - `apps.py` - Module for fetching Steam app list
  - `exchange_rates.py` - Module for fetching currency exchange rates
  - `prices.py` - Module for fetching Steam prices
  - `dataframe.py` - Module for processing data with pandas
  - `multi_region.py` - Module for fetching prices from multiple regions
  - `logger.py` - Logging configuration
- `main.py` - Main entry point
- `analyze_prices.py` - Script to analyze price data
- `create_mock_data.py` - Script to create test data without API calls

## Usage

You can run the main script to fetch all data and generate reports:

```
python main.py
```

### Command Line Options

```bash
# Fetch prices from multiple regions
python main.py --multi-region

# Set custom API request delay to avoid rate limits
python main.py --delay 5.0

# Specify regions to fetch prices from
python main.py --multi-region --regions US JP GB EU CA

# Only fetch prices for popular games
python main.py --popular-only

# Process all Steam apps with a limit
python main.py --full --max-apps 5000

# Disable API-based filtering (not recommended)
python main.py --no-filter

# Adjust the number of apps to sample for API filtering
python main.py --api-sample 200

# Use detailed filtering to check each app (most accurate but slowest)
python main.py --filter-detailed --detailed-limit 5000

# Include free games in the results (default is paid games only)
python main.py --filter-detailed --include-free
```


### Additional Scripts

```bash
# Analyze prices with pandas
python analyze_prices.py

# Create mock data for testing
python create_mock_data.py
```

### Makefile Commands

```bash
# Run the main script
make run

# Format code with ruff
make format

# Lint code with ruff
make lint

# Auto-fix linting issues
make fix
```

The scripts will:
1. Download the complete list of Steam apps
2. Fetch current exchange rates
3. Process games in batches, fetching price information
4. Save results to the `output` directory
5. Generate visualizations and reports

## Output Files

- `output/apps.json` - Complete list of Steam apps
- `output/filtered_apps.json` - Filtered list of valid apps with price data
- `output/prices.json` - Price data for all apps
- `output/exchange_rates.json` - Current exchange rates
- `output/steam_prices_full.csv` - CSV export of all prices
- `output/steam_prices_full.xlsx` - Excel export of all prices
- `output/multi_region/multi_region_prices.json` - Multi-region price data
- `output/multi_region_prices.csv` - CSV export of multi-region data
- `output/region_price_comparison.csv` - Comparison of prices across regions
- `output/plots/` - Visualizations and charts

## Multi-Region Analysis

The multi-region functionality allows you to:

1. Fetch prices for the same games across different regions (US, JP, GB, EU, CA, etc.)
2. Compare prices between regions in their local currencies
3. Analyze which regions offer better prices for specific games
4. Generate visualizations of price differences relative to USD


Example output:

```
=== REGION PRICE ANALYSIS ===
Analyzed prices for 24 apps across 5 countries

Average prices by region (in local currency):
JP: 4779.54
CA: 44.50
US: 35.21
EU: 34.52
GB: 28.82

Price differences relative to US:
JP: +13127.58%
GB: -18.23%
EU: -2.07%
CA: +25.00%
```

## Development

This project uses:
- `pyproject.toml` for dependencies and project configuration
- `uv` for fast package installation and management
- `ruff` for linting and formatting
- Type annotations for better code quality
- `pandas` for data analysis
- `matplotlib` for visualizations

VS Code integration is provided via the `.vscode/settings.json` file, which configures automatic formatting and linting on save.

## Notes

- This project uses unofficial Steam API endpoints that may change
- The script implements rate limiting to avoid being blocked
- Fetching all prices may take several hours due to Steam's rate limits
- When fetching multi-region data, batch sizes are reduced to handle the increased API load
