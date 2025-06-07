#!/usr/bin/env python3
"""Script to create mock price data for testing."""

# Note: This script also creates multi-region mock data

import sys
import json
import random
from pathlib import Path

# Configuration
OUTPUT_DIR = Path(__file__).parent / 'output'

# Ensure output directory exists
OUTPUT_DIR.mkdir(exist_ok=True)

def create_multi_region_mock_data():
    """Create mock data for multi-region price testing."""
    try:
        print("=== Creating Multi-Region Mock Price Data ===")
        
        # Define regions (country code, currency code, currency symbol)
        regions = [
            ('US', 'USD', '$'),      # United States (USD)
            ('JP', 'JPY', '¥'),      # Japan (JPY)
            ('GB', 'GBP', '£'),      # United Kingdom (GBP)
            ('EU', 'EUR', '€'),      # Euro zone (EUR)
            ('CA', 'CAD', 'C$'),     # Canada (CAD)
        ]
        
        # Create multi-region directory
        multi_region_dir = OUTPUT_DIR / 'multi_region'
        multi_region_dir.mkdir(exist_ok=True)
        
        # Create mock app data (use same apps as regular mock data)
        game_names = [
            "Counter-Strike 2", "Dota 2", "PUBG: BATTLEGROUNDS", "Rust", "Apex Legends",
            "Tom Clancy's Rainbow Six Siege", "Call of Duty: Modern Warfare III", 
            "Grand Theft Auto V", "Baldur's Gate 3", "The Finals",
            "Elden Ring", "Cyberpunk 2077", "Red Dead Redemption 2", "Hogwarts Legacy",
            "Stardew Valley", "Terraria", "Minecraft", "Fortnite", "The Witcher 3", "Starfield"
        ]
        
        mock_apps = []
        for i, name in enumerate(game_names):
            mock_apps.append({
                "appid": 10000 + i,
                "name": name
            })
        
        # Base prices in USD for typical games (these will be converted to other currencies)
        base_prices_usd = {
            "Counter-Strike 2": 0,       # Free to play
            "Dota 2": 0,                 # Free to play 
            "PUBG: BATTLEGROUNDS": 29.99,
            "Rust": 39.99,
            "Apex Legends": 0,           # Free to play
            "Tom Clancy's Rainbow Six Siege": 19.99,
            "Call of Duty: Modern Warfare III": 69.99,
            "Grand Theft Auto V": 29.99,
            "Baldur's Gate 3": 59.99,
            "The Finals": 0,             # Free to play
            "Elden Ring": 59.99,
            "Cyberpunk 2077": 59.99,
            "Red Dead Redemption 2": 59.99,
            "Hogwarts Legacy": 49.99,
            "Stardew Valley": 14.99,
            "Terraria": 9.99,
            "Minecraft": 19.99,
            "Fortnite": 0,               # Free to play
            "The Witcher 3": 39.99,
            "Starfield": 69.99
        }
        
        # Exchange rates (to convert from USD to other currencies)
        # These are rough approximations - actual rates fluctuate
        exchange_rates = {
            'USD': 1.0,
            'JPY': 145.0,
            'GBP': 0.78,
            'EUR': 0.92,
            'CAD': 1.35,
        }
        
        # Regional pricing factors (regional price variations compared to USD)
        # Some regions might have higher or lower relative prices
        regional_factors = {
            'US': 1.0,    # Baseline
            'JP': 0.95,   # Slightly cheaper
            'GB': 1.05,   # Slightly more expensive
            'EU': 1.05,   # Slightly more expensive
            'CA': 0.92,   # Cheaper
        }
        
        # Create multi-region price data
        multi_region_prices = {}
        
        for app in mock_apps:
            app_id = str(app["appid"])
            app_name = app["name"]
            
            # Base price in USD
            base_price_usd = base_prices_usd.get(app_name, 29.99)  # Default to 29.99 if not specified
            
            # Randomize discount
            is_free = base_price_usd == 0
            is_discounted = not is_free and random.random() < 0.3  # 30% chance of discount
            discount_percent = 0
            
            if is_discounted:
                discount_percent = random.choice([10, 15, 20, 25, 30, 33, 40, 50, 60, 75])
            
            # Initialize app price data
            price_data = {
                'name': app_name,
                'regions': {},
                'has_price': not is_free,
            }
            
            # Generate prices for each region
            for country, currency, symbol in regions:
                # Convert base price to regional currency
                regional_base_price = base_price_usd * exchange_rates[currency] * regional_factors[country]
                
                # Round to appropriate price point based on currency
                if currency == 'JPY':
                    # JPY doesn't use decimals
                    regional_base_price = round(regional_base_price / 10) * 10
                elif currency in ['USD', 'CAD', 'AUD']:
                    # Common price points like X.99
                    regional_base_price = round(regional_base_price * 4) / 4
                    if regional_base_price > 0:
                        regional_base_price = int(regional_base_price) + 0.99
                else:
                    # Other currencies, round to 0.99
                    regional_base_price = round(regional_base_price)
                    if regional_base_price > 0:
                        regional_base_price = int(regional_base_price) + 0.99
                
                # Apply discount if applicable
                final_price = regional_base_price
                if is_discounted:
                    final_price = round(regional_base_price * (1 - discount_percent / 100), 2)
                    if currency == 'JPY':
                        # JPY doesn't use decimals
                        final_price = round(final_price)
                
                # Format price for display
                if currency == 'JPY':
                    formatted_price = f"{symbol}{int(final_price)}"
                else:
                    formatted_price = f"{symbol}{final_price:.2f}"
                
                # Store region data
                region_data = {
                    'currency': currency,
                    'symbol': symbol,
                    'initial': float(regional_base_price),
                    'final': float(final_price),
                    'discount_percent': discount_percent,
                    'formatted': formatted_price,
                    'savings': float(regional_base_price - final_price) if is_discounted else 0
                }
                
                price_data['regions'][country] = region_data
            
            # Add to multi-region prices
            multi_region_prices[app_id] = price_data
        
        # Save multi-region price data
        with open(multi_region_dir / 'multi_region_prices.json', 'w') as f:
            json.dump(multi_region_prices, f, indent=2)
        
        print(f"Created multi-region price data for {len(multi_region_prices)} games across {len(regions)} regions")
        
        return True
    
    except Exception as e:
        print(f"Error creating multi-region mock data: {str(e)}")
        return False


def main():
    """Create mock data for testing."""
    try:
        print("=== Creating Mock Steam Price Data ===")
        
        # Create mock exchange rates
        # These are rates FROM JPY TO other currencies
        # Example: 1 JPY = 0.006910 USD
        exchange_rates = {
            "USD": 0.006910,
            "EUR": 0.006060,
            "GBP": 0.005110,
            "CAD": 0.009300,
            "AUD": 0.010200,
            "CNY": 0.047800,
            "KRW": 9.090000,
        }
        
        # Save mock exchange rates
        with open(OUTPUT_DIR / 'exchange_rates.json', 'w') as f:
            json.dump(exchange_rates, f, indent=2)
        
        print(f"Created mock exchange rates with {len(exchange_rates)} currencies")
        
        # Create mock app data
        game_names = [
            "Counter-Strike 2", "Dota 2", "PUBG: BATTLEGROUNDS", "Rust", "Apex Legends",
            "Tom Clancy's Rainbow Six Siege", "Call of Duty: Modern Warfare III", 
            "Grand Theft Auto V", "Baldur's Gate 3", "The Finals",
            "Elden Ring", "Cyberpunk 2077", "Red Dead Redemption 2", "Hogwarts Legacy",
            "Stardew Valley", "Terraria", "Minecraft", "Fortnite", "The Witcher 3", "Starfield"
        ]
        
        mock_apps = []
        for i, name in enumerate(game_names):
            mock_apps.append({
                "appid": 10000 + i,
                "name": name
            })
        
        # Save mock apps
        with open(OUTPUT_DIR / 'apps.json', 'w') as f:
            json.dump(mock_apps, f, indent=2)
        
        print(f"Created mock data for {len(mock_apps)} apps")
        
        # Create mock price data
        mock_prices = {}
        
        for app in mock_apps:
            app_id = str(app["appid"])
            
            # Randomize price data
            is_free = random.random() < 0.2  # 20% chance of being free
            
            # Base price in JPY
            if is_free:
                price_jpy = 0
            else:
                price_jpy = random.choice([
                    490, 980, 1480, 1980, 2980, 3980, 4980, 
                    5980, 7980, 8980, 9800, 12800, 19800
                ])
            
            # Discount info
            is_discounted = not is_free and random.random() < 0.3  # 30% chance of discount for non-free games
            discount_percent = 0
            initial_price = price_jpy
            final_price = price_jpy
            
            if is_discounted:
                discount_percent = random.choice([10, 15, 20, 25, 33, 40, 50, 60, 75, 80])
                final_price = round(initial_price * (1 - discount_percent / 100))
            
            # Convert to other currencies using exchange rates
            prices = {
                "JPY": final_price,
                "USD": round(final_price * exchange_rates["USD"], 2),
                "EUR": round(final_price * exchange_rates["EUR"], 2),
                "GBP": round(final_price * exchange_rates["GBP"], 2)
            }
            
            # Create the price entry
            mock_prices[app_id] = {
                "name": app["name"],
                "prices": prices,
                "discount_percent": discount_percent,
                "initial": initial_price,
                "final": final_price
            }
        
        # Save mock prices
        with open(OUTPUT_DIR / 'prices.json', 'w') as f:
            json.dump(mock_prices, f, indent=2)
        
        print(f"Created mock price data for {len(mock_prices)} games")
        
        # Create multi-region mock data
        create_multi_region_mock_data()
        
        print("Mock data creation complete!")
        
    except Exception as e:
        print(f"Error creating mock data: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())