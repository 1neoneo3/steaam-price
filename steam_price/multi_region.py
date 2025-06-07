"""Module for fetching Steam game prices from multiple regions."""

import json
import random
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from steam_price.logger import get_logger

# Setup logger
logger = get_logger(__name__)

# Steam API endpoint for price details
STEAM_PRICE_API = 'https://store.steampowered.com/api/appdetails'

# Request parameters
MAX_RETRIES = 5  # Maximum number of retries for failed requests
INITIAL_RETRY_DELAY = 5  # Initial delay in seconds
MAX_RETRY_DELAY = 60  # Maximum delay in seconds
JITTER = 0.5  # Jitter factor for randomizing delay


def fetch_with_retry(app_id: str, country: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Fetch data from Steam API with exponential backoff retry.

    Args:
        app_id: Steam app ID
        country: Country code
        params: Request parameters

    Returns:
        JSON response data

    Raises:
        requests.RequestException: If all retries fail
    """
    
    retry_count = 0
    last_exception = None

    while retry_count < MAX_RETRIES:
        try:
            # Add jitter to avoid synchronized requests
            jitter_factor = 1 + random.uniform(-JITTER, JITTER)

            logger.debug(f"Fetching price data for app {app_id} in region {country}")
            
            # Make the request with a timeout
            response = requests.get(STEAM_PRICE_API, params=params, timeout=10)
            response.raise_for_status()
            return response.json()

        except requests.RequestException as e:
            last_exception = e
            retry_count += 1

            # Check if we've hit the rate limit
            if hasattr(e, 'response') and e.response is not None and e.response.status_code == 429:
                # Calculate exponential backoff with jitter
                delay = min(MAX_RETRY_DELAY, INITIAL_RETRY_DELAY * (2 ** (retry_count - 1)))
                delay = delay * jitter_factor

                logger.warning(
                    f'Rate limit (429) hit for app {app_id} in region {country}. '
                    f'Retry {retry_count}/{MAX_RETRIES} after {delay:.1f}s'
                )
            else:
                # For other errors, use a smaller delay
                delay = min(30, INITIAL_RETRY_DELAY * retry_count) * jitter_factor
                logger.warning(
                    f'API error for app {app_id} in region {country}: {str(e)}. '
                    f'Retry {retry_count}/{MAX_RETRIES} after {delay:.1f}s'
                )

            # Sleep before retrying
            time.sleep(delay)

    # If we've exhausted all retries, raise the last exception
    logger.error(
        f'Failed to fetch data for app {app_id} in region {country} after {MAX_RETRIES} retries'
    )
    if last_exception:
        raise last_exception
    else:
        raise requests.RequestException(f'Failed to fetch data after {MAX_RETRIES} retries')


# List of common currency regions (country code, currency code, currency symbol)
REGIONS = [
    ('US', 'USD', '$'),  # United States (USD)
    ('JP', 'JPY', '¥'),  # Japan (JPY)
    ('GB', 'GBP', '£'),  # United Kingdom (GBP)
    ('EU', 'EUR', '€'),  # Euro zone (EUR)
    ('CA', 'CAD', 'C$'),  # Canada (CAD)
    ('AU', 'AUD', 'A$'),  # Australia (AUD)
    ('RU', 'RUB', '₽'),  # Russia (RUB)
    ('BR', 'BRL', 'R$'),  # Brazil (BRL)
    ('KR', 'KRW', '₩'),  # South Korea (KRW)
    ('CN', 'CNY', '¥'),  # China (CNY)
    ('IN', 'INR', '₹'),  # India (INR)
    ('TR', 'TRY', '₺'),  # Turkey (TRY)
    ('MX', 'MXN', 'Mex$'),  # Mexico (MXN)
]


def fetch_multi_region_prices(
    apps: List[Dict[str, Any]],
    batch_index: int,
    regions: List = REGIONS,
    output_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Fetch prices for a batch of apps from multiple regions.

    Args:
        apps: List of app dictionaries to process
        batch_index: Index of the current batch
        regions: List of regions to fetch prices from (default is all regions)
        output_dir: Directory to save individual region data files (if provided)

    Returns:
        Dictionary of app prices with region data
    """
    logger.info(
        f'Processing batch {batch_index + 1} for {len(apps)} apps across {len(regions)} regions'
    )

    prices = {}
    success_count = 0
    error_count = 0
    batch_start_time = time.time()

    # Process each app
    for i, app in enumerate(apps):
        app_id = str(app['appid'])
        app_name = app['name']

        logger.debug(f'Processing app {app_id} ({app_name})')

        # Initialize price data for this app
        price_data = {
            'name': app_name,
            'regions': {},
            'has_price': False,  # Flag to track if any region has price data
        }

        # Process each region
        for country, currency, symbol in regions:
            try:
                # Add a delay between requests to avoid rate limiting (429 errors)
                # More conservative delay to avoid rate limits
                delay_time = 3.0  # Increased from 1.0s to 3.0s to reduce rate limit errors
                # Add jitter to avoid synchronized requests
                jitter = random.uniform(0.5, 1.5)
                actual_delay = delay_time * jitter
                logger.debug(f'Adding rate limiting delay of {actual_delay:.2f}s')
                time.sleep(actual_delay)

                # Prepare request parameters
                params = {
                    'appids': app_id,
                    'cc': country,  # Country code
                    'filters': 'price_overview',
                }

                # Make the request with retry logic
                logger.debug(f'Fetching price for app {app_id} in region {country} ({currency})')
                data = fetch_with_retry(app_id, country, params)

                # Process the response
                if data and app_id in data and data[app_id]['success']:
                    app_data = data[app_id]['data']

                    if app_data and 'price_overview' in app_data:
                        price_info = app_data['price_overview']

                        # Store region-specific price data
                        region_data = {
                            'currency': currency,
                            'symbol': symbol,
                            'initial': price_info['initial'] / 100,  # Convert from cents
                            'final': price_info['final'] / 100,  # Convert from cents
                            'discount_percent': price_info['discount_percent'],
                            'formatted': price_info['final_formatted'],
                        }

                        # Calculate savings
                        if price_info['discount_percent'] > 0:
                            region_data['savings'] = region_data['initial'] - region_data['final']
                        else:
                            region_data['savings'] = 0

                        price_data['regions'][country] = region_data
                        price_data['has_price'] = True

                        logger.debug(
                            f'Got price for {app_name} in {country}: {region_data["formatted"]}'
                        )

                        if price_info['discount_percent'] > 0:
                            logger.debug(
                                f'App {app_id} has {price_info["discount_percent"]}% discount in {country}'
                            )
                    else:
                        logger.debug(f'No price data for app {app_id} in region {country}')
                else:
                    logger.debug(f'Failed to get price data for app {app_id} in region {country}')

            except requests.RequestException as e:
                error_count += 1
                # Check if this is a rate limit error (HTTP 429)
                if (
                    hasattr(e, 'response')
                    and e.response is not None
                    and e.response.status_code == 429
                ):
                    # Implement exponential backoff for rate limiting
                    backoff_time = min(30, 5 * (2 ** (error_count % 5)))  # Max 30 seconds
                    logger.warning(
                        f'Rate limit exceeded (429) for app {app_id} in region {country}. '
                        f'Backing off for {backoff_time} seconds...'
                    )
                    time.sleep(backoff_time)
                else:
                    logger.warning(
                        f'API error fetching price for app {app_id} in region {country}: {str(e)}'
                    )
                    time.sleep(5)  # Increased from 2s to 5s for all other errors

            except Exception as e:
                error_count += 1
                logger.error(f'Error processing app {app_id} in region {country}: {str(e)}')

        # Only store apps that have price data in at least one region
        if price_data['has_price']:
            prices[app_id] = price_data
            success_count += 1

            # Log progress
            if i % 5 == 0 or i == len(apps) - 1:
                progress_msg = f'Batch {batch_index + 1}: Processed {i + 1}/{len(apps)} apps'
                progress_msg += f' ({success_count} with price data, {error_count} errors)'
                logger.info(progress_msg)

    # Batch summary
    batch_duration = time.time() - batch_start_time
    batch_summary = (
        f'Batch {batch_index + 1} complete in {batch_duration:.2f} seconds. '
        f'Got prices for {success_count}/{len(apps)} apps with {error_count} errors.'
    )
    logger.info(batch_summary)

    # Save region data if output directory is provided
    if output_dir:
        multi_region_file = output_dir / f'multi_region_prices_batch_{batch_index + 1}.json'
        with open(multi_region_file, 'w') as f:
            json.dump(prices, f, indent=2)
        logger.info(f'Saved multi-region price data to {multi_region_file}')

    return prices


def fetch_all_multi_region_prices(
    all_apps: List[Dict[str, Any]],
    output_dir: Path,
    batch_size: int = 3,  # Even smaller batch size (reduced from 10 to 3) to avoid rate limits
    regions: List = None,  # Use default regions if None
) -> Dict[str, Any]:
    """Fetch prices for all apps from multiple regions.

    Args:
        all_apps: List of all Steam apps
        output_dir: Directory to save the output files
        batch_size: Number of apps to process in each batch
        regions: List of regions to fetch prices from (default is all regions)

    Returns:
        Dictionary of app prices with region data
    """
    multi_region_dir = output_dir / 'multi_region'
    multi_region_dir.mkdir(exist_ok=True)

    prices_file = multi_region_dir / 'multi_region_prices.json'
    total_start_time = time.time()

    # Use specified regions or default to all regions
    selected_regions = regions if regions else REGIONS
    logger.info(
        f'Will fetch prices for {len(selected_regions)} regions: {[r[0] for r in selected_regions]}'
    )

    try:
        logger.info(
            f'Starting to fetch multi-region prices for {len(all_apps)} apps in batches of {batch_size}'
        )

        # Split apps into batches
        batches = []
        for i in range(0, len(all_apps), batch_size):
            batches.append(all_apps[i : i + batch_size])

        logger.info(f'Split apps into {len(batches)} batches')

        # Load existing prices if available
        all_prices = {}
        if prices_file.exists():
            logger.info(f'Found existing multi-region price data at {prices_file}')
            with open(prices_file, 'r') as f:
                all_prices = json.load(f)
            logger.info(f'Loaded {len(all_prices)} existing multi-region price entries')

        # Process batches one by one
        for i, batch in enumerate(batches):
            logger.info(f'Starting multi-region batch {i + 1} of {len(batches)}')
            batch_prices = fetch_multi_region_prices(batch, i, selected_regions, multi_region_dir)

            # Merge with existing prices
            prev_count = len(all_prices)
            all_prices.update(batch_prices)
            new_count = len(all_prices) - prev_count

            logger.info(f'Added {new_count} new multi-region price entries from batch {i + 1}')

            # Save after each batch to preserve progress
            with open(prices_file, 'w') as f:
                json.dump(all_prices, f, indent=2)
                
            # Calculate estimated time to completion
            elapsed_time = time.time() - total_start_time
            batches_completed = i + 1
            batches_remaining = len(batches) - batches_completed
            
            if batches_completed > 0:
                avg_time_per_batch = elapsed_time / batches_completed
                estimated_remaining_time = avg_time_per_batch * batches_remaining
                estimated_total_time = elapsed_time + estimated_remaining_time
                
                # Format times as minutes and seconds
                elapsed_min, elapsed_sec = divmod(int(elapsed_time), 60)
                remaining_min, remaining_sec = divmod(int(estimated_remaining_time), 60)
                total_min, total_sec = divmod(int(estimated_total_time), 60)
                
                progress_msg = f'Progress: {batches_completed}/{len(batches)} batches completed'
                progress_msg += f' ({elapsed_min}m {elapsed_sec}s elapsed, ~{remaining_min}m {remaining_sec}s remaining)'
                progress_msg += f' - Estimated completion in ~{total_min}m {total_sec}s total'
                
                logger.info(progress_msg)

            logger.info(f'Saved multi-region prices after batch {i + 1}/{len(batches)}')

            # Add a longer delay between batches to avoid overwhelming the API
            if i < len(batches) - 1:
                delay_seconds = 30  # Increased from 10s to 30s to avoid rate limiting
                # Add jitter to avoid synchronized requests
                jitter = random.uniform(0.9, 1.1)
                actual_delay = delay_seconds * jitter
                logger.info(f'Waiting {actual_delay:.2f} seconds before next batch...')
                time.sleep(actual_delay)

        total_duration = time.time() - total_start_time
        logger.info(f'Multi-region price fetching complete in {total_duration:.2f} seconds')
        logger.info(f'Retrieved multi-region prices for {len(all_prices)} apps')

        return all_prices

    except Exception as e:
        logger.exception(f'Error in fetch_all_multi_region_prices: {str(e)}')

        # Try to load existing data
        if prices_file.exists():
            logger.warning('Falling back to existing multi-region price data due to error')
            with open(prices_file, 'r') as f:
                existing_data = json.load(f)
            logger.info(
                f'Loaded {len(existing_data)} multi-region price entries from existing file'
            )
            return existing_data

        logger.error('No existing multi-region price data found and price fetching failed')
        raise
