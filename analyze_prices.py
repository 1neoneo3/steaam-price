#!/usr/bin/env python3
"""Script to analyze Steam price data using pandas."""

import sys
import time
from pathlib import Path

from dotenv import load_dotenv

from steam_price.dataframe import (analyze_prices, fetch_sample_data,
                                  load_prices_to_df, save_dataframe)
from steam_price.logger import get_logger

# Load environment variables
load_dotenv()

# Configuration
PROJECT_DIR = Path(__file__).parent
OUTPUT_DIR = PROJECT_DIR / 'output'
LOG_DIR = PROJECT_DIR / 'logs'

# Ensure directories exist
OUTPUT_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

# Setup logger
logger = get_logger(__name__, LOG_DIR)

def main():
    """Run price analysis on Steam data."""
    start_time = time.time()
    logger.info("Starting Steam Price Data Analysis")
    logger.info(f"Output directory: {OUTPUT_DIR}")
    
    try:
        print("=== Steam Price Data Analysis ===")
        
        # Load price data into DataFrame
        logger.info("Loading price data into DataFrame")
        df = load_prices_to_df(OUTPUT_DIR)
        
        if df is None:
            logger.error("No price data found")
            print("No price data found. Please run main.py first to fetch price data.")
            return 1
        
        # Print basic info about the dataset
        logger.info(f"Successfully loaded data for {len(df)} games")
        logger.info(f"Free games: {df['is_free'].sum()}")
        logger.info(f"Discounted games: {df['is_discounted'].sum()}")
        
        print(f"\nDataset contains {len(df)} games")
        print(f"Free games: {df['is_free'].sum()}")
        print(f"Discounted games: {df['is_discounted'].sum()}")
        
        # Save complete dataset to CSV and Excel
        logger.info("Saving full dataset to CSV and Excel")
        save_dataframe(df, OUTPUT_DIR, 'steam_prices_full')
        
        # Create a sample for easier analysis
        logger.info("Creating sample dataset for easier analysis")
        sample_df = fetch_sample_data(df, OUTPUT_DIR, sample_size=100)
        
        # Perform detailed analysis on the full dataset
        logger.info("Performing detailed price analysis")
        analyze_prices(df, OUTPUT_DIR)
        
        elapsed_time = time.time() - start_time
        logger.info(f"Analysis completed in {elapsed_time:.2f} seconds")
        
        print("\nAnalysis complete! Check the output directory for results.")
        print(f"Output directory: {OUTPUT_DIR.absolute()}")
        
    except Exception as e:
        logger.exception(f"Error in price analysis: {str(e)}")
        print(f"Error in analysis: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())