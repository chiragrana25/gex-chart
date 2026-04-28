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
            chart_url = f"https://mztrading.netlify.app/options/analyze/{ticker}?dgextab=GEX&expiry={EXPIRY}"
            data_url = f"https://mztrading.netlify.app/options/analyze/{ticker}?dgextab=GEX&dte={DTE}&showHeatmap=true"
            
            # --- PHASE 1: CAPTURE CHART ---
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

            # --- PHASE 2: SCRAPE DATA (WITH ASYNC DATE FIX) ---
            driver.get(data_url)
            
            # This JS block forces a wait for the first column's content
            result = driver.execute_script("""
                const waitLimit = 15000; 
                const start = Date.now();
                
                async function getData() {
                    // Poll until the first cell has a length > 0
                    while (Date.now() - start < waitLimit) {
                        const firstCell = document.querySelector('tr td, tr th');
                        if (firstCell && firstCell.innerText.trim().length > 0) break;
                        await new Promise(r => setTimeout(r, 1000));
                    }

                    const rows = Array.from(document.querySelectorAll('tr'));
                    
                    // Capture text values including sticky headers
                    const values = rows.map(row => 
                        Array.from(row.querySelectorAll('td, th')).map(cell => cell.innerText.trim())
                    ).filter(r => r.length > 0 && r[0] !== "");

                    // Capture background colors for heatmap
                    const colors = rows.map(row => 
                        Array.from(row.querySelectorAll('td, th')).map(cell => window.getComputedStyle(cell).backgroundColor)
                    ).filter(r => r.length > 0);

                    return { values, colors };
                }
                return getData();
            """)

            # --- PHASE 3: SYNC ---
            now_est = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=4)).strftime("%I:%M %p")
            payload = {
                "ticker": ticker,
                "price": get_live_price(ticker),
                "updated": now_est,
                "values": result['values'],
                "colors": result['colors'],
                "imageData": b64_image
            }

            res = requests.post(WEBAPP_URL, json=payload, timeout=60)
            print(f"Sync Result: {res.text}")
                
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
