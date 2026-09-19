import os
import time
import random
import feedparser
from datetime import datetime
from scraper import scrape_heavy_article
from filter_engine import is_relevant
from extractor import extract_entities
from database import filter_existing_urls, save_article
from sheets_sync import append_to_sheet

SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID", "1MlBvANu6ePWqQSWT9GlQbG0ZhrIm8_yvGTiE1_KeztE")
MAX_SCRAPES_PER_RUN = 50 

def fetch_direct_news_feeds():
    print("Fetching directly from Native News RSS Feeds...")
    article_data = {}
    
    feeds = [
        "https://www.bhaskar.com/rss-feed/2322/", # Dainik Bhaskar UP
        "https://cms.patrika.com/blog/location/lucknow-news/feed/", # Patrika Lucknow
        "https://cms.patrika.com/blog/location/uttar-pradesh/feed/", # Patrika UP
        "https://hindi.news18.com/rss/uttar-pradesh.xml", # News18 UP
        "https://zeenews.india.com/hindi/india/up-uttarakhand/rss.xml", # Zee News UP
        "https://www.livehindustan.com/rss/state/uttar-pradesh", # Hindustan
        "https://www.abplive.com/states/up-uk/feed", # ABP Ganga
        "https://ndtv.in/uttar-pradesh/rss", # NDTV UP
        "https://english.jagran.com/rss/politics.xml", # Jagran English
        "https://rsshub.app/twitter/user/yadavakhilesh", # Akhilesh Yadav X
        "https://rsshub.app/twitter/user/myogiadityanath" # Yogi Adityanath X
    ]
    
    # 48 hours ago timestamp
    time_limit = time.time() - (48 * 3600)
    
    for feed_url in feeds:
        try:
            parsed = feedparser.parse(feed_url)
            for entry in parsed.entries: 
                # Strict Python-level date filter
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    pub_time = time.mktime(entry.published_parsed)
                    if pub_time < time_limit:
                        continue 
                
                if hasattr(entry, 'link'):
                    clean_url = entry.link.split('?')[0]
                    article_data[clean_url] = {
                        "title": entry.get("title", ""),
                        "summary": entry.get("summary", ""),
                        "source_feed": feed_url
                    }
        except Exception as e:
            pass 
            
    return article_data

def run_pipeline():
    print("Starting Direct Native Feed Pipeline...")
    
    live_articles = fetch_direct_news_feeds()
    print(f"Found {len(live_articles)} recent links directly from sources.")
    if not live_articles: return
    
    new_urls = filter_existing_urls(list(live_articles.keys()))
    print(f"Deduplication: {len(new_urls)} brand new links to evaluate.")
    if not new_urls: return

    scraped_count = 0

    for url in new_urls:
        if scraped_count >= MAX_SCRAPES_PER_RUN:
            break

        meta = live_articles[url]
        combined_meta_text = f"{url} {meta['title']} {meta['summary']}"
        if not is_relevant(combined_meta_text):
            continue 
            
        text = scrape_heavy_article(url)
        if not text or len(text) < 50:
            continue
            
        print("   -> Extracting Entities via Groq (with Fallback Roll-over)...")
        extracted_data = extract_entities(text)
        if not extracted_data:
            continue
            
        scraped_count += 1
            
        source = "unknown"
        if "twitter" in url or "rsshub" in meta["source_feed"]: source = "x_twitter"
        else:
            for s in ["bhaskar", "patrika", "news18", "zeenews", "livehindustan", "abplive", "ndtv", "jagran"]:
                if s in url.lower(): source = s; break
            
        record = {
            "article_url": url,
            "source": source,
            "activity_type": str(extracted_data.get("activity_type", "other")),
            "electoral_relevance": str(extracted_data.get("electoral_relevance", "none")),
            "summary": extracted_data.get("summary", ""),
            "raw_json": extracted_data
        }
        
        save_article(record)
        
        now = datetime.now()
        row = [
            now.strftime("%Y-%m-%d"),
            now.strftime("%H:%M:%S"),
            url, 
            source, 
            record["activity_type"], 
            record["electoral_relevance"], 
            str(extracted_data.get("district", "")),
            str(extracted_data.get("constituency", "")),
            str(extracted_data.get("local_geography", "")),
            ", ".join(extracted_data.get("key_leaders", [])),
            ", ".join(extracted_data.get("keywords", [])),
            record["summary"],
            text[:10000]
        ]
        append_to_sheet(SPREADSHEET_ID, row)
        
    print(f"\nPipeline complete. Processed {scraped_count} native articles.")

if __name__ == "__main__":
    run_pipeline()
