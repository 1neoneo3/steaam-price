"""Module for processing Steam price data with pandas DataFrames."""

import json
from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import pandas as pd

from steam_price.logger import get_logger

# Setup logger
logger = get_logger(__name__)


def load_prices_to_df(output_dir: Path) -> Optional[pd.DataFrame]:
    """Load prices from JSON file and convert to pandas DataFrame.

    Args:
        output_dir: Directory where the prices.json file is located

    Returns:
        DataFrame containing price data, or None if file not found
    """
    prices_file = output_dir / 'prices.json'

    if not prices_file.exists():
        logger.error(f'Prices file not found at {prices_file}')
        return None

    try:
        logger.info(f'Loading price data from {prices_file}')

        # Load prices from JSON file
        with open(prices_file, 'r') as f:
            prices = json.load(f)

        # Check if we have any price data
        if not prices:
            logger.warning('No price data found (empty JSON)')
            return None

        logger.info(f'Loaded price data for {len(prices)} games')

        # Convert nested dictionary to DataFrame
        logger.debug('Converting price data to DataFrame')
        data = []
        invalid_entries = 0

        for app_id, app_info in prices.items():
            # Ensure all required keys are present
            if not all(
                key in app_info
                for key in ['name', 'discount_percent', 'initial', 'final', 'prices']
            ):
                logger.debug(f'Skipping app {app_id} due to missing required keys')
                invalid_entries += 1
                continue

            # Ensure prices dictionary has required currencies
            if not all(currency in app_info['prices'] for currency in ['USD', 'EUR', 'GBP']):
                logger.debug(f'Skipping app {app_id} due to missing currency data')
                invalid_entries += 1
                continue

            row = {
                'app_id': app_id,
                'name': app_info['name'],
                'discount_percent': app_info['discount_percent'],
                'initial_price_jpy': app_info['initial'],
                'final_price_jpy': app_info['final'],
                'price_usd': app_info['prices']['USD'],
                'price_eur': app_info['prices']['EUR'],
                'price_gbp': app_info['prices']['GBP'],
            }
            data.append(row)

        if invalid_entries > 0:
            logger.warning(f'Skipped {invalid_entries} entries due to missing or invalid data')

        # Check if we have any valid data rows
        if not data:
            logger.error('No valid price data found after filtering')
            return None

        # Create DataFrame
        df = pd.DataFrame(data)
        logger.info(f'Created DataFrame with {len(df)} rows and {len(df.columns)} columns')

        # Convert numeric columns
        logger.debug('Converting columns to numeric types')
        numeric_cols = [
            'discount_percent',
            'initial_price_jpy',
            'final_price_jpy',
            'price_usd',
            'price_eur',
            'price_gbp',
        ]

        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col])

        # Add calculated columns
        logger.debug('Adding calculated columns')
        df['is_free'] = df['final_price_jpy'] == 0
        df['is_discounted'] = df['discount_percent'] > 0
        df['savings_jpy'] = df['initial_price_jpy'] - df['final_price_jpy']

        # Log data summary
        logger.info(f'DataFrame created successfully with shape: {df.shape}')
        logger.debug(f'DataFrame columns: {list(df.columns)}')
        logger.debug(f'DataFrame data types: {df.dtypes}')

        return df

    except Exception as e:
        logger.exception(f'Error loading prices to DataFrame: {str(e)}')
        return None


def save_dataframe(df: pd.DataFrame, output_dir: Path, filename: str) -> None:
    """Save DataFrame to CSV and Excel files.

    Args:
        df: DataFrame to save
        output_dir: Directory to save the files
        filename: Base filename without extension
    """
    logger.info(f'Saving DataFrame with {len(df)} rows to files')

    try:
        csv_path = output_dir / f'{filename}.csv'
        excel_path = output_dir / f'{filename}.xlsx'

        # Save as CSV
        logger.debug(f'Saving DataFrame to CSV file at {csv_path}')
        df.to_csv(csv_path, index=False)
        logger.info(f'Saved DataFrame to {csv_path}')
        print(f'Saved DataFrame to {csv_path}')

        # Save as Excel
        logger.debug(f'Saving DataFrame to Excel file at {excel_path}')
        df.to_excel(excel_path, index=False)
        logger.info(f'Saved DataFrame to {excel_path}')
        print(f'Saved DataFrame to {excel_path}')

        # Log file sizes
        csv_size = csv_path.stat().st_size / 1024  # KB
        excel_size = excel_path.stat().st_size / 1024  # KB
        logger.debug(f'CSV file size: {csv_size:.2f} KB')
        logger.debug(f'Excel file size: {excel_size:.2f} KB')

    except Exception as e:
        logger.exception(f'Error saving DataFrame: {str(e)}')
        print(f'Error saving DataFrame: {str(e)}')


def load_multi_region_prices_to_df(output_dir: Path) -> Optional[pd.DataFrame]:
    """Load multi-region prices from JSON file and convert to pandas DataFrame.

    Args:
        output_dir: Directory where the multi_region_prices.json file is located

    Returns:
        DataFrame containing multi-region price data, or None if file not found
    """
    multi_region_dir = output_dir / 'multi_region'
    prices_file = multi_region_dir / 'multi_region_prices.json'

    if not prices_file.exists():
        logger.error(f'Multi-region prices file not found at {prices_file}')
        return None

    try:
        logger.info(f'Loading multi-region price data from {prices_file}')

        # Load prices from JSON file
        with open(prices_file, 'r') as f:
            prices = json.load(f)

        # Check if we have any price data
        if not prices:
            logger.warning('No multi-region price data found (empty JSON)')
            return None

        logger.info(f'Loaded multi-region price data for {len(prices)} games')

        # Convert nested dictionary to DataFrame
        logger.debug('Converting multi-region price data to DataFrame')

        # Create a list to hold all region-specific price rows
        all_rows = []

        # Process each app's region data
        for app_id, app_info in prices.items():
            app_name = app_info['name']

            # Skip if no price data in any region
            if not app_info['has_price']:
                continue

            # Process each region
            for country_code, region_data in app_info['regions'].items():
                # Find currency code and symbol for this country
                currency_code = region_data['currency']
                currency_symbol = region_data['symbol']

                # Create a row with app and region data
                row = {
                    'app_id': app_id,
                    'name': app_name,
                    'country': country_code,
                    'currency': currency_code,
                    'currency_symbol': currency_symbol,
                    'initial_price': region_data['initial'],
                    'final_price': region_data['final'],
                    'discount_percent': region_data['discount_percent'],
                    'formatted_price': region_data['formatted'],
                    'savings': region_data['savings'],
                }

                all_rows.append(row)

        # Check if we have any valid data rows
        if not all_rows:
            logger.error('No valid multi-region price data found after processing')
            return None

        # Create DataFrame
        df = pd.DataFrame(all_rows)
        logger.info(
            f'Created multi-region DataFrame with {len(df)} rows and {len(df.columns)} columns'
        )

        # Add calculated columns
        df['is_free'] = df['final_price'] == 0
        df['is_discounted'] = df['discount_percent'] > 0

        # Log data summary
        logger.info(f'Multi-region DataFrame created with {len(df)} rows')
        logger.debug(f'Country distribution: {df["country"].value_counts().to_dict()}')

        return df

    except Exception as e:
        logger.exception(f'Error loading multi-region prices to DataFrame: {str(e)}')
        return None


def analyze_region_price_differences(df: pd.DataFrame, output_dir: Path) -> None:
    """Analyze price differences between regions.

    Args:
        df: DataFrame containing multi-region price data
        output_dir: Directory to save visualizations
    """
    try:
        logger.info('Analyzing price differences between regions')

        # Create plots directory if it doesn't exist
        plots_dir = output_dir / 'plots'
        plots_dir.mkdir(exist_ok=True)

        # Get unique apps and countries
        apps = df['app_id'].unique()
        countries = df['country'].unique()

        logger.info(f'Analyzing {len(apps)} apps across {len(countries)} countries')

        # Create a price comparison table (pivot)
        pivot_df = df.pivot_table(
            index=['app_id', 'name'], columns='country', values='final_price', aggfunc='first'
        ).reset_index()

        # Calculate price differences
        # Use US as the base for comparison
        if 'US' in pivot_df.columns:
            logger.info('Calculating price differences relative to US prices')

            # Calculate USD equivalent prices for comparison
            for country in countries:
                if country != 'US' and country in pivot_df.columns:
                    # Calculate price difference percentage
                    diff_col = f'{country}_vs_US_diff_pct'
                    pivot_df[diff_col] = ((pivot_df[country] / pivot_df['US']) - 1) * 100

        # Save the price comparison table
        comparison_file = output_dir / 'region_price_comparison.csv'
        pivot_df.to_csv(comparison_file, index=False)
        logger.info(f'Saved region price comparison to {comparison_file}')

        # Generate visualizations

        # 1. Box plot of price differences by region
        diff_cols = [col for col in pivot_df.columns if col.endswith('_diff_pct')]
        if diff_cols:
            diff_data = pivot_df[diff_cols].melt(var_name='Region', value_name='Price Difference %')
            diff_data['Region'] = diff_data['Region'].str.replace('_vs_US_diff_pct', '')

            plt.figure(figsize=(12, 6))
            plt.boxplot(
                [
                    diff_data[diff_data['Region'] == region]['Price Difference %'].dropna()
                    for region in diff_data['Region'].unique()
                ],
                labels=diff_data['Region'].unique(),
            )
            plt.title('Price Differences Relative to US Prices')
            plt.ylabel('Price Difference %')
            plt.axhline(y=0, color='r', linestyle='-', alpha=0.3)
            plt.grid(axis='y', alpha=0.3)
            plt.savefig(plots_dir / 'region_price_differences.png')
            logger.info(
                f'Saved region price difference plot to {plots_dir / "region_price_differences.png"}'
            )

        # 2. Heatmap of average prices by region
        region_avg_prices = df.groupby('country')['final_price'].mean().reset_index()
        region_avg_prices = region_avg_prices.sort_values('final_price', ascending=False)

        plt.figure(figsize=(10, 6))
        plt.bar(region_avg_prices['country'], region_avg_prices['final_price'])
        plt.title('Average Game Prices by Region')
        plt.xlabel('Region')
        plt.ylabel('Average Price (Local Currency)')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(plots_dir / 'region_avg_prices.png')
        logger.info(f'Saved region average prices plot to {plots_dir / "region_avg_prices.png"}')

        # Print summary
        print('\n=== REGION PRICE ANALYSIS ===')
        print(f'Analyzed prices for {len(apps)} apps across {len(countries)} countries')
        print('\nAverage prices by region (in local currency):')
        for _, row in region_avg_prices.iterrows():
            print(f'{row["country"]}: {row["final_price"]:.2f}')

        if 'US' in pivot_df.columns:
            print('\nPrice differences relative to US:')
            for diff_col in diff_cols:
                region = diff_col.replace('_vs_US_diff_pct', '')
                avg_diff = pivot_df[diff_col].mean()
                print(f'{region}: {avg_diff:+.2f}%')

        print(f'\nDetailed comparison saved to {comparison_file}')

    except Exception as e:
        logger.exception(f'Error analyzing region price differences: {str(e)}')
        print(f'Error analyzing region price differences: {str(e)}')


def analyze_prices(df: pd.DataFrame, output_dir: Path) -> None:
    """Perform analysis on price data and generate visualizations.

    Args:
        df: DataFrame containing price data
        output_dir: Directory to save visualizations
    """
    try:
        print('\n=== PRICE ANALYSIS ===')

        # Basic statistics
        print('\nBasic statistics (USD prices):')
        price_stats = df[df['price_usd'] > 0]['price_usd'].describe()
        print(price_stats)

        # Price distribution
        print('\nPrice distribution:')
        # Create custom categories for better analysis
        df['price_category'] = 'Unknown'

        # Define price categories
        df.loc[df['price_usd'] == 0, 'price_category'] = 'Free'
        df.loc[(df['price_usd'] > 0) & (df['price_usd'] < 5), 'price_category'] = 'Under $5'
        df.loc[(df['price_usd'] >= 5) & (df['price_usd'] < 10), 'price_category'] = '$5-$10'
        df.loc[(df['price_usd'] >= 10) & (df['price_usd'] < 20), 'price_category'] = '$10-$20'
        df.loc[(df['price_usd'] >= 20) & (df['price_usd'] < 30), 'price_category'] = '$20-$30'
        df.loc[(df['price_usd'] >= 30) & (df['price_usd'] < 60), 'price_category'] = '$30-$60'
        df.loc[df['price_usd'] >= 60, 'price_category'] = 'Over $60'

        price_distribution = df['price_category'].value_counts().sort_index()
        print(price_distribution)

        # Discount statistics
        discounted_df = df[df['is_discounted']]
        if not discounted_df.empty:
            print('\nDiscount statistics:')
            discount_stats = discounted_df['discount_percent'].describe()
            print(discount_stats)

            print('\nTop 10 discounts:')
            top_discounts = discounted_df.sort_values('discount_percent', ascending=False).head(10)
            print(
                top_discounts[['name', 'discount_percent', 'initial_price_jpy', 'final_price_jpy']]
            )

        # Create visualizations
        plots_dir = output_dir / 'plots'
        plots_dir.mkdir(exist_ok=True)

        # Price distribution plot
        plt.figure(figsize=(12, 6))
        price_distribution.plot(kind='bar', color='skyblue')
        plt.title('Price Distribution of Steam Games')
        plt.xlabel('Price Range (USD)')
        plt.ylabel('Number of Games')
        plt.tight_layout()
        plt.savefig(plots_dir / 'price_distribution.png')
        print(f'\nSaved price distribution plot to {plots_dir / "price_distribution.png"}')

        # Discount distribution plot
        if not discounted_df.empty:
            plt.figure(figsize=(12, 6))
            plt.hist(discounted_df['discount_percent'], bins=20, color='green', alpha=0.7)
            plt.title('Discount Distribution')
            plt.xlabel('Discount Percentage')
            plt.ylabel('Number of Games')
            plt.grid(axis='y', alpha=0.3)
            plt.tight_layout()
            plt.savefig(plots_dir / 'discount_distribution.png')
            print(f'Saved discount distribution plot to {plots_dir / "discount_distribution.png"}')

        print('\nAnalysis complete!')

    except Exception as e:
        print(f'Error during analysis: {str(e)}')


def fetch_sample_data(df: pd.DataFrame, output_dir: Path, sample_size: int = 100) -> pd.DataFrame:
    """Fetch a sample of the data for quick testing.

    Args:
        df: Full DataFrame
        output_dir: Directory to save the sample data
        sample_size: Number of records to sample

    Returns:
        Sample DataFrame
    """
    try:
        # Get a representative sample
        # Include some free, some discounted, and some regular priced games
        free_games = df[df['is_free']].sample(min(sample_size // 3, len(df[df['is_free']])))
        discounted = df[df['is_discounted'] & ~df['is_free']]
        discounted_games = discounted.sample(min(sample_size // 3, len(discounted)))
        regular_games = df[~df['is_free'] & ~df['is_discounted']]
        regular_games = regular_games.sample(min(sample_size // 3, len(regular_games)))

        # Combine samples
        sample_df = pd.concat([free_games, discounted_games, regular_games])

        # Shuffle the sample
        sample_df = sample_df.sample(frac=1).reset_index(drop=True)

        # Limit to requested sample size
        if len(sample_df) > sample_size:
            sample_df = sample_df.head(sample_size)

        # Save the sample
        sample_df.to_csv(output_dir / 'sample_games.csv', index=False)
        print(f'Saved sample of {len(sample_df)} games to {output_dir / "sample_games.csv"}')

        return sample_df

    except Exception as e:
        print(f'Error creating sample data: {str(e)}')
        return df.sample(min(sample_size, len(df)))
