import re
import random
import trafilatura
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
]

def scrape_heavy_article(url):
    """
    Advanced Scraper: Uses Trafilatura for lightning-fast parsing. 
    If blocked by Cloudflare, falls back to Playwright Stealth.
    """
    print(f"Scraping: {url}")
    
    # 1. TRAFILATURA (Primary: Fast & Accurate)
    try:
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            text = trafilatura.extract(downloaded, include_comments=False, include_tables=False)
            if text and len(text) > 100:
                print("   -> (Trafilatura Success)")
                return text.strip()
    except Exception as e:
        pass # Fallback to Playwright
        
    # 2. PLAYWRIGHT (Fallback: Stealth for Cloudflare/WAF)
    text_content = ""
    try:
        print("   -> Trafilatura blocked. Falling back to Playwright Stealth...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=random.choice(USER_AGENTS),
                viewport={"width": 1920, "height": 1080},
                java_script_enabled=True,
                bypass_csp=True
            )
            context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            page = context.new_page()
            
            try:
                page.goto(url, timeout=25000, wait_until="domcontentloaded")
                page.wait_for_timeout(2000)
            except Exception:
                pass

            html = page.content()
            browser.close()

            soup = BeautifulSoup(html, "html.parser")
            for junk in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'iframe', 'button']):
                junk.decompose()
                
            paragraphs = soup.find_all('p')
            raw_text = "\n".join([p.get_text().strip() for p in paragraphs if len(p.get_text().strip()) > 20])
            
            if len(raw_text) < 200:
                body = soup.find('body')
                if body: raw_text = body.get_text(separator=' ', strip=True)

            text_content = re.sub(r'\s+', ' ', raw_text).strip()
            
    except Exception as e:
        print(f"   -> Playwright crashed: {e}")

    return text_content
