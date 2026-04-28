import os
import time
import requests
import base64
import datetime
import yfinance as yf
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from PIL import Image

# --- CONFIGURATION ---
WEBAPP_URL = os.environ.get('WEBAPP_URL')
#TICKERS = ["SPX", "SPY", "QQQ", "MU","NVDA", "SNDK", "AAOI", "TSLA", "NBIS", "CRWV", "AMD", "PANW", "ASTS", "UNH"] 
TICKERS = ["SPY"] 
EXPIRY = '7'
DTE = '30'

def setup_driver():
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1600,1200') 
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def get_live_price(ticker):
    try:
        stock = yf.Ticker(ticker)
        return f"{stock.fast_info['last_price']:.2f}"
    except: return "N/A"

def rgb_to_hex(rgb_str):
    if not rgb_str or 'rgba(0, 0, 0, 0)' in rgb_str or 'transparent' in rgb_str:
        return "#FFFFFF"
    try:
        # Extracts numbers from "rgb(1, 2, 3)" or "rgba(1, 2, 3, 1)"
        nums = [int(x) for x in rgb_str.replace('rgb', '').replace('a', '').replace('(', '').replace(')', '').split(',')[:3]]
        return '#{:02x}{:02x}{:02x}'.format(*nums)
    except: return "#FFFFFF"

def main():
    if not WEBAPP_URL:
        print("CRITICAL: WEBAPP_URL secret is missing!")
        return

    driver = setup_driver()
    try:
        for ticker in TICKERS:
            print(f"Processing {ticker}...")
            # 1. Capture Chart (7-Day)
            chart_url = f"https://mztrading.netlify.app/options/analyze/{ticker}?dgextab=GEX&expiry={EXPIRY}"
            driver.get(chart_url)
            time.sleep(15) 
            
            full_path = f"full_{ticker}.png"
            driver.save_screenshot(full_path)
            img = Image.open(full_path)
            chart_img = img.crop((450, 180, 1500, 950)) 
            crop_path = f"{ticker}_final.png"
            chart_img.save(crop_path)
            
            with open(crop_path, "rb") as img_file:
                b64_image = base64.b64encode(img_file.read()).decode('utf-8')

            # 2. Capture Data (30-Day Heatmap)
            data_url = f"https://mztrading.netlify.app/options/analyze/{ticker}?dgextab=GEX&dte={DTE}&showHeatmap=true"
            driver.get(data_url)
            time.sleep(10) # Essential wait for sticky columns to hydrate

            values_table = []
            colors_table = []
            
            # Re-implementing your working extraction logic for Selenium
            rows = driver.find_elements(By.TAG_NAME, "tr")
            for row in rows:
                cells = row.find_elements(By.CSS_SELECTOR, "td, th")
                if not cells: continue
                
                # 'execute_script' is Selenium's equivalent to Playwright's 'evaluate'
                v_row = [driver.execute_script("return arguments[0].innerText;", c).strip() for c in cells]
                
                if v_row and any(v_row):
                    values_table.append(v_row)
                    # Catch the background color for heatmap
                    bg_color = [driver.execute_script("return window.getComputedStyle(arguments[0]).backgroundColor;", c) for c in cells]
                    colors_table.append([rgb_to_hex(color) for color in bg_color])

            # 3. Sync
            now_est = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=4)).strftime("%I:%M %p")
            payload = {
                "ticker": ticker,
                "price": get_live_price(ticker),
                "updated": now_est,
                "values": values_table,
                "colors": colors_table,
                "imageData": b64_image
            }

            res = requests.post(WEBAPP_URL, json=payload, timeout=60)
            print(f"Sync {ticker}: {res.text}")
                
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
