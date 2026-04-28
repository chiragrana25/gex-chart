import os
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import json

# --- CONFIGURATION ---
TICKERS = ['NVDA', 'AAPL', 'TSLA', 'AMD'] # Add your tickers here
EXPIRY = '7'
SHEET_NAME = "Options Analysis Log"

def setup_driver():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver

def update_google_sheets(ticker):
    # Retrieve credentials from Environment Variable (for GitHub Secrets)
    creds_dict = json.loads(os.environ['G_SHEETS_CREDS'])
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_key_file_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    
    try:
        sheet = client.open(SHEET_NAME).sheet1
        # Logging the refresh time
        sheet.append_row([ticker, "Refreshed", time.strftime("%Y-%m-%d %H:%M:%S")])
    except Exception as e:
        print(f"Error updating sheet: {e}")

def main():
    driver = setup_driver()
    try:
        for ticker in TICKERS:
            url = f"https://mztrading.netlify.app/options/analyze/{ticker}?expiry={EXPIRY}"
            driver.get(url)
            time.sleep(8) # Allow extra time for chart rendering on CI/CD
            update_google_sheets(ticker)
            print(f"Processed {ticker}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
