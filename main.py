import os, asyncio, base64, datetime, re, requests, time
import yfinance as yf
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from playwright.sync_api import sync_playwright
from PIL import Image

# --- CONFIG ---
WEBAPP_URL = os.environ.get('WEBAPP_URL')
TICKERS = ['^SPX', 'SPY', 'QQQ', 'NVDA', 'TSLA', 'AAPL', 'AMD', 'MU', 'MSFT', 'UNH', 
           'SNDK', 'CRWV', 'NBIS', 'AAOI', 'ASTS', 'RDDT', 'ALAB', 'PANW']

def rgb_to_hex(rgb_str):
    try:
        nums = re.findall(r'\d+', rgb_str)
        if len(nums) >= 3:
            return '#{:02x}{:02x}{:02x}'.format(int(nums[0]), int(nums[1]), int(nums[2]))
        return "#FFFFFF"
    except: return "#FFFFFF"

def get_live_price(ticker):
    try:
        t = yf.Ticker(ticker)
        price = t.fast_info.get('last_price') or t.fast_info.get('lastPrice')
        return f"{price:.2f}" if price else "N/A"
    except: return "N/A"

def capture_chart(ticker):
    """Phase 1: Selenium for Chart Image"""
    clean_ticker = ticker.replace('^', '')
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    try:
        url = f"https://mztrading.netlify.app/options/analyze/{clean_ticker}?dgextab=GEX&expiry=7"
        driver.get(url)
        # Wait for Highcharts to render
        try:
            WebDriverWait(driver, 25).until(EC.visibility_of_element_located((By.CLASS_NAME, "highcharts-container")))
        except:
            time.sleep(10)
        
        path = f"full_{clean_ticker}.png"
        driver.save_screenshot(path)
        # Expanded crop to 1850 for the right side
        with Image.open(path) as img:
            img.crop((450, 180, 1850, 950)).save(f"{clean_ticker}_final.png")
        with open(f"{clean_ticker}_final.png", "rb") as f:
            return base64.b64encode(f.read()).decode('utf-8')
    finally:
        driver.quit()

def scrape_ticker(context, ticker):
    """Phase 2: Playwright for Heatmap Data"""
    clean_ticker = ticker.replace('^', '')
    data_url = f"https://mztrading.netlify.app/options/analyze/{clean_ticker}?dgextab=GEX&expiry=30&dte=30&showHeatmap=true"
    
    # Isolation: Fresh page for every ticker to prevent RDDT/TSLA memory leaks
    page = context.new_page()
    print(f"[{clean_ticker}] Starting Sync...")
    
    chart_b64 = capture_chart(ticker)
    price = get_live_price(ticker)

    try:
        # Increase navigation timeout for slow Netlify responses
        page.goto(data_url, wait_until="domcontentloaded", timeout=120000)
        
        # INCREASED HYDRATION TIMEOUT: 120s for SPY/QQQ
        print(f"  [{clean_ticker}] Waiting for table hydration (Max 120s)...")
        page.wait_for_function("""() => {
            const cells = document.querySelectorAll('td');
            return cells.length > 20 && /[0-9]/.test(cells[10].innerText);
        }""", timeout=120000)
        
        time.sleep(5) # Colors/CSS settlement
        
        rows = page.query_selector_all("tr")
        values_table, colors_table = [], []
        for row in rows:
            cells = row.query_selector_all("td, th")
            if not cells: continue
            v_row = [c.evaluate("el => el.innerText").strip() for c in cells]
            if v_row and any(v_row):
                values_table.append(v_row)
                c_row = [rgb_to_hex(c.evaluate("el => window.getComputedStyle(el).backgroundColor")) for c in cells]
                colors_table.append(c_row)
        
        payload = {
            "ticker": clean_ticker, "values": values_table, "colors": colors_table,
            "imageData": chart_b64, "price": price,
            "gex_sync": (datetime.datetime.now() - datetime.timedelta(hours=4)).strftime("%I:%M %p")
        }
        
        resp = requests.post(WEBAPP_URL, json=payload, timeout=60)
        print(f"  Success: {clean_ticker} synced.")
    except Exception as e:
        print(f"  Failed {clean_ticker}: {e}")
    finally:
        page.close()

def main():
    if not WEBAPP_URL: return print("WEBAPP_URL missing")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36"
        )
        for ticker in TICKERS:
            scrape_ticker(context, ticker)
            time.sleep(2) # Memory clearing buffer
        browser.close()

if __name__ == "__main__":
    main()
