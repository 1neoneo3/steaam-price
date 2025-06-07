"""Module for fetching exchange rates."""

import json
from pathlib import Path

import requests

from steam_price.logger import get_logger

# Exchange rate API endpoint
EXCHANGE_RATE_API = 'https://api.exchangerate-api.com/v4/latest/JPY'

# Setup logger
logger = get_logger(__name__)


def fetch_exchange_rates(output_dir: Path) -> dict:
    """Fetch current exchange rates and save them to a file.

    Args:
        output_dir: Directory to save the output file

    Returns:
        Dictionary of exchange rates
    """
    
    exchange_rates_file = output_dir / 'exchange_rates.json'

    try:
        logger.info('Fetching exchange rates...')
        logger.debug(f'API endpoint: {EXCHANGE_RATE_API}')

        response = requests.get(EXCHANGE_RATE_API, timeout=10)
        response.raise_for_status()

        logger.debug(f'Response status code: {response.status_code}')
        data = response.json()

        if data and 'rates' in data:
            rates = data['rates']
            logger.info('Exchange rates retrieved successfully')
            logger.debug(f'Base currency: {data.get("base", "unknown")}')
            logger.debug(
                f'Sample rates: USD={rates.get("USD", "N/A")}, EUR={rates.get("EUR", "N/A")}, GBP={rates.get("GBP", "N/A")}'
            )

            # Save exchange rates to file (for backward compatibility)
            with open(exchange_rates_file, 'w') as f:
                json.dump(rates, f, indent=2)

            logger.info(f'Exchange rates saved to {exchange_rates_file}')
            return rates
        else:
            logger.error('Invalid response format from Exchange Rate API')
            logger.debug(f'Response data: {data}')
            raise ValueError('Invalid response format from Exchange Rate API')

    except requests.RequestException as e:
        logger.error(f'HTTP error fetching exchange rates: {str(e)}')

        # If we have a local cache, use that instead
        if exchange_rates_file.exists():
            logger.warning('Using cached exchange rates from file due to API error')
            with open(exchange_rates_file, 'r') as f:
                cached_rates = json.load(f)
            logger.info(f'Loaded {len(cached_rates)} currencies from cache file')
            return cached_rates

        logger.exception('No cached exchange rates available')
        raise

    except Exception as e:
        logger.exception(f'Unexpected error fetching exchange rates: {str(e)}')

        # If we have a local cache, use that instead
        if exchange_rates_file.exists():
            logger.warning('Using cached exchange rates from file due to error')
            with open(exchange_rates_file, 'r') as f:
                cached_rates = json.load(f)
            logger.info(f'Loaded {len(cached_rates)} currencies from cache file')
            return cached_rates

        logger.error('No cached exchange rates available and API request failed')
        raise
