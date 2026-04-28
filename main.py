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

def setup_driver():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    # Set a custom user agent so the site treats the bot like a real browser
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def update_sheet_with_image(ticker, image_path):
    with open(image_path, "rb") as img_file:
        b64_string = base64.b64encode(img_file.read()).decode('utf-8')

    payload = {
        "ticker": ticker,
        "status": "Chart Captured",
        "imageData": b64_string,
        "mimeType": "image/png"
    }
    
    try:
        response = requests.post(WEBAPP_URL, json=payload, timeout=30)
        print(f"Uploaded {ticker}: {response.text}")
    except Exception as e:
        print(f"Failed to send to Google Sheets: {e}")

def main():
    driver = setup_driver()
    tickers = ['NVDA'] # Add more tickers here
    
    try:
        for ticker in tickers:
            print(f"Analyzing {ticker}...")
            driver.get(f"https://mztrading.netlify.app/options/analyze/{ticker}?expiry=7")
            
            # Use Explicit Wait for up to 30 seconds
            wait = WebDriverWait(driver, 30)
            try:
                # 1. Wait for the chart container to exist in the DOM
                # 2. Wait for it to be visible on screen
                chart_element = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "recharts-wrapper")))
                
                # Give it an extra 2 seconds to ensure the animations are finished
                time.sleep(2) 
                
                path = f"{ticker}.png"
                chart_element.screenshot(path)
                update_sheet_with_image(ticker, path)
                
            except Exception as e:
                print(f"Could not find chart for {ticker}. The site might be slow or the selector changed. Error: {e}")
                
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
