import re
import random
import trafilatura
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from htmldate import find_date

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
]

def extract_publish_date(html_content, url):
    """
    Uses htmldate (a dedicated library) to extract the real publish date from
    the article's HTML metadata — <meta property="article:published_time">,
    JSON-LD schema, byline, etc. Far more reliable than guessing from the URL.
    Returns a 'YYYY-MM-DD' string or None.
    """
    try:
        date = find_date(html_content, outputformat="%Y-%m-%d", extensive_search=True)
        return date
    except Exception:
        pass

    # Fallback: try to extract from URL pattern (e.g. -2026-09-19 at the end)
    url_date_match = re.search(r'(\d{4}-\d{2}-\d{2})', url)
    if url_date_match:
        return url_date_match.group(1)

    return None


def clean_extracted_text(raw_text):
    raw_text = re.sub(r'<[^>]+>', '', raw_text)
    raw_text = re.sub(r'\s+', ' ', raw_text)
    return raw_text.strip()


def scrape_heavy_article(url):
    """
    Returns: (text, publish_date)
    - text: clean article body
    - publish_date: 'YYYY-MM-DD' string from article metadata, or None
    """
    print(f"Scraping: {url}")
    text_content = ""
    publish_date = None
    raw_html = None

    # 1. TRAFILATURA (primary — fast, great at extracting body)
    try:
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            raw_html = downloaded  # save for date extraction
            text = trafilatura.extract(downloaded, include_comments=False, include_tables=False)
            if text and len(text) > 100:
                publish_date = extract_publish_date(downloaded, url)
                print(f"   -> (Trafilatura) publish_date={publish_date}")
                return clean_extracted_text(text), publish_date
    except Exception:
        pass

    # 2. PLAYWRIGHT (fallback — for Cloudflare/JS-heavy sites)
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

            raw_html = page.content()
            browser.close()

            publish_date = extract_publish_date(raw_html, url)

            soup = BeautifulSoup(raw_html, "html.parser")
            for junk in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'iframe', 'button', 'noscript']):
                junk.decompose()

            paragraphs = soup.find_all('p')
            raw_text = "\n".join([
                p.get_text(separator=' ', strip=True)
                for p in paragraphs if len(p.get_text(strip=True)) > 20
            ])
            text_content = clean_extracted_text(raw_text)
            print(f"   -> (Playwright) publish_date={publish_date}")

    except Exception as e:
        print(f"   -> Playwright crashed: {e}")

    return text_content, publish_date
