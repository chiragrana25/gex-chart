import os
import time
import requests
import base64
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# --- SETTINGS ---
WEBAPP_URL = os.environ.get('WEBAPP_URL')
TICKERS = ['NVDA', 'TSLA', 'AAPL', 'AMD'] 
EXPIRY = '7'

def setup_driver():
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1200')
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def main():
    if not WEBAPP_URL:
        print("CRITICAL ERROR: WEBAPP_URL secret is missing!")
        return

    driver = setup_driver()
    
    try:
        for ticker in TICKERS:
            print(f"Processing {ticker}...")
            url = f"https://mztrading.netlify.app/options/analyze/{ticker}?expiry={EXPIRY}"
            driver.get(url)
            
            wait = WebDriverWait(driver, 45)
            
            try:
                # Wait for the chart (SVG) to be visible
                chart_element = wait.until(EC.visibility_of_element_located((By.TAG_NAME, "svg")))
                
                # IMPORTANT: Sleep to allow Recharts animations to finish
                time.sleep(6) 
                
                # Capture screenshot of the chart element
                path = f"{ticker}.png"
                chart_element.screenshot(path)
                
                # Check file size for debugging
                file_size = os.path.getsize(path)
                print(f"Captured {ticker} ({file_size} bytes)")

                if file_size < 1000:
                    print(f"Warning: {ticker} image seems too small/empty.")

                # Encode to Base64
                with open(path, "rb") as img_file:
                    b64_string = base64.b64encode(img_file.read()).decode('utf-8')

                # Send to Google Apps Script
                payload = {
                    "ticker": ticker,
                    "imageData": b64_string
                }
                
                response = requests.post(WEBAPP_URL, json=payload, timeout=30)
                print(f"Response from Google: {response.text}")

            except Exception as e:
                print(f"Failed to capture {ticker}: {e}")
                
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
