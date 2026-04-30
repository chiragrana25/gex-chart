import os, base64, time, requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from PIL import Image

# Config from GitHub Secrets
WEBAPP_URL = os.environ.get('WEBAPP_URL')
TICKERS = ['NVDA']

def capture_vision(ticker):
    clean_ticker = ticker.replace('^', '')
    print(f"[{clean_ticker}] Starting Vision Capture...")
    
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu') # Vital for GitHub Actions
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--remote-debugging-port=9222') # Helps prevent crash
    
    # Explicitly point to the Chrome binary location in GitHub Ubuntu runners
    options.binary_location = "/usr/bin/google-chrome"
    
    service = Service(ChromeDriverManager().install())
    
    try:
        driver = webdriver.Chrome(service=service, options=options)
        url = f"https://mztrading.netlify.app/options/analyze/{clean_ticker}?dgextab=GEX&expiry=7"
        
        # Increase the page load timeout for these heavy charts
        driver.set_page_load_timeout(60) 
        driver.get(url)
        
        # Wait for the actual chart container
        wait = WebDriverWait(driver, 45) # Increased wait time
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "highcharts-container")))
        
        time.sleep(8) # Extra time for the bars to animate in
        
        raw_path = f"raw_{clean_ticker}.png"
        driver.save_screenshot(raw_path)
        
        # CROP SETTINGS: (left, top, right, bottom)
        # 1850 on the right ensures we see the strike labels
        with Image.open(raw_path) as img:
            img.crop((450, 180, 1850, 950)).save(crop_path)
            
        with open(crop_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode('utf-8')
            
        payload = {
            "ticker": clean_ticker,
            "imageData": img_b64
        }
        
        # Send to the Vision-specific Apps Script URL
        response = requests.post(WEBAPP_URL, json=payload, timeout=60)
        print(f"  Result: {response.text}")
        
    except Exception as e:
        print(f"  Failed {clean_ticker}: {str(e)}")
    finally:
        driver.quit()

if __name__ == "__main__":
    if not WEBAPP_URL:
        print("CRITICAL: WEBAPP_URL secret is missing!")
    else:
        for ticker in TICKERS:
            capture_vision(ticker)
            time.sleep(2) # Prevent browser-thread congestion
