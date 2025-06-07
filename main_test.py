#!/usr/bin/env python3
"""Test script for the Steam Price Fetcher."""

import json
import sys
from pathlib import Path

from dotenv import load_dotenv

from steam_price.apps import fetch_all_steam_apps
from steam_price.exchange_rates import fetch_exchange_rates

# Load environment variables
load_dotenv()

# Configuration
OUTPUT_DIR = Path(__file__).parent / 'output'

# Ensure output directory exists
OUTPUT_DIR.mkdir(exist_ok=True)


def main():
    """Run a test of the application."""
    try:
        print('=== TEST MODE ===')
        print('This is a limited test run of the Steam Price Fetcher')

        # Test exchange rates API
        print('\nTesting exchange rates API...')
        try:
            exchange_rates = fetch_exchange_rates(OUTPUT_DIR)
            print(f'Success! Fetched exchange rates for {len(exchange_rates)} currencies')
            # Display a few sample exchange rates
            print('Sample exchange rates:')
            sample_currencies = ['USD', 'EUR', 'GBP']
            for currency in sample_currencies:
                if currency in exchange_rates:
                    print(f'  1 JPY = {exchange_rates[currency]:.6f} {currency}')
        except Exception as e:
            print(f'Error fetching exchange rates: {e}')

        # Test Steam app list API
        print('\nTesting Steam app list API...')
        try:
            # Try to load existing apps list first
            if (OUTPUT_DIR / 'apps.json').exists():
                with open(OUTPUT_DIR / 'apps.json', 'r') as f:
                    apps = json.load(f)
                    print(f'Loaded {len(apps)} apps from existing file')
                    # Show first 5 apps
                    print('First 5 apps:')
                    for app in apps[:5]:
                        print(f'  {app["appid"]}: {app["name"]}')
            else:
                # Fetch apps (this may take a while)
                print('No existing apps.json found, attempting to fetch from API...')
                print('This may take a while, but can be interrupted safely.')
                apps = fetch_all_steam_apps(OUTPUT_DIR)
        except Exception as e:
            print(f'Error with Steam app list: {e}')

        print("\nTest completed. Use 'python main.py' to run the full program.")

    except Exception as e:
        print(f'Error in test function: {str(e)}')
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
