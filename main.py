import os
import time
import requests
import base64
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from PIL import Image

WEBAPP_URL = os.environ.get('WEBAPP_URL')
#TICKERS = ['NVDA']
TICKERS = ['SPX', 'SPY', 'QQQ', 'NVDA', 'MU', 'SNDK','TSLA', 'AAPL', 'AMD', 'CRWV', 'NBIS', 'MSFT', 'QCOM', 'AAOI', 'ASTS', 'RDDT', 'ALAB', 'ANET','MSTR', 'TEM' ]

def setup_driver():
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    # Use a wider window so the sidebar/filler doesn't push the chart out
    options.add_argument('--window-size=1600,1200') 
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def main():
    driver = setup_driver()
    try:
        for ticker in TICKERS:
            print(f"Processing {ticker}...")
            driver.get(f"https://mztrading.netlify.app/options/analyze/{ticker}?expiry=7&dgextab=GEX")
            
            # Wait for data to load and animations to settle
            time.sleep(15) 
            
            full_path = f"full_{ticker}.png"
            driver.save_screenshot(full_path)
            
            # --- TWEAK CROP COORDINATES HERE ---
            # (left, top, right, bottom)
            # Increased 'left' to 300 to cut off the sidebar/filler
            # Increased 'right' to 1300 to capture the full width of the chart
            left = 500   
            top = 180    
            right = 1450 
            bottom = 950 
            
            img = Image.open(full_path)
            chart_img = img.crop((left, top, right, bottom))
            
            crop_path = f"{ticker}_final.png"
            chart_img.save(crop_path)

            with open(crop_path, "rb") as img_file:
                b64_string = base64.b64encode(img_file.read()).decode('utf-8')

            payload = {"ticker": ticker, "imageData": b64_string}
            res = requests.post(WEBAPP_URL, json=payload, timeout=30)
            print(f"Uploaded {ticker}: {res.text}")
                
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
