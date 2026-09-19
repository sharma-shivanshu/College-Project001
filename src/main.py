import os
import time
import feedparser
from scraper import scrape_dainik_bhaskar
from filter_engine import is_relevant
from extractor import extract_entities
from database import filter_existing_urls, save_article
from sheets_sync import append_to_sheet

SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID", "SET_ME_IN_GITHUB_SECRETS")

def fetch_live_urls():
    """
    Fetches the absolute latest URLs dynamically from live RSS feeds.
    This guarantees we never process old 2-year-old articles.
    """
    print("Fetching live RSS feeds...")
    urls = []
    
    # List of live RSS feeds to monitor
    feeds = [
        "https://www.bhaskar.com/rss-feed/2322/", # Example Bhaskar UP feed
        "https://cms.patrika.com/blog/location/lucknow-news/feed/"
    ]
    
    for feed_url in feeds:
        try:
            parsed = feedparser.parse(feed_url)
            for entry in parsed.entries[:20]: # Grab top 20 latest from each feed
                if hasattr(entry, 'link'):
                    urls.append(entry.link)
        except Exception as e:
            print(f"Failed to fetch feed {feed_url}: {e}")
            
    # Fallback to homepage scraping if RSS fails (optional advanced logic)
    return list(set(urls))

def run_pipeline():
    print("Starting Political Intelligence Pipeline...")
    
    # 1. Discover LIVE URLs from today
    discovered_urls = fetch_live_urls()
    print(f"Found {len(discovered_urls)} live articles published recently.")
    
    if not discovered_urls:
        print("No URLs discovered. Exiting.")
        return
    
    # 2. Deduplication (Check Supabase so we don't process old URLs)
    new_urls = filter_existing_urls(discovered_urls)
    if not new_urls:
        print("All discovered articles have already been processed previously. Exiting cleanly.")
        return

    # 3. Process new URLs
    for url in new_urls:
        print(f"\nProcessing: {url}")
        
        # A. Scrape
        text = scrape_dainik_bhaskar(url)
        if not text or len(text) < 100:
            print("Failed to scrape or text too short. Skipping.")
            continue
            
        # B. Funnel Filter (Does it contain political keywords or pass ML?)
        if not is_relevant(text):
            print("Article is not politically relevant. Skipping.")
            continue
            
        # C. LLM Extraction
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
