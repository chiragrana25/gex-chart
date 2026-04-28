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
from PIL import Image

# --- CONFIGURATION ---
WEBAPP_URL = os.environ.get('WEBAPP_URL')
TICKERS = ['SPY', 'QQQ', 'NVDA', 'TSLA', 'AAPL', 'AMD', 'MU', 'MSFT'] 
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

def main():
    if not WEBAPP_URL:
        print("CRITICAL: WEBAPP_URL secret is missing!")
        return

    driver = setup_driver()
    try:
        for ticker in TICKERS:
            print(f"Processing {ticker}...")
            # 1. URLS
            chart_url = f"https://mztrading.netlify.app/options/analyze/{ticker}?dgextab=GEX&expiry={EXPIRY}"
            data_url = f"https://mztrading.netlify.app/options/analyze/{ticker}?dgextab=GEX&dte={DTE}&showHeatmap=true"
            
            # 2. CAPTURE CHART IMAGE
            driver.get(chart_url)
            time.sleep(15) # Wait for animation
            full_path = f"full_{ticker}.png"
            driver.save_screenshot(full_path)
            
            # Crop Chart
            img = Image.open(full_path)
            chart_img = img.crop((450, 180, 1500, 950)) 
            crop_path = f"{ticker}_final.png"
            chart_img.save(crop_path)
            
            with open(crop_path, "rb") as img_file:
                b64_image = base64.b64encode(img_file.read()).decode('utf-8')

            # 3. SCRAPE TABLE DATA
            driver.get(data_url)
            time.sleep(8) # Wait for table hydration
            
            # Using execute_script to pull the clean text from every cell (fixes missing dates)
            values_table = driver.execute_script("""
                return Array.from(document.querySelectorAll('tr')).map(row => 
                    Array.from(row.querySelectorAll('td, th')).map(cell => cell.innerText.trim())
                ).filter(r => r.length > 0 && r[0] !== "");
            """)
            
            # Capture background colors for the heatmap
            colors_table = driver.execute_script("""
                return Array.from(document.querySelectorAll('tr')).map(row => 
                    Array.from(row.querySelectorAll('td, th')).map(cell => window.getComputedStyle(cell).backgroundColor)
                ).filter(r => r.length > 0);
            """)

            # 4. CONSTRUCT PAYLOAD
            now_est = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=4)).strftime("%I:%M %p")
            payload = {
                "ticker": ticker,
                "price": get_live_price(ticker),
                "updated": now_est,
                "values": values_table,
                "colors": colors_table,
                "imageData": b64_image
            }

            # 5. SEND TO GOOGLE
            res = requests.post(WEBAPP_URL, json=payload, timeout=60)
            print(f"Sync Result for {ticker}: {res.text}")
                
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
