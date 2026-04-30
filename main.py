import os, base64, time, requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from PIL import Image

WEBAPP_URL = os.environ.get('WEBAPP_URL')
TICKERS = ['^SPX', 'SPY', 'QQQ', 'NVDA', 'TSLA', 'AAPL', 'AMD', 'MU', 'MSFT', 'UNH', 
           'SNDK', 'CRWV', 'NBIS', 'AAOI', 'ASTS', 'RDDT', 'ALAB', 'PANW']

def capture_vision(ticker):
    clean_ticker = ticker.replace('^', '')
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--window-size=1920,1080')
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    try:
        driver.get(f"https://mztrading.netlify.app/options/analyze/{clean_ticker}?dgextab=GEX&expiry=7")
        WebDriverWait(driver, 30).until(EC.visibility_of_element_located((By.CLASS_NAME, "highcharts-container")))
        time.sleep(5) # Settle animations
        
        path = f"{clean_ticker}.png"
        driver.save_screenshot(path)
        with Image.open(path) as img:
            img.crop((450, 180, 1850, 950)).save(f"final_{clean_ticker}.png")
        
        with open(f"final_{clean_ticker}.png", "rb") as f:
            b64 = base64.b64encode(f.read()).decode('utf-8')
        
        requests.post(WEBAPP_URL, json={"type": "VISION_SYNC", "ticker": clean_ticker, "imageData": b64}, timeout=60)
        print(f"[{clean_ticker}] Vision Synced.")
    except Exception as e: print(f"[{clean_ticker}] Vision Error: {e}")
    finally: driver.quit()

for t in TICKERS: capture_vision(t)
