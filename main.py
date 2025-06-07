#!/usr/bin/env python3
"""Main script for the Steam Price Fetcher."""

import argparse
import json
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

from steam_price.apps import (
    fetch_all_steam_apps,
    filter_apps_by_api_details,
    filter_apps_with_details,
)
from steam_price.dataframe import (
    analyze_region_price_differences,
    load_multi_region_prices_to_df,
    save_dataframe,
)
from steam_price.exchange_rates import fetch_exchange_rates
from steam_price.logger import get_logger
from steam_price.multi_region import REGIONS, fetch_all_multi_region_prices

# Load environment variables
load_dotenv()

# Configuration
BATCH_SIZE = 50  # Reduced batch size to avoid rate limits
MULTI_REGION_BATCH_SIZE = 25  # Smaller batch size for multi-region processing
PROJECT_DIR = Path(__file__).parent
OUTPUT_DIR = PROJECT_DIR / 'output'
LOG_DIR = PROJECT_DIR / 'logs'

# Ensure directories exist
OUTPUT_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)
MULTI_REGION_DIR = OUTPUT_DIR / 'multi_region'
MULTI_REGION_DIR.mkdir(exist_ok=True)

# Setup logger
logger = get_logger(__name__, LOG_DIR)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Steam Price Fetcher')
    # Multi-region flag removed as it's the default behavior now
    # Removed sample option
    parser.add_argument('--batch-size', type=int, help='Batch size for processing apps')
    parser.add_argument(
        '--delay',
        type=float,
        help='Delay in seconds between API requests (default varies by operation)',
    )
    parser.add_argument(
        '--regions',
        nargs='+',
        choices=[r[0] for r in REGIONS],
        help='Regions to fetch prices from (e.g. US JP GB EU CA)',
    )
    parser.add_argument(
        '--popular-only', action='store_true', help='Only fetch prices for popular games (top 100)'
    )
    parser.add_argument('--limit', type=int, help='Limit the number of apps to process')
    parser.add_argument(
        '--full', action='store_true', help='Process all Steam apps (warning: takes a long time)'
    )
    parser.add_argument(
        '--max-apps',
        type=int,
        help='Maximum number of apps to process',
    )
    parser.add_argument(
        '--no-filter',
        action='store_true',
        help='Disable API-based filtering of apps (not recommended)',
    )
    parser.add_argument(
        '--filter-detailed',
        action='store_true',
        help='Filter apps by checking details for each app (most accurate but slowest)',
    )
    parser.add_argument(
        '--api-sample',
        type=int,
        default=1000,
        help='Number of apps to sample for API filtering (default: 1000)',
    )
    parser.add_argument(
        '--detailed-limit',
        type=int,
        default=2000,
        help='Maximum number of apps to check in detailed filtering (default: 2000)',
    )
    parser.add_argument(
        '--min-appid', type=int, help='Minimum app ID to include (useful for filtering)'
    )
    parser.add_argument(
        '--max-appid', type=int, help='Maximum app ID to include (useful for filtering)'
    )
    parser.add_argument(
        '--include-free',
        action='store_true',
        help='Include free apps in the results (default: only paid apps)',
    )

    # Cache options removed

    return parser.parse_args()


# Single region price fetching removed - using only multi-region functionality


def fetch_multiple_regions(all_apps, selected_regions=None):
    """Fetch prices from multiple regions."""
    logger.info('Starting multi-region price fetching process...')

    # If regions are specified, convert them to region tuples
    if selected_regions:
        # Find the matching region tuples
        regions_to_use = []
        for region_code in selected_regions:
            for region in REGIONS:
                if region[0] == region_code:
                    regions_to_use.append(region)
                    break

        if not regions_to_use:
            logger.warning('No valid regions specified, using default regions')
            # Use minimal regions if none specified
            regions_to_use = [
                ('US', 'USD', '$'),  # United States
                ('JP', 'JPY', '¥'),  # Japan
            ]
    else:
        # Use minimal regions if none specified
        regions_to_use = [
            ('US', 'USD', '$'),  # United States
            ('JP', 'JPY', '¥'),  # Japan
        ]

    logger.info(
        f'Will fetch prices for {len(regions_to_use)} regions: {[r[0] for r in regions_to_use]}'
    )

    # Fetch multi-region prices
    prices = fetch_all_multi_region_prices(
        all_apps, OUTPUT_DIR, MULTI_REGION_BATCH_SIZE, regions_to_use
    )
    logger.info(f'Retrieved multi-region prices for {len(prices)} apps')

    # Load into DataFrame for analysis
    logger.info('Loading multi-region data into DataFrame...')
    df = load_multi_region_prices_to_df(OUTPUT_DIR)

    if df is not None:
        # Save to CSV/Excel
        logger.info('Saving multi-region data to CSV/Excel...')
        save_dataframe(df, OUTPUT_DIR, 'multi_region_prices')

        # Analyze region differences
        logger.info('Analyzing price differences between regions...')
        analyze_region_price_differences(df, OUTPUT_DIR)

    return prices


def main():
    """Run the main application."""
    start_time = time.time()
    logger.info('Starting Steam Price Fetcher')
    logger.info(f'Output directory: {OUTPUT_DIR}')

    # Parse command line arguments
    args = parse_args()
    popular_only = args.popular_only
    limit_count = args.limit
    process_all = args.full
    max_apps = args.max_apps
    no_filter = args.no_filter
    filter_api = not args.no_filter
    filter_detailed = args.filter_detailed
    api_sample_size = args.api_sample
    detailed_limit = args.detailed_limit
    min_appid = args.min_appid
    max_appid = args.max_appid
    include_free = args.include_free
    custom_delay = args.delay

    # Cache options removed

    # Set batch size from args if provided, otherwise use multi-region batch size
    batch_size = args.batch_size if args.batch_size else MULTI_REGION_BATCH_SIZE

    logger.info(f'Batch size: {batch_size}')

    # Set custom delay if provided
    if custom_delay is not None:
        import steam_price.apps
        import steam_price.multi_region
        import steam_price.prices

        # Update delay values in relevant modules
        steam_price.apps.API_DELAY = custom_delay
        logger.info(f'Using custom API delay: {custom_delay}s')

    # Cache configuration removed

    try:
        # Fetch all apps
        logger.info('Fetching Steam apps list...')
        all_apps = fetch_all_steam_apps(OUTPUT_DIR)
        logger.info(f'Retrieved {len(all_apps)} apps')

        # Apply pre-filtering by app ID range if requested
        if min_appid is not None or max_appid is not None:
            initial_count = len(all_apps)

            if min_appid is not None:
                logger.info(f'Filtering apps with ID >= {min_appid}')
                all_apps = [app for app in all_apps if int(app['appid']) >= min_appid]

            if max_appid is not None:
                logger.info(f'Filtering apps with ID <= {max_appid}')
                all_apps = [app for app in all_apps if int(app['appid']) <= max_appid]

            logger.info(
                f'After ID filtering: {len(all_apps)} apps (removed {initial_count - len(all_apps)} apps)'
            )

        # Apply detailed filtering (most accurate but slowest)
        if filter_detailed:
            logger.info(
                f'Applying detailed filtering to find valid apps (checking up to {detailed_limit} apps)'
            )
            filtered_apps_file = OUTPUT_DIR / 'filtered_apps.json'
            
            # Check if we already have filtered apps saved
            if filtered_apps_file.exists():
                logger.info(f'Found existing filtered apps file at {filtered_apps_file}')
                with open(filtered_apps_file, 'r') as f:
                    all_apps = json.load(f)
                logger.info(f'Loaded {len(all_apps)} pre-filtered apps from file')
            else:
                # Perform detailed filtering
                all_apps = filter_apps_with_details(
                    all_apps, 
                    batch_size=batch_size, 
                    total_apps_to_check=detailed_limit,
                    include_free=include_free
                )
                # Save filtered apps for future use
                with open(filtered_apps_file, 'w') as f:
                    json.dump(all_apps, f, indent=2)
                logger.info(f'Saved {len(all_apps)} filtered apps to {filtered_apps_file}')
                
            logger.info(f'After detailed filtering: {len(all_apps)} valid apps')
                
        # Apply API-based filtering by default, unless specifically disabled or detailed filtering is used
        elif filter_api:
            logger.info(
                f'Applying API-based filtering to find apps with price data (sample size: {api_sample_size})'
            )
            all_apps = filter_apps_by_api_details(all_apps, sample_size=api_sample_size, include_free=include_free)
            logger.info(f'After API filtering: {len(all_apps)} apps with confirmed price data')

        # Define the list of popular game IDs - these are known to have price data
        popular_app_ids = [
            730,  # Counter-Strike 2
            570,  # Dota 2
            578080,  # PUBG
            252490,  # Rust
            1172470,  # Apex Legends
            359550,  # Rainbow Six Siege
            1938090,  # Call of Duty: Modern Warfare III
            271590,  # Grand Theft Auto V
            1086940,  # Baldur's Gate 3
            1222670,  # The Finals
            292030,  # The Witcher 3
            1091500,  # Cyberpunk 2077
            2050650,  # Resident Evil 4
            1811260,  # EA Sports FC 24
            1245620,  # Elden Ring
            440,  # Team Fortress 2
            230410,  # Warframe
            550,  # Left 4 Dead 2
            105600,  # Terraria
            620,  # Portal 2
            1172620,  # Apex Legends
            1293830,  # Forza Horizon 4
            1240440,  # Halo Infinite
            1506830,  # FIFA 23
            361420,  # ASTRONEER
            431960,  # Wallpaper Engine
            582010,  # Monster Hunter: World
            594570,  # Total War: WARHAMMER II
            289070,  # Sid Meier's Civilization VI
            477160,  # Human: Fall Flat
            291550,  # Brawlhalla
            227300,  # Euro Truck Simulator 2
            1091500,  # Cyberpunk 2077
            374320,  # DARK SOULS III
            1172470,  # Apex Legends
            391540,  # Undertale
            8930,  # Sid Meier's Civilization V
            218620,  # PAYDAY 2
            236390,  # War Thunder
            230410,  # Warframe
            377160,  # Fallout 4
            736260,  # Valheim
            381210,  # Dead by Daylight
            1446780,  # MONSTER HUNTER RISE
            435150,  # Divinity: Original Sin 2
            646570,  # Slay the Spire
            1174180,  # Red Dead Redemption 2
            1174370,  # STAR WARS Jedi: Fallen Order
            814380,  # Sekiro: Shadows Die Twice
            306130,  # The Elder Scrolls V: Skyrim Special Edition
            1174180,  # Red Dead Redemption 2
            240,  # Counter-Strike: Source
            219990,  # Grim Dawn
            648800,  # Raft
            322330,  # Don't Starve Together
            311210,  # Call of Duty: Black Ops III
            252950,  # Rocket League
            312060,  # State of Decay 2
            1281930,  # Warhammer 40,000: Darktide
            1222670,  # The Finals
        ]

        filtered_apps = all_apps

        # Filter by popular games only if requested
        if popular_only:
            logger.info('Filtering to include only popular games with known price data')
            popular_apps = []
            for app in all_apps:
                if int(app['appid']) in popular_app_ids:
                    popular_apps.append(app)

            logger.info(f'Selected {len(popular_apps)} popular apps')
            filtered_apps = popular_apps

        # Process all apps if requested (with max limit)
        elif process_all:
            # Sort by app ID to start with lower IDs which are usually more popular
            sorted_apps = sorted(all_apps, key=lambda x: int(x['appid']))

            # Limit to max_apps if specified
            if max_apps and max_apps > 0:
                logger.info(f'Processing all apps with limit of {max_apps}')
                filtered_apps = sorted_apps[:max_apps]
            else:
                # No default limit
                logger.info('Processing all apps (no limit)')
                filtered_apps = sorted_apps

            logger.warning('Processing all apps may take a very long time and hit API rate limits')

        # Apply limit if specified
        if limit_count and limit_count > 0 and not process_all:
            logger.info(f'Limiting to {limit_count} apps')
            filtered_apps = filtered_apps[:limit_count]

        logger.info(f'Processing {len(filtered_apps)} apps in total')
        all_apps = filtered_apps

        # Always fetch prices from multiple regions
        prices = fetch_multiple_regions(all_apps, args.regions)

        elapsed_time = time.time() - start_time
        logger.info(f'Process completed in {elapsed_time:.2f} seconds')

    except Exception as e:
        logger.exception(f'Error in main function: {str(e)}')
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
