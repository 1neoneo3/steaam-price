"""Module for fetching Steam apps."""

import json
import re
import time
import random
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Set

import requests

from steam_price.logger import get_logger

# Steam API endpoints
STEAM_APP_LIST_API = 'https://api.steampowered.com/ISteamApps/GetAppList/v2/'
STEAM_STORE_API = 'https://store.steampowered.com/api/appdetails'

# Steam store API parameters
DEFAULT_COUNTRY_CODE = 'US'  # Use US as default for filtering
API_DELAY = 3.0  # Increased from 1.0s to 3.0s to avoid rate limits

# App types that likely don't have price data
NON_PRICED_APP_TYPES = {
    'demo', 'dlc', 'mod', 'tool', 'soundtrack', 'video', 'hardware',
    'advertising', 'application', 'config', 'driver', 'media', 'server'
}

# Setup logger
logger = get_logger(__name__)


def fetch_app_details(app_id: int, country_code: str = DEFAULT_COUNTRY_CODE) -> Optional[Dict[str, Any]]:
    """Fetch detailed information about a specific app from Steam API.
    
    Args:
        app_id: The Steam app ID
        country_code: Country code for regional pricing and availability
        
    Returns:
        App details dictionary or None if unavailable
    """
    
    # Prepare API request parameters
    params = {
        'appids': app_id,
        'cc': country_code,
        'l': 'english'  # Language
    }
    
    logger.debug(f"Fetching details for app {app_id} from Steam API (country: {country_code})")
    
    try:
        response = requests.get(STEAM_STORE_API, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if str(app_id) in data and data[str(app_id)]['success']:
            return data[str(app_id)]['data']
        
        logger.debug(f"App {app_id} details not found or not successful")
        return None
    except Exception as e:
        logger.debug(f"Error fetching details for app {app_id}: {e}")
        return None


def get_app_details_batch(app_ids: List[int], batch_size: int = 100, 
                          country_code: str = DEFAULT_COUNTRY_CODE) -> Dict[int, Dict[str, Any]]:
    """Fetch details for a batch of apps with rate limiting.
    
    Args:
        app_ids: List of app IDs to fetch details for
        batch_size: Number of apps to process in each batch
        country_code: Country code for regional pricing
        
    Returns:
        Dictionary mapping app_id to app details
    """
    app_details = {}
    total_apps = len(app_ids)
    
    logger.info(f"Fetching detailed information for {total_apps} apps in batches of {batch_size}")
    
    # Process in small batches to avoid overwhelming the API
    for i in range(0, total_apps, batch_size):
        batch = app_ids[i:i + batch_size]
        logger.info(f"Processing batch {i//batch_size + 1}/{(total_apps + batch_size - 1)//batch_size}: {len(batch)} apps")
        
        for app_id in batch:
            details = fetch_app_details(app_id, country_code)
            if details:
                app_details[app_id] = details
            
            # Delay to avoid rate limiting with jitter
            jitter = random.uniform(0.8, 1.2)
            actual_delay = API_DELAY * jitter
            time.sleep(actual_delay)
        
        # Log progress
        logger.info(f"Retrieved details for {len(app_details)} apps so far")
    
    return app_details


def filter_apps_by_api_details(apps: List[Dict[str, Any]], 
                               sample_size: int = 100,
                               country_code: str = DEFAULT_COUNTRY_CODE,
                               include_free: bool = False) -> List[Dict[str, Any]]:
    """Filter apps by fetching detailed information from Steam API.
    
    This is the recommended filtering method as it provides a good balance
    between accuracy and API usage.
    
    Args:
        apps: List of all Steam apps
        sample_size: Maximum number of apps to check (for efficiency)
        country_code: Country code for regional pricing
        include_free: Whether to include free apps in the results
        
    Returns:
        Filtered list of apps that are likely to have price data
    """
    # Select a reasonable sample size to avoid excessive API calls
    # Use smaller of: sample_size or all apps
    sample_size = min(len(apps), sample_size)
    
    # Prioritize apps in known game ID ranges for more accurate sampling
    likely_ranges = [(0, 100000), (200000, 400000), (500000, 1000000)]
    likely_game_ids = []
    
    # First collect apps in likely ranges
    for app in apps:
        app_id = int(app['appid'])
        if any(start <= app_id <= end for start, end in likely_ranges):
            likely_game_ids.append(app_id)
            if len(likely_game_ids) >= sample_size:
                break
    
    # If we don't have enough, add more apps
    remaining_app_ids = [
        int(app['appid']) for app in apps 
        if int(app['appid']) not in likely_game_ids
    ]
    
    app_ids = likely_game_ids + remaining_app_ids[:max(0, sample_size - len(likely_game_ids))]
    app_ids = app_ids[:sample_size]  # Make sure we don't exceed the sample size
    
    logger.info(f"Selected {len(app_ids)} apps for API detail checking")
    
    # Fetch details for the sample
    app_details = get_app_details_batch(app_ids, batch_size=100, country_code=country_code)
    
    # Filter apps based on their details
    priced_apps = []
    free_apps = []
    demo_apps = []
    dlc_apps = []
    not_released_apps = []
    other_apps = []
    
    for app_id, details in app_details.items():
        # Get a matching app dict from the original list
        app_dict = next((app for app in apps if int(app['appid']) == app_id), None)
        if not app_dict:
            continue
            
        # Get key attributes
        app_type = details.get('type', '').lower()
        is_game = app_type == 'game'
        is_released = not details.get('release_date', {}).get('coming_soon', False)
        has_price = 'price_overview' in details
        is_free = details.get('is_free', False)
        is_demo = 'demo' in app_type or 'demo' in app_dict['name'].lower()
        is_dlc = app_type == 'dlc' or 'dlc' in app_dict['name'].lower()
        
        # Categorize the app
        if is_demo:
            demo_apps.append(app_dict)
        elif is_dlc:
            dlc_apps.append(app_dict)
        elif not is_released:
            not_released_apps.append(app_dict)
        elif is_game:
            if has_price:
                priced_apps.append(app_dict)
            elif is_free:
                free_apps.append(app_dict)
            else:
                other_apps.append(app_dict)
        else:
            other_apps.append(app_dict)
    
    # Log the distribution of app types
    logger.info(f"App type distribution in sample:")
    logger.info(f"  - Priced games: {len(priced_apps)}")
    logger.info(f"  - Free games: {len(free_apps)}")
    logger.info(f"  - Demo apps: {len(demo_apps)}")
    logger.info(f"  - DLC apps: {len(dlc_apps)}")
    logger.info(f"  - Unreleased apps: {len(not_released_apps)}")
    logger.info(f"  - Other apps: {len(other_apps)}")
    
    # Calculate the ratio of priced apps in the sample
    total_valid = len(priced_apps) + len(free_apps)
    if total_valid > 0:
        priced_ratio = len(priced_apps) / total_valid
        logger.info(f"Ratio of priced to free games: {priced_ratio:.2f}")
    
    # Return appropriate apps based on the include_free flag
    if include_free:
        combined_apps = priced_apps + free_apps
        logger.info(f"Returning {len(combined_apps)} apps (priced and free)")
        return combined_apps
    else:
        logger.info(f"Returning {len(priced_apps)} priced apps only")
        return priced_apps




def filter_apps_with_details(all_apps: List[Dict[str, Any]], 
                            country_code: str = DEFAULT_COUNTRY_CODE,
                            batch_size: int = 20,
                            total_apps_to_check: int = 2000,
                            include_free: bool = False) -> List[Dict[str, Any]]:
    """Filter apps by checking detailed information for each app.
    
    This function checks each app's details from the Steam API to determine:
    - If it's a game that exists and can be retrieved
    - If it has price data (not free unless include_free is True)
    - If it's not discontinued/removed from store
    
    Args:
        all_apps: List of all Steam apps
        country_code: Country code for regional pricing
        batch_size: Number of apps to process in each batch
        total_apps_to_check: Maximum number of apps to check in total
        include_free: Whether to include free apps in the results
        
    Returns:
        Filtered list of apps with valid price data
    """
    # Prioritize apps in known game ID ranges
    logger.info(f"Applying initial filtering to {len(all_apps)} apps")
    
    # Common app ID ranges for games with price data
    likely_game_ranges = [
        (0, 100000),       # Early Steam games
        (200000, 400000),  # Mid-era Steam games
        (500000, 1000000), # Modern popular games
    ]
    
    # Keywords that suggest a game with price
    game_keywords = [
        'game', 'rpg', 'action', 'adventure', 'strategy', 'shooter', 
        'puzzle', 'simulation', 'sports', 'racing', 'indie'
    ]
    
    # Keywords that suggest no price data
    non_game_keywords = [
        'demo', 'beta', 'test', 'server', 'dedicated', 'soundtrack', 
        'sdk', 'dlc', 'tool', 'content pack', 'artbook', 'manual'
    ]
    
    # Apply basic filtering
    likely_apps = []
    for app in all_apps:
        app_id = int(app['appid'])
        name = app['name'].lower()
        
        # Skip apps with known non-game keywords
        if any(keyword in name for keyword in non_game_keywords):
            continue
            
        # Include apps with game keywords
        has_game_keyword = any(keyword in name for keyword in game_keywords)
        
        # Check if app ID is in likely game ranges
        is_in_likely_range = any(start <= app_id <= end for start, end in likely_game_ranges)
        
        # Include if either condition is met
        if has_game_keyword or is_in_likely_range:
            likely_apps.append(app)
            
    logger.info(f"Initial filtering: {len(likely_apps)} apps selected out of {len(all_apps)}")
    
    # Limit the number of apps to check to avoid excessive API calls
    apps_to_check = likely_apps[:min(len(likely_apps), total_apps_to_check)]
    logger.info(f"Will check details for {len(apps_to_check)} apps in batches of {batch_size}")
    
    valid_apps = []
    invalid_apps = []
    free_apps = []
    discontinued_apps = []
    app_types = {}
    
    # Process in batches
    for i in range(0, len(apps_to_check), batch_size):
        batch = apps_to_check[i:i + batch_size]
        logger.info(f"Processing batch {i//batch_size + 1}/{(len(apps_to_check) + batch_size - 1)//batch_size}: {len(batch)} apps")
        
        for app in batch:
            app_id = int(app['appid'])
            app_name = app['name']
            details = fetch_app_details(app_id, country_code)
            
            if details is None:
                # App couldn't be retrieved
                invalid_apps.append(app)
                logger.debug(f"App {app_id} ({app_name}) couldn't be retrieved")
                continue
                
            # Check app type
            app_type = details.get('type', '').lower()
            if app_type in app_types:
                app_types[app_type] += 1
            else:
                app_types[app_type] = 1
                
            # Check if it's a game
            if app_type != 'game':
                invalid_apps.append(app)
                logger.debug(f"App {app_id} ({app_name}) is not a game, type: {app_type}")
                continue
                
            # Check if the game is free
            is_free = details.get('is_free', False)
            if is_free:
                free_apps.append(app)
                logger.debug(f"App {app_id} ({app_name}) is free")
                if not include_free:
                    continue
                    
            # Check if the game has price data
            has_price = 'price_overview' in details
            if not has_price and not is_free:
                # No price data and not marked as free (might be discontinued)
                discontinued_apps.append(app)
                logger.debug(f"App {app_id} ({app_name}) has no price data and is not marked as free")
                continue
                
            # This is a valid app
            valid_apps.append(app)
            
            # Delay to avoid rate limiting
            jitter = random.uniform(0.8, 1.2)
            actual_delay = API_DELAY * jitter
            time.sleep(actual_delay)
            
        # Log progress after each batch
        logger.info(f"Progress: Found {len(valid_apps)} valid apps, {len(free_apps)} free apps, {len(invalid_apps)} invalid apps, {len(discontinued_apps)} discontinued apps")
    
    # Log app type distribution
    logger.info(f"App type distribution:")
    for app_type, count in sorted(app_types.items(), key=lambda x: x[1], reverse=True):
        logger.info(f"  - {app_type}: {count}")
    
    # Determine the final list based on include_free flag
    result_apps = valid_apps
    if include_free:
        # Include apps that are explicitly marked as free
        result_apps = [app for app in valid_apps]
        free_apps_not_in_valid = [app for app in free_apps if app not in valid_apps]
        result_apps.extend(free_apps_not_in_valid)
        
    logger.info(f"Final filtered apps: {len(result_apps)} apps")
    logger.info(f"Free apps: {len(free_apps)}, Invalid apps: {len(invalid_apps)}, Discontinued apps: {len(discontinued_apps)}")
    
    return result_apps


def fetch_all_steam_apps(output_dir: Path) -> List[Dict[str, Any]]:
    """Fetch all Steam apps and save them to a file.

    Args:
        output_dir: Directory to save the output file

    Returns:
        List of apps from the Steam API
    """
    apps_file = output_dir / 'apps.json'
    # File-based caching is maintained for backward compatibility

    try:
        logger.info('Fetching all Steam apps...')
        logger.debug(f'API endpoint: {STEAM_APP_LIST_API}')

        response = requests.get(STEAM_APP_LIST_API, timeout=10)
        response.raise_for_status()

        logger.debug(f'Response status code: {response.status_code}')
        data = response.json()

        if data and 'applist' in data and 'apps' in data['applist']:
            apps = data['applist']['apps']
            logger.info(f'Retrieved {len(apps)} apps from Steam API')
            logger.debug(f'First few apps: {apps[:3]}')

            # Save apps to file (for backward compatibility)
            with open(apps_file, 'w') as f:
                json.dump(apps, f, indent=2)

            logger.info(f'App list saved to {apps_file}')
            return apps
        else:
            logger.error('Invalid response format from Steam API')
            logger.debug(f'Response data: {data}')
            raise ValueError('Invalid response format from Steam API')

    except requests.RequestException as e:
        logger.error(f'HTTP error fetching Steam apps: {str(e)}')

        # If we have a local cache, use that instead
        if apps_file.exists():
            logger.warning('Using cached app list due to API error')
            with open(apps_file, 'r') as f:
                cached_apps = json.load(f)
            logger.info(f'Loaded {len(cached_apps)} apps from cache file')
            return cached_apps

        logger.exception('No cached data available')
        raise

    except Exception as e:
        logger.exception(f'Unexpected error fetching Steam apps: {str(e)}')

        # If we have a local cache, use that instead
        if apps_file.exists():
            logger.warning('Using cached app list due to error')
            with open(apps_file, 'r') as f:
                cached_apps = json.load(f)
            logger.info(f'Loaded {len(cached_apps)} apps from cache file')
            return cached_apps

        logger.error('No cached data available and API request failed')
        raise
