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
from PIL import Image

# --- CONFIGURATION ---
WEBAPP_URL = os.environ.get('WEBAPP_URL')
TICKERS = ['SPX', 'SPY', 'QQQ', 'NVDA', 'MU', 'SNDK','TSLA', 'AAPL', 'AMD', 'CRWV', 'NBIS', 'MSFT', 'UNH', 'AAOI', 'ASTS', 'RDDT', 'ALAB', 'PANW', 'UNH'] 
#TICKERS = ['SPY'] 

def rgb_to_hex(rgb_str):
    if not rgb_str or 'rgba(0, 0, 0, 0)' in rgb_str or 'transparent' in rgb_str:
        return "#FFFFFF"
    try:
        # Extract numbers from "rgb(1, 2, 3)"
        nums = re.findall(r'\d+', rgb_str)
        if len(nums) >= 3:
            return '#{:02x}{:02x}{:02x}'.format(int(nums[0]), int(nums[1]), int(nums[2]))
        return "#FFFFFF"
    except: return "#FFFFFF"

def setup_driver():
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--window-size=1600,1200') 
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def main():
    driver = setup_driver()
    try:
        for ticker in TICKERS:
            print(f"Processing {ticker}...")
            
            # 1. Capture Chart
            driver.get(f"https://mztrading.netlify.app/options/analyze/{ticker}?dgextab=GEX&expiry=7")
            time.sleep(15) 
            full_path = f"full_{ticker}.png"
            driver.save_screenshot(full_path)
            img = Image.open(full_path).crop((450, 180, 1500, 950))
            crop_path = f"{ticker}_final.png"
            img.save(crop_path)
            with open(crop_path, "rb") as f:
                b64_image = base64.b64encode(f.read()).decode('utf-8')

            # 2. Capture Data & Colors (Heatmap Fix)
            driver.get(f"https://mztrading.netlify.app/options/analyze/{ticker}?dgextab=GEX&dte=30&showHeatmap=true")
            time.sleep(10)
            
            values_table, colors_table = [], []
            rows = driver.find_elements(By.TAG_NAME, "tr")
            for row in rows:
                cells = row.find_elements(By.CSS_SELECTOR, "td, th")
                if not cells: continue
                
                # Capture Text (Dates included)
                v_row = [driver.execute_script("return arguments[0].innerText;", c).strip() for c in cells]
                # Capture and Convert Colors
                c_row = [rgb_to_hex(driver.execute_script("return window.getComputedStyle(arguments[0]).backgroundColor;", c)) for c in cells]
                
                if v_row and any(v_row):
                    values_table.append(v_row)
                    colors_table.append(c_row)

            # 3. Sync
            payload = {
                "ticker": ticker,
                "values": values_table,
                "colors": colors_table, # Now sending HEX colors
                "imageData": b64_image,
                "price": yf.Ticker(ticker).fast_info['last_price'] if ticker != "^SPX" else "N/A",
                "updated": (datetime.datetime.now() - datetime.timedelta(hours=4)).strftime("%I:%M %p")
            }
            requests.post(WEBAPP_URL, json=payload, timeout=60)
                
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
