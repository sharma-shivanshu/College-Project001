import os
import json
import time
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync

def scrape_dainik_bhaskar(url):
    print(f"Scraping {url} with Playwright Stealth...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        stealth_sync(page)
        
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            time.sleep(3) # Wait for JS checks
            html = page.content()
            soup = BeautifulSoup(html, 'html.parser')
            # Extract main article body (adjust selector as needed for Dainik Bhaskar)
            article_div = soup.find('div', class_='story-details')
            text = article_div.get_text(separator=' ', strip=True) if article_div else soup.get_text(strip=True)
            return text
        except Exception as e:
            print(f"Failed to scrape {url}: {e}")
            return None
        finally:
            browser.close()

if __name__ == "__main__":
    # Test execution
    pass
