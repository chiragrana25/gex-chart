import os
import time
import requests
import base64
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from PIL import Image # Add 'Pillow' to your pip install list

WEBAPP_URL = os.environ.get('WEBAPP_URL')
TICKERS = ['NVDA', 'TSLA']

def setup_driver():
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1200,1600') # Tall window to capture chart + table
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def main():
    driver = setup_driver()
    try:
        for ticker in TICKERS:
            print(f"Processing {ticker}...")
            driver.get(f"https://mztrading.netlify.app/options/analyze/{ticker}?expiry=7")
            
            # Static wait since we know the site works but Selenium is being finicky with detection
            time.sleep(12) 
            
            # Save the full page
            full_path = f"full_{ticker}.png"
            driver.save_screenshot(full_path)
            
            # CROP THE IMAGE (Top 700 pixels usually covers the chart on this site)
            # This ensures we always have an image to send even if selectors fail
            img = Image.open(full_path)
            chart_img = img.crop((0, 150, 1000, 850)) # (left, top, right, bottom)
            crop_path = f"{ticker}_cropped.png"
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
