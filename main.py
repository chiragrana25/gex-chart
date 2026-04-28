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

WEBAPP_URL = os.environ.get('WEBAPP_URL')
TICKERS = ['NVDA', 'TSLA', 'AAPL', 'AMD']

def setup_driver():
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    # Use a very specific, modern User-Agent
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def main():
    if not WEBAPP_URL:
        print("WEBAPP_URL missing")
        return

    driver = setup_driver()
    # Stealth mode: hide Selenium fingerprint
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    try:
        for ticker in TICKERS:
            print(f"Processing {ticker}...")
            driver.get(f"https://mztrading.netlify.app/options/analyze/{ticker}?expiry=7")
            
            wait = WebDriverWait(driver, 30)
            
            try:
                # Wait for the main container to load first
                wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                
                # Wait for the SVG (the chart)
                chart_element = wait.until(EC.visibility_of_element_located((By.TAG_NAME, "svg")))
                
                time.sleep(7) # Extra buffer for animations
                
                path = f"{ticker}.png"
                chart_element.screenshot(path)
                
                with open(path, "rb") as img_file:
                    b64_string = base64.b64encode(img_file.read()).decode('utf-8')

                payload = {"ticker": ticker, "imageData": b64_string}
                requests.post(WEBAPP_URL, json=payload, timeout=30)
                print(f"Uploaded {ticker}")

            except Exception as e:
                # DIAGNOSTIC: Save a screenshot of what the bot actually sees
                error_path = f"ERROR_{ticker}.png"
                driver.save_screenshot(error_path)
                print(f"Failed {ticker}. Saved diagnostic screenshot to {error_path}. Error: {e}")
                
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
