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
from selenium.webdriver.support import expected_conditions as EC
from PIL import Image

# --- CONFIGURATION ---
WEBAPP_URL = os.environ.get('WEBAPP_URL')
TICKERS = ['^SPX', 'SPY', 'QQQ', 'NVDA', 'TSLA', 'AAPL', 'AMD', 'MU', 'MSFT', 'UNH'] 

def rgb_to_hex(rgb_str):
    if not rgb_str or 'rgba(0, 0, 0, 0)' in rgb_str or 'transparent' in rgb_str:
        return "#FFFFFF"
    try:
        nums = re.findall(r'\d+', rgb_str)
        if len(nums) >= 3:
            return '#{:02x}{:02x}{:02x}'.format(int(nums[0]), int(nums[1]), int(nums[2]))
        return "#FFFFFF"
    except: return "#FFFFFF"

def get_live_price(ticker):
    try:
        t = yf.Ticker(ticker)
        price = t.fast_info.get('last_price')
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
    driver = setup_driver()
    try:
        for ticker in TICKERS:
            clean_ticker = ticker.replace('^', '')
            print(f"Processing {clean_ticker}...")
            
            # 1. Capture 7D Chart
            driver.get(f"https://mztrading.netlify.app/options/analyze/{clean_ticker}?dgextab=GEX&expiry=7")
            time.sleep(15) # Allow animations
            full_path = f"full_{clean_ticker}.png"
            driver.save_screenshot(full_path)
            img = Image.open(full_path).crop((450, 180, 1500, 950))
            crop_path = f"{clean_ticker}_final.png"
            img.save(crop_path)
            with open(crop_path, "rb") as f:
                b64_image = base64.b64encode(f.read()).decode('utf-8')

            # 2. Capture 30D Data (Hardened for missing strikes)
            driver.get(f"https://mztrading.netlify.app/options/analyze/{clean_ticker}?dgextab=GEX&dte=30&showHeatmap=true")
            
            # WAIT UNTIL DATA IS ACTUALLY IN THE CELLS
            try:
                WebDriverWait(driver, 20).until(
                    lambda d: d.execute_script("return document.querySelector('tr td') && document.querySelector('tr td').innerText.trim().length > 0")
                )
            except:
                print(f"Timeout waiting for data for {clean_ticker}")
                continue

            values_table, colors_table = [], []
            rows = driver.find_elements(By.TAG_NAME, "tr")
            for row in rows:
                cells = row.find_elements(By.CSS_SELECTOR, "td, th")
                if not cells: continue
                
                # Using InnerText mapping is essential for 'sticky' strike columns
                v_row = [driver.execute_script("return arguments[0].innerText;", c).strip() for c in cells]
                c_row = [rgb_to_hex(driver.execute_script("return window.getComputedStyle(arguments[0]).backgroundColor;", c)) for c in cells]
                
                if v_row and any(v_row):
                    values_table.append(v_row)
                    colors_table.append(c_row)

            # 3. Sync
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
