// Script to fetch prices for Steam apps in batches
require('dotenv').config();
const axios = require('axios');
const fs = require('fs');
const path = require('path');

// Steam API endpoint for price details
const STEAM_PRICE_API = 'https://store.steampowered.com/api/appdetails';

// Configuration
const BATCH_SIZE = 1000; // Process 1000 apps per batch
const OUTPUT_DIR = path.join(__dirname, 'output');
const PRICES_FILE = path.join(OUTPUT_DIR, 'prices.json');
const APPS_FILE = path.join(OUTPUT_DIR, 'apps.json');
const EXCHANGE_RATES_FILE = path.join(OUTPUT_DIR, 'exchange_rates.json');

// Ensure output directory exists
if (!fs.existsSync(OUTPUT_DIR)) {
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });
}

// Delay function to avoid rate limiting
const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));

// Fetch price for a batch of apps
async function fetchPricesForBatch(apps, batchIndex, exchangeRates) {
  console.log(`Processing batch ${batchIndex + 1} (${apps.length} apps)...`);
  
  const prices = {};
  let successCount = 0;
  
  for (let i = 0; i < apps.length; i++) {
    const app = apps[i];
    try {
      // Every 5 requests, add a small delay to avoid rate limiting
      if (i % 5 === 0 && i > 0) {
        await delay(1000); // 1 second delay
      }
      
      const response = await axios.get(STEAM_PRICE_API, {
        params: {
          appids: app.appid,
          cc: 'JP', // Country code for Japan to get JPY prices
          filters: 'price_overview'
        },
        timeout: 5000 // 5 second timeout
      });
      
      if (response.data && response.data[app.appid] && response.data[app.appid].success) {
        const data = response.data[app.appid].data;
        
        if (data && data.price_overview) {
          const priceInfo = data.price_overview;
          const priceInJPY = priceInfo.final / 100; // Steam prices are in cents
          
          // Convert JPY to other currencies
          const convertedPrices = {
            JPY: priceInJPY,
            USD: priceInJPY / exchangeRates.USD,
            EUR: priceInJPY / exchangeRates.EUR,
            GBP: priceInJPY / exchangeRates.GBP
          };
          
          prices[app.appid] = {
            name: app.name,
            prices: convertedPrices,
            discount_percent: priceInfo.discount_percent,
            initial: priceInfo.initial / 100,
            final: priceInfo.final / 100
          };
          
          successCount++;
          
          // Log progress for every 50 apps
          if (i % 50 === 0 || i === apps.length - 1) {
            console.log(`Batch ${batchIndex + 1}: Processed ${i + 1}/${apps.length} apps (${successCount} with price data)`);
          }
        }
      }
    } catch (error) {
      // Just log the error and continue with the next app
      if (i % 50 === 0) {
        console.error(`Error fetching price for app ${app.appid} (${app.name}):`, error.message);
      }
    }
  }
  
  console.log(`Batch ${batchIndex + 1} complete. Got prices for ${successCount}/${apps.length} apps`);
  return prices;
}

// Main function to fetch all prices
async function fetchAllPrices() {
  try {
    // Check if apps file exists
    if (!fs.existsSync(APPS_FILE)) {
      console.error('Apps file not found. Run fetchApps.js first.');
      process.exit(1);
    }
    
    // Check if exchange rates file exists
    if (!fs.existsSync(EXCHANGE_RATES_FILE)) {
      console.error('Exchange rates file not found. Run fetchExchangeRates.js first.');
      process.exit(1);
    }
    
    // Load apps and exchange rates
    const allApps = JSON.parse(fs.readFileSync(APPS_FILE, 'utf8'));
    const exchangeRates = JSON.parse(fs.readFileSync(EXCHANGE_RATES_FILE, 'utf8'));
    
    console.log(`Starting to fetch prices for ${allApps.length} apps in batches of ${BATCH_SIZE}`);
    
    // Split apps into batches
    const batches = [];
    for (let i = 0; i < allApps.length; i += BATCH_SIZE) {
      batches.push(allApps.slice(i, i + BATCH_SIZE));
    }
    
    console.log(`Split apps into ${batches.length} batches`);
    
    // Load existing prices if available
    let allPrices = {};
    if (fs.existsSync(PRICES_FILE)) {
      allPrices = JSON.parse(fs.readFileSync(PRICES_FILE, 'utf8'));
      console.log(`Loaded ${Object.keys(allPrices).length} existing price entries`);
    }
    
    // Process batches one by one to avoid overwhelming the API
    for (let i = 0; i < batches.length; i++) {
      const batchPrices = await fetchPricesForBatch(batches[i], i, exchangeRates);
      
      // Merge with existing prices
      allPrices = { ...allPrices, ...batchPrices };
      
      // Save after each batch to preserve progress
      fs.writeFileSync(PRICES_FILE, JSON.stringify(allPrices, null, 2));
      console.log(`Saved prices after batch ${i + 1}/${batches.length}`);
      
      // Add a delay between batches to be nice to the API
      if (i < batches.length - 1) {
        console.log('Waiting 5 seconds before next batch...');
        await delay(5000);
      }
    }
    
    console.log(`Price fetching complete. Got prices for ${Object.keys(allPrices).length} apps`);
    return allPrices;
  } catch (error) {
    console.error('Error in fetchAllPrices:', error);
    throw error;
  }
}

// Run the fetch function
(async () => {
  try {
    await fetchAllPrices();
  } catch (error) {
    console.error('Error in main function:', error);
    process.exit(1);
  }
})();