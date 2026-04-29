import os, time, requests, base64, datetime, re
import yfinance as yf
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from PIL import Image

# --- CONFIGURATION ---
WEBAPP_URL = os.environ.get('WEBAPP_URL')
TICKERS = ['SPY', 'QQQ', 'NVDA']

def rgb_to_hex(rgb_str):
    try:
        nums = re.findall(r'\d+', rgb_str)
        if len(nums) >= 3:
            return '#{:02x}{:02x}{:02x}'.format(int(nums[0]), int(nums[1]), int(nums[2]))
        return "#FFFFFF"
    except: return "#FFFFFF"

def setup_driver():
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def main():
    if not WEBAPP_URL:
        print("CRITICAL: WEBAPP_URL secret is missing!")
        return

    driver = setup_driver()
    try:
        for ticker in TICKERS:
            clean_ticker = ticker.replace('^', '')
            print(f"Processing {clean_ticker}...")
            
            # PHASE 1: Chart Capture (7-Day View)
            driver.get(f"https://mztrading.netlify.app/options/analyze/{clean_ticker}?dgextab=GEX&expiry=7")
            time.sleep(15) 
            full_path = f"full_{clean_ticker}.png"
            driver.save_screenshot(full_path)
            Image.open(full_path).crop((450, 180, 1500, 950)).save(f"{clean_ticker}_final.png")
            with open(f"{clean_ticker}_final.png", "rb") as f:
                b64_image = base64.b64encode(f.read()).decode('utf-8')

            # PHASE 2: Heatmap Extraction (FORCED 30-Day DTE)
            driver
