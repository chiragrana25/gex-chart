import os, time, requests, base64, datetime, re
import yfinance as yf
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from PIL import Image

# --- CONFIGURATION ---
WEBAPP_URL = os.environ.get('WEBAPP_URL')
TICKERS = ['SPY', 'QQQ', 'NVDA']

def rgb_to_hex(rgb_str):
    try:
        nums = re.findall(r'\d+', rgb_str)
        if len(nums) >= 3:
            return '#{:02x}{:02x}{:02x}'.format(int(nums[0]), int(nums[1]), int(nums[2]))
        return "#FFFFFF"
    except: return "#FFFFFF"

def setup_driver():
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def main():
    if not WEBAPP_URL:
        print("CRITICAL: WEBAPP_URL secret is missing!")
        return

    driver = setup_driver()
    try:
        for ticker in TICKERS:
            clean_ticker = ticker.replace('^', '')
            print(f"Processing {clean_ticker}...")
            
            # PHASE 1: Chart Capture
            driver.get(f"https://mztrading.netlify.app/options/analyze/{clean_ticker}?dgextab=GEX&expiry=7")
            time.sleep(15) 
            full_path = f"full_{clean_ticker}.png"
            driver.save_screenshot(full_path)
            Image.open(full_path).crop((450, 180, 1500, 950)).save(f"{clean_ticker}_final.png")
            with open(f"{clean_ticker}_final.png", "rb") as f:
                b64_image = base64.b64encode(f.read()).decode('utf-8')

            # PHASE 2: Heatmap Extraction (Forced 30D DTE)
            driver.get(f"https://mztrading.netlify.app/options/analyze/{clean_ticker}?dgextab=GEX&dte=30&showHeatmap=true")
            
            data_ready = False
            for attempt in range(3):
                try:
                    # Logic: Wait for > 15 rows and numeric text in cell 5
                    WebDriverWait(driver, 45).until(lambda d: d.execute_script(
                        "let r = document.querySelectorAll('tr');"
                        "let c = document.querySelectorAll('tr td');"
                        "return r.length > 15 && c.length > 10 && c[5].innerText.trim().match(/[0-9]/);"
                    ))
                    data_ready = True
                    break
                except:
                    print(f"  Attempt {attempt+1}: {clean_ticker} blank, refreshing...")
                    driver.refresh()
                    time.sleep(12)

            if not data_ready:
                print(f"  Skipping {clean_ticker}: Table failed to hydrate.")
                continue

            # PHASE 3: Extraction
            values_table, colors_table = [], []
            rows = driver.find_elements(By.TAG_NAME, "tr")
            for row in rows:
                cells = row.find_elements(By.CSS_SELECTOR, "td, th")
                if not cells: continue
                
                v_row = [driver.execute_script("return arguments[0].innerText;", c).strip() for c in cells]
                c_row = [rgb_to_hex(driver.execute_script("return window.getComputedStyle(arguments[0]).backgroundColor;", c)) for c in cells]
                
                if v_row and any(v_row):
                    values_table.append(v_row)
                    colors_table.append(c_row)

            # PHASE 4: Sync
            try:
                price = yf.Ticker(ticker).fast_info.get('last_price', 'N/A')
                payload = {
                    "ticker": clean_ticker, "values": values_table, "colors": colors_table,
                    "imageData": b64_image, "price": f"{price:.2f}" if price != 'N/A' else 'N/A',
                    "updated": (datetime.datetime.now() - datetime.timedelta(hours=4)).strftime("%I:%M %p")
                }
                requests.post(WEBAPP_URL, json=payload, timeout=60)
                print(f"  Success: {clean_ticker} synced.")
            except Exception as e:
                print(f"  Sync Error for {clean_ticker}: {e}")
                
    except Exception as e:
        print(f"FATAL ERROR: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
