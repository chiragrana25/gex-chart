import os, asyncio, base64, datetime, re, requests, time
import yfinance as yf
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from playwright.sync_api import sync_playwright
from PIL import Image

WEBAPP_URL = os.environ.get('WEBAPP_URL')
TICKERS = ['SPY', 'QQQ', 'NVDA']

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
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})

        for ticker in TICKERS:
            clean_ticker = ticker.replace('^', '')
            print(f"[{clean_ticker}] Processing...")

            try:
                # PHASE 1: SELENIUM FOR CHART
                chart_url = f"https://mztrading.netlify.app/options/analyze/{clean_ticker}?dgextab=GEX&expiry=7"
                sel_driver.get(chart_url)
                time.sleep(15) 
                screenshot = f"full_{clean_ticker}.png"
                sel_driver.save_screenshot(screenshot)
                with Image.open(screenshot) as img:
                    img.crop((450, 180, 1500, 950)).save(f"{clean_ticker}_final.png")
                with open(f"{clean_ticker}_final.png", "rb") as f:
                    b64_image = base64.b64encode(f.read()).decode('utf-8')

                # PHASE 2: PLAYWRIGHT FOR 30D DATA (Your Preferred Logic)
                page = context.new_page()
                data_url = f"https://mztrading.netlify.app/options/analyze/{clean_ticker}?dgextab=GEX&dte=30&showHeatmap=true"
                
                # Navigate and wait for DOM
                page.goto(data_url, wait_until="domcontentloaded", timeout=90000)
                
                # Deep Hydration Check: Ensures numbers are in cells before scraping
                page.wait_for_function("""() => {
                    const cells = document.querySelectorAll('td');
                    return cells.length > 20 && /[0-9]/.test(cells[10].innerText);
                }""", timeout=60000)
                
                time.sleep(5) # Final safety buffer

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
