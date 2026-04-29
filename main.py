import os, time, datetime, requests, re, base64
import yfinance as yf
from playwright.sync_api import sync_playwright
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from PIL import Image

# --- CONFIG ---
SHEETS_BRIDGE_URL = os.environ.get('WEBAPP_URL')
TICKERS = ['SPY', 'QQQ', 'NVDA']

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
        # Using fast_info for 2026 yfinance compatibility
        price = t.fast_info.get('last_price') or t.fast_info.get('lastPrice')
        return f"{price:.2f}" if price else "N/A"
    except: return "N/A"

def capture_chart(ticker):
    """Keep Selenium for the 7D Chart capture as requested."""
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
        time.sleep(15) # Wait for chart animation
        path = f"full_{clean_ticker}.png"
        driver.save_screenshot(path)
        Image.open(path).crop((450, 180, 1500, 950)).save(f"{clean_ticker}_final.png")
        with open(f"{clean_ticker}_final.png", "rb") as f:
            return base64.b64encode(f.read()).decode('utf-8')
    finally:
        driver.quit()

def scrape_ticker(context, ticker):
    clean_ticker = ticker.replace('^', '')
    url = f"https://mztrading.netlify.app/options/analyze/{clean_ticker}?dgextab=GEX&dte=30&showHeatmap=true"
    page = context.new_page()
    print(f"[{clean_ticker}] Scraping Heatmap...")
    
    price = get_live_price(ticker)
    chart_b64 = capture_chart(ticker)
    
    try:
        # 1. Wait for network to quiet down
        page.goto(url, wait_until="networkidle", timeout=90000)
        
        # 2. HYDRATION LOCK: Wait specifically for data to appear in cells
        # This replaces the fixed time.sleep(5) with a logic-based wait
        print(f"[{clean_ticker}] Waiting for data hydration...")
        page.wait_for_function("""() => {
            const cells = document.querySelectorAll('td');
            return cells.length > 20 && /[0-9]/.test(cells[10].innerText);
        }""", timeout=60000)

        # 3. Final small buffer for color rendering
        time.sleep(2) 

        rows = page.query_selector_all("tr")
        values_table, colors_table = [], []

        for row in rows:
            cells = row.query_selector_all("td, th")
            if not cells: continue
            
            # evaluate(innerText) is the key to catching 'sticky' columns like Dates
            v_row = [c.evaluate("el => el.innerText").strip() for c in cells]
            
            if v_row and any(v_row):
                values_table.append(v_row)
                c_row = [rgb_to_hex(c.evaluate("el => window.getComputedStyle(el).backgroundColor")) for c in cells]
                colors_table.append(c_row)

        now_est = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=4)
        payload = {
            "ticker": clean_ticker, 
            "values": values_table, 
            "colors": colors_table,
            "imageData": chart_b64,
            "updated": now_est.strftime("%I:%M %p"), 
            "price": price
        }
        
        resp = requests.post(SHEETS_BRIDGE_URL, json=payload, timeout=60)
        print(f"[{clean_ticker}] Sync: {resp.text}")

    except Exception as e:
        print(f"[{clean_ticker}] Error: {e}")
    finally:
        page.close()

def run_main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        for ticker in TICKERS:
            scrape_ticker(context, ticker)
        browser.close()

if __name__ == "__main__":
    run_main()
