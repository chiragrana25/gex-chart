import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# --- CONFIGURATION ---
TICKERS = ['NVDA']
EXPIRY = '7'
# Paste your Web App URL into a GitHub Secret named WEBAPP_URL
WEBAPP_URL = os.environ.get('WEBAPP_URL')

def setup_driver():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver

def update_sheet_via_webapp(ticker, status):
    payload = {"ticker": ticker, "status": status}
    response = requests.post(WEBAPP_URL, json=payload)
    print(f"Update for {ticker}: {response.text}")

def main():
    driver = setup_driver()
    try:
        for ticker in TICKERS:
            url = f"https://mztrading.netlify.app/options/analyze/{ticker}?expiry={EXPIRY}"
            driver.get(url)
            time.sleep(5) # Wait for chart
            
            # Here we just log the status. 
            # If you want to send the actual image, you'd need to upload it 
            # to a host first and send the URL to the WebApp.
            update_sheet_via_webapp(ticker, "Chart Scanned")
            
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
