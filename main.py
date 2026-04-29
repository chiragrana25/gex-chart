import os, asyncio, base64, datetime, re, requests, time
import yfinance as yf
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from playwright.sync_api import sync_playwright
from PIL import Image

# --- CONFIG ---
WEBAPP_URL = os.environ.get('WEBAPP_URL')
TICKERS = ['NVDA']

def rgb_to_hex(rgb_str):
    try:
        nums = re.findall(r'\d+', rgb_str)
        if len(nums) >= 3:
            return '#{:02x}{:02x}{:02x}'.format(int(nums[0]), int(nums[1]), int(nums[2]))
        return "#FFFFFF"
    except: return "#FFFFFF"

def setup_selenium():
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def main():
    if not WEBAPP_URL: return print("WEBAPP_URL missing")
    sel_driver = setup_selenium()
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Using a desktop User Agent helps prevent the site from defaulting to mobile layouts
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )

        for ticker in TICKERS:
            clean_ticker = ticker.replace('^', '')
            print(f"[{clean_ticker}] Starting Sync...")

            try:
                # PHASE 1: SELENIUM FOR CHART IMAGE
                chart_url = f"https://mztrading.netlify.app/options/analyze/{clean_ticker}?dgextab=GEX&expiry=7"
                sel_driver.get(chart_url)
                time.sleep(15) 
                screenshot = f"full_{clean_ticker}.png"
                sel_driver.save_screenshot(screenshot)
                with Image.open(screenshot) as img:
                    img.crop((550, 180, 1650, 950)).save(f"{clean_ticker}_final.png")
                with open(f"{clean_ticker}_final.png", "rb") as f:
                    b64_image = base64.b64encode(f.read()).decode('utf-8')

                # PHASE 2: PLAYWRIGHT FOR DATA (URL DRIVEN)
                page = context.new_page()
                # Switched back to URL parameters. Using both expiry and dte to force the view.
                data_url = f"https://mztrading.netlify.app/options/analyze/{clean_ticker}?dgextab=GEX&expiry=30&dte=30&showHeatmap=true"
                
                page.goto(data_url, wait_until="domcontentloaded", timeout=90000)
                
                # HYDRATION LOCK: This is the most important line. 
                # It waits until there are >20 cells AND cell 10 contains a number.
                print(f"  [{clean_ticker}] Waiting for table hydration...")
                page.wait_for_function("""() => {
                    const cells = document.querySelectorAll('td');
                    return cells.length > 20 && /[0-9]/.test(cells[10].innerText);
                }""", timeout=60000)
                
                # Small buffer to ensure the site finishes rendering background colors
                time.sleep(3) 

                rows = page.query_selector_all("tr")
                values_table, colors_table = [], []
                for row in rows:
                    cells = row.query_selector_all("td, th")
                    if not cells: continue
                    
                    # Capture text and colors
                    v_row = [c.evaluate("el => el.innerText").strip() for c in cells]
                    if v_row and any(v_row):
                        values_table.append(v_row)
                        c_row = [rgb_to_hex(c.evaluate("el => window.getComputedStyle(el).backgroundColor")) for c in cells]
                        colors_table.append(c_row)
                
                page.close()

                # PHASE 3: DISPATCH
                price_val = yf.Ticker(ticker).fast_info.get('last_price', 'N/A')
# Change the label from "updated" to "GEX SYNC"
                payload = {
                    "ticker": clean_ticker, 
                    "values": values_table, 
                    "colors": colors_table,
                    "imageData": b64_image, 
                    "price": f"{price_val:.2f}" if price_val != 'N/A' else 'N/A',
                    "gex_sync": (datetime.datetime.now() - datetime.timedelta(hours=4)).strftime("%I:%M %p")
        }
                requests.post(WEBAPP_URL, json=payload, timeout=60)
                print(f"  Success: {clean_ticker} synced.")

            except Exception as e:
                print(f"  Failed {clean_ticker}: {e}")

        browser.close()
    sel_driver.quit()

if __name__ == "__main__":
    main()
