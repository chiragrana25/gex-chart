import os
import asyncio
import base64
import datetime
import re
import requests
import yfinance as yf
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from playwright.async_api import async_playwright
from PIL import Image

# --- CONFIG
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

async def process_ticker(sel_driver, pw_browser, ticker):
    clean_ticker = ticker.replace('^', '')
    print(f"Processing {clean_ticker}...")

    try:
        # PHASE 1: SELENIUM CHART CAPTURE
        chart_url = f"https://mztrading.netlify.app/options/analyze/{clean_ticker}?dgextab=GEX&expiry=7"
        sel_driver.get(chart_url)
        await asyncio.sleep(15) 
        
        screenshot_path = f"full_{clean_ticker}.png"
        sel_driver.save_screenshot(screenshot_path)
        with Image.open(screenshot_path) as img:
            img.crop((450, 180, 1500, 950)).save(f"{clean_ticker}_final.png")
        
        with open(f"{clean_ticker}_final.png", "rb") as f:
            b64_image = base64.b64encode(f.read()).decode('utf-8')

        # PHASE 2: PLAYWRIGHT 30D HEATMAP DATA
        page = await pw_browser.new_page()
        data_url = f"https://mztrading.netlify.app/options/analyze/{clean_ticker}?dgextab=GEX&dte=30&showHeatmap=true"
        
        # Increased timeout and switched to domcontentloaded for heavy NVDA/QQQ loads
        await page.goto(data_url, wait_until="domcontentloaded", timeout=90000)

        print(f"  Hydrating data for {clean_ticker}...")
        await page.wait_for_function("""() => {
            const cells = document.querySelectorAll('tr td');
            return cells.length > 30 && /[0-9]/.test(cells[10].innerText);
        }""", timeout=120000)

        table_data = await page.evaluate("""() => {
            const rows = Array.from(document.querySelectorAll('tr'));
            return rows.filter(r => r.querySelector('td')).map(r => {
                const cells = Array.from(r.querySelectorAll('td, th'));
                return {
                    values: cells.map(c => c.innerText.trim()),
                    colors: cells.map(c => window.getComputedStyle(c).backgroundColor)
                };
            });
        }""")
        await page.close()

        values_table = [row['values'] for row in table_data]
        colors_table = [[rgb_to_hex(c) for c in row['colors']] for row in table_data]

        # PHASE 3: DISPATCH
        try:
            price_val = yf.Ticker(ticker).fast_info.get('last_price')
            price = f"{price_val:.2f}" if price_val else "N/A"
        except:
            price = "N/A"

        payload = {
            "ticker": clean_ticker, "values": values_table, "colors": colors_table,
            "imageData": b64_image, "price": price,
            "updated": (datetime.datetime.now() - datetime.timedelta(hours=4)).strftime("%I:%M %p")
        }
        
        requests.post(WEBAPP_URL, json=payload, timeout=60)
        print(f"  Success: {clean_ticker} synced.")

    except Exception as e:
        print(f"  Failed {clean_ticker}: {e}")

async def main():
    if not WEBAPP_URL: return print("WEBAPP_URL Missing")
    sel_driver = setup_selenium()
    async with async_playwright() as p:
        pw_browser = await p.chromium.launch(headless=True)
        for ticker in TICKERS:
            await process_ticker(sel_driver, pw_browser, ticker)
        await pw_browser.close()
    sel_driver.quit()

if __name__ == "__main__":
    asyncio.run(main())
