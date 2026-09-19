import os
import time
import random
import feedparser
from scraper import scrape_heavy_article
from filter_engine import is_relevant
from extractor import extract_entities
from database import filter_existing_urls, save_article
from sheets_sync import append_to_sheet

SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID", "1MlBvANu6ePWqQSWT9GlQbG0ZhrIm8_yvGTiE1_KeztE")

def fetch_live_feed_data():
    print("Fetching live RSS feeds across UP...")
    article_data = {}
    
    # Expanded News Footprint for massive UP coverage
    feeds = [
        "https://www.bhaskar.com/rss-feed/2322/", # Dainik Bhaskar UP
        "https://cms.patrika.com/blog/location/lucknow-news/feed/", # Patrika Lucknow
        "https://cms.patrika.com/blog/location/uttar-pradesh/feed/", # Patrika UP
        "https://hindi.news18.com/rss/uttar-pradesh.xml", # News18 UP
        "https://zeenews.india.com/hindi/india/up-uttarakhand/rss.xml", # Zee News UP
        "https://www.livehindustan.com/rss/state/uttar-pradesh", # Hindustan
        "https://www.abplive.com/states/up-uk/feed", # ABP Ganga
        "https://ndtv.in/uttar-pradesh/rss", # NDTV UP
        # Twitter/Social feeds via public RSS Bridges can be added here
    ]
    
    for feed_url in feeds:
        try:
            parsed = feedparser.parse(feed_url)
            for entry in parsed.entries: # Removed the limit to scrape everything aggressively
                if hasattr(entry, 'link'):
                    title = entry.get("title", "")
                    summary = entry.get("summary", "")
                    # Clean up tracking params
                    clean_url = entry.link.split('?')[0]
                    article_data[clean_url] = {
                        "title": title,
                        "summary": summary
                    }
        except Exception as e:
            print(f"Failed to fetch feed {feed_url}: {e}")
            
    return article_data

def run_pipeline():
    print("Starting Aggressive UP Intelligence Pipeline...")
    
    live_articles = fetch_live_feed_data()
    print(f"Found {len(live_articles)} live articles across all sources.")
    if not live_articles: return
    
    new_urls = filter_existing_urls(list(live_articles.keys()))
    print(f"Deduplication: {len(live_articles)} total -> {len(new_urls)} new articles.")
    if not new_urls: return

    for url in new_urls:
        print(f"\nEvaluating: {url}")
        meta = live_articles[url]
        
        # SMART PRE-FILTER
        combined_meta_text = f"{url} {meta['title']} {meta['summary']}"
        if not is_relevant(combined_meta_text):
            continue 
            
        print("   -> Pre-filter PASSED. Initiating stealth scrape...")
        # Random delay to prevent IP bans
        time.sleep(random.uniform(1.5, 4.0)) 
        
        text = scrape_heavy_article(url)
        if not text or len(text) < 100:
            print("   -> Failed to scrape or text too short. Skipping.")
            continue
            
        print("   -> Sending to Groq (gpt-oss-120b)...")
        extracted_data = extract_entities(text)
        if not extracted_data:
            continue
            
        # Determine source
        source = "unknown"
        for s in ["bhaskar", "patrika", "news18", "zeenews", "livehindustan", "abplive", "ndtv"]:
            if s in url: source = s; break
            
        record = {
            "article_url": url,
            "source": source,
            "activity_type": str(extracted_data.get("activity_type", "other")),
            "electoral_relevance": str(extracted_data.get("electoral_relevance", "none")),
            "summary": extracted_data.get("summary", ""),
            "raw_json": extracted_data
        }
        
        save_article(record)
        
        row = [
            url, 
            record["source"], 
            record["activity_type"], 
            record["electoral_relevance"], 
            record["summary"],
            extracted_data.get("district", ""),
            ", ".join(extracted_data.get("key_leaders", []))
        ]
        append_to_sheet(SPREADSHEET_ID, row)
        
    print("\nPipeline execution complete.")

if __name__ == "__main__":
    run_pipeline()
