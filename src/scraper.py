import re
import random
import trafilatura
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
]

def clean_extracted_text(raw_text):
    # Remove javascript blobs, JSON arrays, and excessive whitespace
    raw_text = re.sub(r'\{.*?\}', '', raw_text)
    raw_text = re.sub(r'\[.*?\]', '', raw_text)
    raw_text = re.sub(r'function\s*\(.*?\)\s*\{.*?\}', '', raw_text)
    raw_text = re.sub(r'\s+', ' ', raw_text)
    return raw_text.strip()

def scrape_heavy_article(url):
    print(f"Scraping: {url}")
    text_content = ""
    
    # 1. TRAFILATURA 
    try:
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            text = trafilatura.extract(downloaded, include_comments=False, include_tables=False)
            if text and len(text) > 100:
                print("   -> (Trafilatura Success)")
                return clean_extracted_text(text)
    except Exception as e:
        pass 
        
    # 2. PLAYWRIGHT
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
            # Aggressively remove gibberish sources
            for junk in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'iframe', 'button', 'noscript', 'meta', 'link']):
                junk.decompose()
                
            paragraphs = soup.find_all('p')
            raw_text = "\n".join([p.get_text(separator=' ', strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 20])
            
            text_content = clean_extracted_text(raw_text)
    except Exception as e:
        print(f"   -> Playwright crashed: {e}")

    return text_content
