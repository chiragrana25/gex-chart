import os
import time
import requests
import base64
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

WEBAPP_URL = os.environ.get('WEBAPP_URL')

def setup_driver():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def update_sheet_with_image(ticker, image_path):
    # Convert image to Base64 string
    with open(image_path, "rb") as img_file:
        b64_string = base64.b64encode(img_file.read()).decode('utf-8')

    payload = {
        "ticker": ticker,
        "status": "Chart Captured",
        "imageData": b64_string,
        "mimeType": "image/png"
    }
    
    response = requests.post(WEBAPP_URL, json=payload)
    print(f"Uploaded {ticker}: {response.text}")

def main():
    driver = setup_driver()
    tickers = ['NVDA', 'AAPL'] # Add yours
    
    try:
        for ticker in tickers:
            driver.get(f"https://mztrading.netlify.app/options/analyze/{ticker}?expiry=7")
            time.sleep(10) # Give the chart plenty of time to render
            
            # Find the chart element and save it
            try:
                # 'recharts-wrapper' is the container for the charts on that site
                chart = driver.find_element(By.CLASS_NAME, "recharts-wrapper")
                path = f"{ticker}.png"
                chart.screenshot(path)
                
                update_sheet_with_image(ticker, path)
            except Exception as e:
                print(f"Failed to capture {ticker}: {e}")
                
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
