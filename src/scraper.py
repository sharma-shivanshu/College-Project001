import re
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import random

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
]

def scrape_heavy_article(url):
    """
    Robust scraper using Playwright Stealth to bypass WAFs/Cloudflare across all news sites.
    """
    print(f"Scraping {url} with Playwright Stealth...")
    text_content = ""
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=random.choice(USER_AGENTS),
                viewport={"width": 1920, "height": 1080},
                java_script_enabled=True,
                bypass_csp=True
            )
            
            # Additional stealth scripts
            context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            page = context.new_page()
            
            # Anti-ban timeout and load strategy
            try:
                page.goto(url, timeout=25000, wait_until="domcontentloaded")
                # Wait briefly for JS to inject content
                page.wait_for_timeout(3000)
            except Exception as e:
                print(f"   -> Timeout or load error (ignored, attempting extraction): {e}")

            html = page.content()
            browser.close()

            # Universal extraction logic using BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")
            
            # Remove junk scripts, styles, nav, footers
            for junk in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'iframe', 'button']):
                junk.decompose()
                
            # Extract all paragraphs
            paragraphs = soup.find_all('p')
            raw_text = "\n".join([p.get_text().strip() for p in paragraphs if len(p.get_text().strip()) > 20])
            
            # Fallback if site doesn't use p tags well
            if len(raw_text) < 200:
                body = soup.find('body')
                if body:
                    raw_text = body.get_text(separator=' ', strip=True)

            text_content = re.sub(r'\s+', ' ', raw_text).strip()
            
    except Exception as e:
        print(f"   -> Scraper crashed: {e}")

    return text_content
