import os
import time
import feedparser
from scraper import scrape_dainik_bhaskar
from filter_engine import is_relevant
from extractor import extract_entities
from database import filter_existing_urls, save_article
from sheets_sync import append_to_sheet

SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID", "SET_ME_IN_GITHUB_SECRETS")

def fetch_live_feed_data():
    """
    Fetches the latest articles dynamically from RSS feeds.
    Returns a dictionary mapping URL -> metadata {title, summary}.
    """
    print("Fetching live RSS feeds...")
    article_data = {}
    
    feeds = [
        "https://www.bhaskar.com/rss-feed/2322/",
        "https://cms.patrika.com/blog/location/lucknow-news/feed/"
    ]
    
    for feed_url in feeds:
        try:
            parsed = feedparser.parse(feed_url)
            for entry in parsed.entries[:30]: 
                if hasattr(entry, 'link'):
                    article_data[entry.link] = {
                        "title": entry.get("title", ""),
                        "summary": entry.get("summary", "")
                    }
        except Exception as e:
            print(f"Failed to fetch feed {feed_url}: {e}")
            
    return article_data

def run_pipeline():
    print("Starting Optimized Pre-Filter Pipeline...")
    
    # 1. Discover LIVE URLs and metadata
    live_articles = fetch_live_feed_data()
    print(f"Found {len(live_articles)} live articles.")
    if not live_articles: return
    
    # 2. Deduplication (Check Supabase so we don't process old URLs)
    new_urls = filter_existing_urls(list(live_articles.keys()))
    if not new_urls:
        print("All discovered articles have already been processed previously. Exiting cleanly.")
        return

    # 3. Process new URLs
    for url in new_urls:
        print(f"\nEvaluating: {url}")
        meta = live_articles[url]
        
        # A. SMART PRE-FILTER (Evaluate URL, Title, and Summary BEFORE Scraping!)
        combined_meta_text = f"{url} {meta['title']} {meta['summary']}"
        if not is_relevant(combined_meta_text):
            continue # Skip scraping entirely! Saves massive compute time.
            
        # B. Scrape Full Text (Only for articles that passed the pre-filter)
        print("   -> Pre-filter PASSED. Initiating heavy scrape...")
        text = scrape_dainik_bhaskar(url)
        if not text or len(text) < 100:
            print("   -> Failed to scrape or text too short. Skipping.")
            continue
            
        # C. LLM Extraction
        print("   -> Sending to Gemini for extraction...")
        extracted_data = extract_entities(text)
        if not extracted_data:
            continue
            
        # D. Assemble Final Record
        record = {
            "article_url": url,
            "source": "dainik_bhaskar" if "bhaskar.com" in url else "patrika",
            "activity_type": extracted_data.get("activity_type", "other"),
            "electoral_relevance": extracted_data.get("electoral_relevance", "none"),
            "summary": extracted_data.get("summary", ""),
            "raw_json": extracted_data
        }
        
        # E. Save to Supabase
        save_article(record)
        
        # F. Save to Google Sheets (for visibility)
        row = [
            url, 
            record["source"], 
            record["activity_type"], 
            record["electoral_relevance"], 
            record["summary"]
        ]
        append_to_sheet(SPREADSHEET_ID, row)
        
    print("\nPipeline execution complete.")

if __name__ == "__main__":
    run_pipeline()
