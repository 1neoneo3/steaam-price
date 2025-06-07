require('dotenv').config();
const axios = require('axios');
const fs = require('fs');
const path = require('path');

// Steam API endpoints
const STEAM_APP_LIST_API = 'https://api.steampowered.com/ISteamApps/GetAppList/v2/';
const STEAM_PRICE_API = 'https://store.steampowered.com/api/appdetails';

// Exchange rate API endpoint
const EXCHANGE_RATE_API = 'https://api.exchangerate-api.com/v4/latest/JPY';

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

// Fetch all Steam apps
async function fetchAllSteamApps() {
  try {
    console.log('Fetching all Steam apps...');
    const response = await axios.get(STEAM_APP_LIST_API);
    
    if (response.status === 200 && response.data && response.data.applist && response.data.applist.apps) {
      const apps = response.data.applist.apps;
      console.log(`Retrieved ${apps.length} apps from Steam API`);
      
      // Save apps to file
      fs.writeFileSync(APPS_FILE, JSON.stringify(apps, null, 2));
      
      return apps;
    } else {
      throw new Error('Invalid response format from Steam API');
    }
  } catch (error) {
    console.error('Error fetching Steam apps:', error.message);
    
    // If we have a local cache, use that instead
    if (fs.existsSync(APPS_FILE)) {
      console.log('Using cached app list');
      return JSON.parse(fs.readFileSync(APPS_FILE, 'utf8'));
    }
    
    throw error;
  }
}

// Fetch exchange rates
async function fetchExchangeRates() {
  try {
    console.log('Fetching exchange rates...');
    const response = await axios.get(EXCHANGE_RATE_API);
    
    if (response.status === 200 && response.data && response.data.rates) {
      const rates = response.data.rates;
      console.log('Exchange rates retrieved successfully');
      
      // Save exchange rates to file
      fs.writeFileSync(EXCHANGE_RATES_FILE, JSON.stringify(rates, null, 2));
      
      return rates;
    } else {
      throw new Error('Invalid response format from Exchange Rate API');
    }
  } catch (error) {
    console.error('Error fetching exchange rates:', error.message);
    
    // If we have a local cache, use that instead
    if (fs.existsSync(EXCHANGE_RATES_FILE)) {
      console.log('Using cached exchange rates');
      return JSON.parse(fs.readFileSync(EXCHANGE_RATES_FILE, 'utf8'));
    }
    
    throw error;
  }
}

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
    // Fetch all apps and exchange rates
    const [allApps, exchangeRates] = await Promise.all([
      fetchAllSteamApps(),
      fetchExchangeRates()
    ]);
    
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

// Generate a summary report
function generateReport(prices) {
  const totalApps = Object.keys(prices).length;
  const freeApps = Object.values(prices).filter(p => p.prices.JPY === 0).length;
  const discountedApps = Object.values(prices).filter(p => p.discount_percent > 0).length;
  
  const priceRanges = {
    'Free': 0,
    'Under $5': 0,
    '$5-$10': 0,
    '$10-$20': 0,
    '$20-$30': 0,
    '$30-$60': 0,
    'Over $60': 0
  };
  
  Object.values(prices).forEach(app => {
    const priceUSD = app.prices.USD;
    
    if (priceUSD === 0) {
      priceRanges['Free']++;
    } else if (priceUSD < 5) {
      priceRanges['Under $5']++;
    } else if (priceUSD < 10) {
      priceRanges['$5-$10']++;
    } else if (priceUSD < 20) {
      priceRanges['$10-$20']++;
    } else if (priceUSD < 30) {
      priceRanges['$20-$30']++;
    } else if (priceUSD < 60) {
      priceRanges['$30-$60']++;
    } else {
      priceRanges['Over $60']++;
    }
  });
  
  console.log('\n=== PRICE REPORT ===');
  console.log(`Total apps with price data: ${totalApps}`);
  console.log(`Free apps: ${freeApps} (${((freeApps / totalApps) * 100).toFixed(2)}%)`);
  console.log(`Discounted apps: ${discountedApps} (${((discountedApps / totalApps) * 100).toFixed(2)}%)`);
  console.log('\nPrice distribution (USD):');
  
  Object.entries(priceRanges).forEach(([range, count]) => {
    console.log(`${range}: ${count} (${((count / totalApps) * 100).toFixed(2)}%)`);
  });
}

// Find games with the biggest discounts
function findBiggestDiscounts(prices, limit = 10) {
  const discountedApps = Object.values(prices)
    .filter(app => app.discount_percent > 0)
    .sort((a, b) => b.discount_percent - a.discount_percent)
    .slice(0, limit);
  
  console.log('\n=== BIGGEST DISCOUNTS ===');
  discountedApps.forEach(app => {
    const originalPrice = app.initial;
    const discountedPrice = app.final;
    const savings = originalPrice - discountedPrice;
    
    console.log(`${app.name} - ${app.discount_percent}% OFF`);
    console.log(`  Original: ¥${originalPrice.toFixed(2)} (${app.prices.USD.toFixed(2)} USD)`);
    console.log(`  Current: ¥${discountedPrice.toFixed(2)} (${(app.prices.USD).toFixed(2)} USD)`);
    console.log(`  You save: ¥${savings.toFixed(2)} (${(savings / exchangeRates.USD).toFixed(2)} USD)`);
    console.log('-------------------');
  });
}

// Run the main function
let exchangeRates = {};

(async () => {
  try {
    const prices = await fetchAllPrices();
    exchangeRates = JSON.parse(fs.readFileSync(EXCHANGE_RATES_FILE, 'utf8'));
    
    // Generate reports
    generateReport(prices);
    findBiggestDiscounts(prices);
  } catch (error) {
    console.error('Error in main function:', error);
  }
})();