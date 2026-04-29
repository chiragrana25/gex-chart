import os
import time
import requests
import base64
import datetime
import re
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
# Use ^SPX for indices to avoid yfinance errors
TICKERS = ['NVDA']

def rgb_to_hex(rgb_str):
    try:
        nums = re.findall(r'\d+', rgb_str)
        if len(nums) >= 3:
            return '#{:02x}{:02x}{:02x}'.format(int(nums[0]), int(nums[1]), int(nums[2]))
        return "#FFFFFF"
    except: return "#FFFFFF"

def get_live_price(ticker):
    try:
        t = yf.Ticker(ticker)
        # 2026 Fallback for yfinance attribute changes
        price = t.fast_info.get('lastPrice') or t.fast_info.get('last_price')
        return f"{price:.2f}" if price else "N/A"
    except: return "N/A"

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
            
            # PHASE 1: Chart Capture (7-Day)
            driver.get(f"https://mztrading.netlify.app/options/analyze/{clean_ticker}?dgextab=GEX&expiry=7")
            time.sleep(15) 
            full_path = f"full_{clean_ticker}.png"
            driver.save_screenshot(full_path)
            
            # Crop logic (left, top, right, bottom)
            img = Image.open(full_path).crop((450, 180, 1500, 950))
            crop_path = f"{clean_ticker}_final.png"
            img.save(crop_path)
            
            with open(crop_path, "rb") as f:
                b64_image = base64.b64encode(f.read()).decode('utf-8')

            # PHASE 2: Heatmap Data Extraction
            data_url = f"https://mztrading.netlify.app/options/analyze/{clean_ticker}?dgextab=GEX&dte=30&showHeatmap=true"
            data_loaded = False
            
            for attempt in range(2):
                driver.get(data_url)
                try:
                    # Wait for specific cell text to ensure table hydration
                    WebDriverWait(driver, 40).until(
                        lambda d: d.execute_script("return document.querySelector('tr td') && document.querySelector('tr td').innerText.trim().length > 0")
                    )
                    data_loaded = True
                    break
                except:
                    if attempt == 0:
                        print(f"Retrying {clean_ticker} load...")
                        driver.refresh()
                        time.sleep(5)

            if not data_loaded:
                print(f"Skipping {clean_ticker}: No data loaded.")
                continue

            values_table, colors_table = [], []
            rows = driver.find_elements(By.TAG_NAME, "tr")
            for row in rows:
                cells = row.find_elements(By.CSS_SELECTOR, "td, th")
                if not cells: continue
                
                # Fetch text and color via JS to handle sticky headers
                v_row = [driver.execute_script("return arguments[0].innerText;", c).strip() for c in cells]
                c_row = [rgb_to_hex(driver.execute_script("return window.getComputedStyle(arguments[0]).backgroundColor;", c)) for c in cells]
                
                if v_row and any(v_row):
                    values_table.append(v_row)
                    colors_table.append(c_row)

            # PHASE 3: Send Payload
            payload = {
                "ticker": clean_ticker,
                "values": values_table,
                "colors": colors_table,
                "imageData": b64_image,
                "price": get_live_price(ticker),
                "updated": (datetime.datetime.now() - datetime.timedelta(hours=4)).strftime("%I:%M %p")
            }
            requests.post(WEBAPP_URL, json=payload, timeout=60)
                
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
