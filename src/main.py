import os
import time
import random
import feedparser
import requests
import urllib.parse
from bs4 import BeautifulSoup
from datetime import datetime
from scraper import scrape_heavy_article
from filter_engine import is_relevant
from extractor import extract_entities
from database import filter_existing_urls, save_article
from sheets_sync import append_to_sheet
from sources_config import RSS_FEEDS, HTML_TOPIC_PAGES

SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID", "1MlBvANu6ePWqQSWT9GlQbG0ZhrIm8_yvGTiE1_KeztE")
MAX_SCRAPES_PER_RUN = 50  # 50/hr = 1200/day — well within free tier limits

def fetch_all_sources():
    """
    Two-pronged discovery:
    1. RSS feeds  — fast, timestamped, easy to date-filter.
    2. HTML topic pages — extracts article links directly from district/party pages.
    Each run picks a random 15-page sample from HTML_TOPIC_PAGES to stay within
    GitHub Actions time limits while covering different districts every hour.
    """
    print("Fetching from all native sources (RSS + HTML District Pages)...")
    article_data = {}  # url -> {title, summary, source, district}
    time_limit = time.time() - (48 * 3600)

    # ── 1. RSS Feeds ────────────────────────────────────────────────────
    for (src, feed_url) in RSS_FEEDS:
        try:
            parsed = feedparser.parse(feed_url)
            for entry in parsed.entries[:15]:
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    if time.mktime(entry.published_parsed) < time_limit:
                        continue
                if hasattr(entry, 'link'):
                    clean_url = entry.link.split('?')[0]
                    article_data[clean_url] = {
                        "title":   entry.get("title", ""),
                        "summary": entry.get("summary", ""),
                        "source":  src,
                        "district": ""
                    }
        except Exception:
            pass

    # ── 2. HTML Topic Pages (sampled) ───────────────────────────────────
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    sampled = random.sample(HTML_TOPIC_PAGES, min(15, len(HTML_TOPIC_PAGES)))

    for (src, topic_url, district_tag) in sampled:
        try:
            res = requests.get(topic_url, headers=headers, timeout=7)
            if res.status_code != 200:
                continue
            soup = BeautifulSoup(res.text, "html.parser")
            domain = urllib.parse.urlparse(topic_url).scheme + "://" + urllib.parse.urlparse(topic_url).netloc

            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"].strip()
                # Resolve relative paths
                if href.startswith("/"):
                    href = domain + href
                if not href.startswith("http"):
                    continue
                clean_url = href.split('?')[0]
                # Heuristic: real article URLs are long and contain news/date patterns
                if len(clean_url) < 40:
                    continue
                if not any(x in clean_url for x in [".html", ".cms", "/news/", "/article", "story"]):
                    continue
                if clean_url not in article_data:
                    title = a_tag.get_text(strip=True)[:120]
                    if len(title) < 10:
                        continue
                    article_data[clean_url] = {
                        "title":   title,
                        "summary": "",
                        "source":  src,
                        "district": district_tag
                    }
        except Exception:
            pass

    print(f"Discovery complete. Total unique links: {len(article_data)}")
    return article_data


def run_pipeline():
    print("═" * 60)
    print("UP Political Intelligence Pipeline — Starting")
    print("═" * 60)

    live_articles = fetch_all_sources()
    if not live_articles:
        print("No articles found. Exiting.")
        return

    new_urls = filter_existing_urls(list(live_articles.keys()))
    print(f"After deduplication: {len(new_urls)} new links to evaluate.")
    if not new_urls:
        print("All articles already processed. Nothing to do.")
        return

    # Shuffle so each run covers different sources
    random.shuffle(new_urls)

    scraped_count = 0

    for url in new_urls:
        if scraped_count >= MAX_SCRAPES_PER_RUN:
            print(f"\n[LIMIT] Reached MAX_SCRAPES_PER_RUN ({MAX_SCRAPES_PER_RUN}). Stopping gracefully.")
            break

        meta = live_articles[url]
        combined_meta_text = f"{url} {meta['title']} {meta['summary']}"

        # ── Pre-filter (no scraping yet) ────────────────────────────
        if not is_relevant(combined_meta_text):
            continue

        # ── Scrape ──────────────────────────────────────────────────
        text, publish_date = scrape_heavy_article(url)
        if not text or len(text) < 50:
            continue

        # ── AI Extract ──────────────────────────────────────────────
        print("   -> Extracting via Groq (multi-model fallback)...")
        extracted_data = extract_entities(text)
        if not extracted_data:
            continue

        scraped_count += 1
        source = meta["source"]

        now = datetime.now()
        district = extracted_data.get("district") or meta.get("district", "")
        # Use article's real publish date; fall back to today if not found
        post_date = publish_date if publish_date else now.strftime("%Y-%m-%d")
        post_time = now.strftime("%H:%M:%S")  # when our pipeline scraped it

        record = {
            "article_url":         url,
            "source":              source,
            "activity_type":       str(extracted_data.get("activity_type", "other")),
            "electoral_relevance": str(extracted_data.get("electoral_relevance", "none")),
            "summary":             extracted_data.get("summary", ""),
            "scraped_text":        text[:20000],
            "published_date":      post_date,
            "sheet_synced":        True,
            "raw_json":            extracted_data
        }
        article_id = save_article(record)
        # If save failed, don't append to sheet to maintain sync
        if not article_id:
            continue

        row = [
            str(article_id) if isinstance(article_id, str) else "",
            post_date,          # A: Real publish date from article metadata
            post_time,          # B: When our pipeline scraped it
            url,
            source,
            record["activity_type"],
            record["electoral_relevance"],
            str(district),
            str(extracted_data.get("constituency", "")),
            str(extracted_data.get("local_geography", "")),
            ", ".join(extracted_data.get("parties_involved", [])),
            ", ".join(extracted_data.get("key_leaders", [])),
            ", ".join(extracted_data.get("keywords", [])),
            record["summary"],
            text[:10000]        # N: Raw scraped text for reference
        ]
        append_to_sheet(SPREADSHEET_ID, row)

    print(f"\n{'═'*60}")
    print(f"Pipeline complete. Successfully processed {scraped_count} articles.")
    print(f"{'═'*60}")


if __name__ == "__main__":
    run_pipeline()
