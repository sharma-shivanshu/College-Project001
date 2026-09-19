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
MAX_SCRAPES_PER_RUN = 40  # Prevents GitHub Actions from timing out or hitting rate limits

def fetch_live_feed_data():
    print("Fetching live RSS feeds across UP (News + Social)...")
    article_data = {}
    
    feeds = [
        # News Sources
        "https://www.bhaskar.com/rss-feed/2322/", 
        "https://cms.patrika.com/blog/location/lucknow-news/feed/", 
        "https://hindi.news18.com/rss/uttar-pradesh.xml", 
        "https://zeenews.india.com/hindi/india/up-uttarakhand/rss.xml", 
        "https://www.livehindustan.com/rss/state/uttar-pradesh", 
        "https://www.abplive.com/states/up-uk/feed", 
        "https://ndtv.in/uttar-pradesh/rss",
        # Social Media (X/Twitter via public RSS bridges for top leaders)
        "https://rsshub.app/twitter/user/yadavakhilesh",
        "https://rsshub.app/twitter/user/myogiadityanath",
        "https://rsshub.app/twitter/user/Mayawati"
    ]
    
    for feed_url in feeds:
        try:
            parsed = feedparser.parse(feed_url)
            for entry in parsed.entries: 
                if hasattr(entry, 'link'):
                    title = entry.get("title", "")
                    summary = entry.get("summary", "")
                    clean_url = entry.link.split('?')[0]
                    article_data[clean_url] = {
                        "title": title,
                        "summary": summary,
                        "source_feed": feed_url
                    }
        except Exception as e:
            pass # Fail silently for individual feeds to keep pipeline alive
            
    return article_data

def run_pipeline():
    print("Starting Aggressive UP Intelligence Pipeline...")
    
    live_articles = fetch_live_feed_data()
    print(f"Found {len(live_articles)} live links across all sources.")
    if not live_articles: return
    
    new_urls = filter_existing_urls(list(live_articles.keys()))
    print(f"Deduplication: {len(new_urls)} brand new links to evaluate.")
    if not new_urls: return

    scraped_count = 0

    for url in new_urls:
        if scraped_count >= MAX_SCRAPES_PER_RUN:
            print(f"\nReached MAX_SCRAPES_PER_RUN ({MAX_SCRAPES_PER_RUN}). Stopping gracefully to save compute time.")
            break

        print(f"\nEvaluating: {url}")
        meta = live_articles[url]
        
        # 1. SMART PRE-FILTER (Runs instantly, NO scraping yet)
        combined_meta_text = f"{url} {meta['title']} {meta['summary']}"
        if not is_relevant(combined_meta_text):
            continue 
            
        # 2. HEAVY SCRAPE (Only runs if it passes the filter)
        print("   -> Pre-filter PASSED. Initiating stealth scrape...")
        time.sleep(random.uniform(1.5, 4.0)) 
        
        text = scrape_heavy_article(url)
        if not text or len(text) < 50:
            # If Playwright fails (common with Twitter blocks), use the RSS summary as fallback!
            if "twitter" in url or "x.com" in url:
                print("   -> Social media scrape blocked. Falling back to RSS text...")
                text = meta['title'] + " " + meta['summary']
            else:
                print("   -> Failed to scrape or text too short. Skipping.")
                continue
            
        # 3. AI EXTRACTION
        print("   -> Sending to Groq...")
        extracted_data = extract_entities(text)
        if not extracted_data:
            continue
            
        scraped_count += 1
            
        source = "unknown"
        if "twitter" in url or "rsshub" in meta["source_feed"]: source = "x_twitter"
        elif "facebook" in url: source = "facebook"
        else:
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
        
    print(f"\nPipeline execution complete. Successfully processed {scraped_count} items.")

if __name__ == "__main__":
    run_pipeline()
