// Script to fetch all Steam apps and save them to a file
require('dotenv').config();
const axios = require('axios');
const fs = require('fs');
const path = require('path');

// Steam API endpoint for app list
const STEAM_APP_LIST_API = 'https://api.steampowered.com/ISteamApps/GetAppList/v2/';

// Configuration
const OUTPUT_DIR = path.join(__dirname, 'output');
const APPS_FILE = path.join(OUTPUT_DIR, 'apps.json');

// Ensure output directory exists
if (!fs.existsSync(OUTPUT_DIR)) {
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });
}

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
      console.log(`App list saved to ${APPS_FILE}`);
      
      return apps;
    } else {
      throw new Error('Invalid response format from Steam API');
    }
  } catch (error) {
    console.error('Error fetching Steam apps:', error.message);
    throw error;
  }
}

// Run the fetch function
(async () => {
  try {
    await fetchAllSteamApps();
  } catch (error) {
    console.error('Error in main function:', error);
    process.exit(1);
  }
})();