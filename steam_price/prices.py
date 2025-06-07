"""Module for fetching Steam game prices."""

import json
import random
import time
from pathlib import Path
from typing import Any, Dict, List

import requests

from steam_price.logger import get_logger

# Steam API endpoint for price details
STEAM_PRICE_API = 'https://store.steampowered.com/api/appdetails'

# Request parameters
MAX_RETRIES = 5  # Maximum number of retries for failed requests
INITIAL_RETRY_DELAY = 5  # Initial delay in seconds
MAX_RETRY_DELAY = 60  # Maximum delay in seconds
JITTER = 0.5  # Jitter factor for randomizing delay

# Setup logger
logger = get_logger(__name__)


def fetch_with_retry(app_id: str, app_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Fetch data from Steam API with exponential backoff retry.
    
    Args:
        app_id: Steam app ID
        app_name: App name for logging
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
            
            logger.debug(f"Fetching price data for app {app_id} ({app_name}) from Steam API")
            
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
                    f'Rate limit (429) hit for app {app_id} ({app_name}). '
                    f'Retry {retry_count}/{MAX_RETRIES} after {delay:.1f}s'
                )
            else:
                # For other errors, use a smaller delay
                delay = min(30, INITIAL_RETRY_DELAY * retry_count) * jitter_factor
                logger.warning(
                    f'API error for app {app_id} ({app_name}): {str(e)}. '
                    f'Retry {retry_count}/{MAX_RETRIES} after {delay:.1f}s'
                )
                
            # Sleep before retrying
            time.sleep(delay)
    
    # If we've exhausted all retries, raise the last exception
    logger.error(f'Failed to fetch data for app {app_id} ({app_name}) after {MAX_RETRIES} retries')
    if last_exception:
        raise last_exception
    else:
        raise requests.RequestException(f'Failed to fetch data after {MAX_RETRIES} retries')


def fetch_prices_for_batch(
    apps: List[Dict[str, Any]], batch_index: int, exchange_rates: Dict[str, float]
) -> Dict[str, Any]:
    """Fetch price for a batch of apps.

    Args:
        apps: List of app dictionaries to process
        batch_index: Index of the current batch
        exchange_rates: Dictionary of exchange rates

    Returns:
        Dictionary of app prices
    """
    logger.info(f'Processing batch {batch_index + 1} ({len(apps)} apps)...')

    prices = {}
    success_count = 0
    error_count = 0
    batch_start_time = time.time()

    logger.debug(
        f'Exchange rates: USD={exchange_rates.get("USD")}, EUR={exchange_rates.get("EUR")}, GBP={exchange_rates.get("GBP")}'
    )

    for i, app in enumerate(apps):
        try:
            app_id = str(app['appid'])
            app_name = app['name']

            # Add a delay between ALL requests to avoid rate limiting (429 errors)
            # More conservative delay strategy with jitter
            delay_time = 3.5  # 3.5 seconds between ALL requests (increased from 2.5s)
            # Add jitter to avoid synchronized requests hitting rate limits
            jitter = random.uniform(0.8, 1.2)
            actual_delay = delay_time * jitter
            logger.debug(f'Adding rate limiting delay of {actual_delay:.2f}s')
            time.sleep(actual_delay)

            # Define country code (cc) for this request
            # We'll use country code 'JP' (Japan) as the base
            country_code = 'JP'  # Default to Japan for JPY prices

            params = {
                'appids': app_id,
                'cc': country_code,  # Country code for price region
                'filters': 'price_overview',
            }

            logger.debug(f'Fetching price for app {app_id} ({app_name})')
            # Use retry mechanism instead of direct request
            data = fetch_with_retry(app_id, app_name, params)

            app_id = str(app['appid'])
            if data and app_id in data and data[app_id]['success']:
                app_data = data[app_id]['data']

                if app_data and 'price_overview' in app_data:
                    price_info = app_data['price_overview']
                    price_in_jpy = price_info['final'] / 100  # Steam prices are in cents

                    # Convert JPY to other currencies
                    # For JPY to other currency, we need to multiply by the exchange rate
                    # exchange_rates['USD'] represents how many USD for 1 JPY
                    converted_prices = {
                        'JPY': price_in_jpy,
                        'USD': round(price_in_jpy * exchange_rates['USD'], 2),
                        'EUR': round(price_in_jpy * exchange_rates['EUR'], 2),
                        'GBP': round(price_in_jpy * exchange_rates['GBP'], 2),
                    }

                    prices[app_id] = {
                        'name': app['name'],
                        'prices': converted_prices,
                        'discount_percent': price_info['discount_percent'],
                        'initial': price_info['initial'] / 100,
                        'final': price_info['final'] / 100,
                    }

                    success_count += 1

                    # Log detailed price info at debug level
                    if price_info['discount_percent'] > 0:
                        logger.debug(
                            f'App {app_id} ({app_name}) has {price_info["discount_percent"]}% discount: '
                            f'¥{price_info["initial"] / 100} -> ¥{price_info["final"] / 100}'
                        )

                    # Log progress for every 50 apps
                    if i % 50 == 0 or i == len(apps) - 1:
                        progress_msg = (
                            f'Batch {batch_index + 1}: Processed {i + 1}/{len(apps)} apps'
                        )
                        progress_msg += f' ({success_count} with price data, {error_count} errors)'
                        logger.info(progress_msg)
                else:
                    logger.debug(f'No price data available for app {app_id} ({app_name})')
            else:
                logger.debug(f'Failed to get price data for app {app_id} ({app_name})')

        except requests.RequestException as e:
            # Network or API error
            error_count += 1
            
            # Check if this is a rate limit error (HTTP 429)
            if hasattr(e, 'response') and e.response is not None and e.response.status_code == 429:
                # Implement exponential backoff for rate limiting
                backoff_time = min(30, 5 * (2 ** (error_count % 5)))  # Max 30 seconds
                logger.warning(
                    f'Rate limit exceeded (429) for app {app["appid"]} ({app["name"]}). '
                    f'Backing off for {backoff_time} seconds...'
                )
                time.sleep(backoff_time)
            else:
                logger.warning(
                    f'API error fetching price for app {app["appid"]} ({app["name"]}): {str(e)}'
                )
                time.sleep(5)  # Increased from 2s to 5s for all other errors

        except Exception as e:
            # Other errors
            error_count += 1
            logger.error(f'Error processing app {app["appid"]} ({app["name"]}): {str(e)}')

            # Only log the full traceback occasionally to avoid flooding the logs
            if error_count % 10 == 1:
                logger.exception('Exception details:')

    batch_duration = time.time() - batch_start_time
    batch_summary = (
        f'Batch {batch_index + 1} complete in {batch_duration:.2f} seconds. '
        f'Got prices for {success_count}/{len(apps)} apps with {error_count} errors.'
    )
    logger.info(batch_summary)

    return prices


def fetch_all_prices(
    all_apps: List[Dict[str, Any]],
    exchange_rates: Dict[str, float],
    output_dir: Path,
    batch_size: int = 100,  # Reduced from 1000 to 100 to avoid rate limits
) -> Dict[str, Any]:
    """Fetch prices for all apps.

    Args:
        all_apps: List of all Steam apps
        exchange_rates: Dictionary of exchange rates
        output_dir: Directory to save the output file
        batch_size: Number of apps to process in each batch

    Returns:
        Dictionary of app prices
    """
    prices_file = output_dir / 'prices.json'
    total_start_time = time.time()

    try:
        logger.info(f'Starting to fetch prices for {len(all_apps)} apps in batches of {batch_size}')

        # Split apps into batches
        batches = []
        for i in range(0, len(all_apps), batch_size):
            batches.append(all_apps[i : i + batch_size])

        logger.info(f'Split apps into {len(batches)} batches')
        logger.debug(f'First batch contains {len(batches[0])} apps')
        logger.debug(f'First app in batch: {batches[0][0]["appid"]} - {batches[0][0]["name"]}')

        # Load existing prices if available
        all_prices = {}
        if prices_file.exists():
            logger.info(f'Found existing price data at {prices_file}')
            with open(prices_file, 'r') as f:
                all_prices = json.load(f)
            logger.info(f'Loaded {len(all_prices)} existing price entries')

            # Log some sample data from existing prices
            if all_prices:
                sample_app_id = next(iter(all_prices))
                logger.debug(
                    f'Sample existing price data for app {sample_app_id}: {all_prices[sample_app_id]}'
                )

        # Process batches one by one to avoid overwhelming the API
        for i, batch in enumerate(batches):
            logger.info(f'Starting batch {i + 1} of {len(batches)}')
            batch_prices = fetch_prices_for_batch(batch, i, exchange_rates)

            # Merge with existing prices
            prev_count = len(all_prices)
            all_prices.update(batch_prices)
            new_count = len(all_prices) - prev_count

            logger.info(f'Added {new_count} new price entries from batch {i + 1}')

            # Save after each batch to preserve progress
            with open(prices_file, 'w') as f:
                json.dump(all_prices, f, indent=2)

            logger.info(f'Saved prices after batch {i + 1}/{len(batches)}')
            logger.info(f'Current total: {len(all_prices)} apps with price data')

            # Add a longer delay between batches to avoid overwhelming the API
            if i < len(batches) - 1:
                delay_seconds = 45  # Increased from 30s to 45s for better rate limit management
                # Add jitter to avoid synchronized requests
                jitter = random.uniform(0.9, 1.1)
                actual_delay = delay_seconds * jitter
                logger.info(f'Waiting {actual_delay:.2f} seconds before next batch...')
                time.sleep(actual_delay)

        total_duration = time.time() - total_start_time
        logger.info(f'Price fetching complete in {total_duration:.2f} seconds')
        logger.info(f'Retrieved prices for {len(all_prices)} apps')

        return all_prices

    except Exception as e:
        logger.exception(f'Error in fetch_all_prices: {str(e)}')

        # Try to load existing data
        if prices_file.exists():
            logger.warning('Falling back to existing price data due to error')
            with open(prices_file, 'r') as f:
                existing_data = json.load(f)
            logger.info(f'Loaded {len(existing_data)} price entries from existing file')
            return existing_data

        logger.error('No existing price data found and price fetching failed')
        raise
