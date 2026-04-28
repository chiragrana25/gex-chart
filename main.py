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
    options.add_argument('--headless=new') # Uses the newer, more stable headless mode
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def main():
    driver = setup_driver()
    tickers = ['NVDA', 'TSLA'] # Updated list
    
    try:
        for ticker in tickers:
            print(f"Attempting to capture {ticker}...")
            url = f"https://mztrading.netlify.app/options/analyze/{ticker}?expiry=7"
            driver.get(url)
            
            # 1. Increase wait time to 45s for slow API responses
            wait = WebDriverWait(driver, 45)
            
            try:
                # 2. Wait for ANY SVG element (Recharts uses SVGs for its charts)
                # This is more reliable than a class name that might change
                wait.until(EC.presence_of_element_located((By.TAG_NAME, "svg")))
                
                # 3. Scroll to the bottom and back up to force rendering
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                driver.execute_script("window.scrollTo(0, 0);")
                
                # 4. Try finding the chart wrapper or the main content container
                # We'll take a screenshot of the main 'main' tag if specific wrapper fails
                try:
                    target = driver.find_element(By.CLASS_NAME, "recharts-wrapper")
                except:
                    target = driver.find_element(By.TAG_NAME, "main")
                
                path = f"{ticker}.png"
                target.screenshot(path)
                
                # Upload logic
                with open(path, "rb") as img_file:
                    b64_string = base64.b64encode(img_file.read()).decode('utf-8')
                
                payload = {"ticker": ticker, "status": "Success", "imageData": b64_string}
                requests.post(WEBAPP_URL, json=payload, timeout=30)
                print(f"Successfully processed {ticker}")
                
            except Exception as e:
                # 5. Diagnostic: Take a full page screenshot if it fails to help you see what went wrong
                driver.save_screenshot(f"ERROR_{ticker}.png")
                print(f"Failed {ticker}. Check ERROR_{ticker}.png in artifacts. Error: {e}")
                
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
