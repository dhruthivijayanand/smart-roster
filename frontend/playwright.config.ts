import {defineConfig} from '@playwright/test';
export default defineConfig({testDir:'./e2e',timeout:240000,workers:1,use:{baseURL:process.env.TEST_BASE_URL||'http://127.0.0.1:8000',headless:true,launchOptions:{executablePath:process.env.CHROME_PATH||'C:/Program Files/Google/Chrome/Application/chrome.exe'},viewport:{width:1440,height:1000},screenshot:'only-on-failure'},reporter:[['list'],['json',{outputFile:'../docs/browser-tests.json'}]]});


