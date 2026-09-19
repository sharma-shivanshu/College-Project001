import os
import time
import random
import feedparser
import urllib.parse
from datetime import datetime, timedelta
from scraper import scrape_heavy_article
from filter_engine import is_relevant
from extractor import extract_entities
from database import filter_existing_urls, save_article
from sheets_sync import append_to_sheet

SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID", "1MlBvANu6ePWqQSWT9GlQbG0ZhrIm8_yvGTiE1_KeztE")
MAX_SCRAPES_PER_RUN = 30  # Hard cap to respect Groq's 200k Tokens Per Day limit

UP_DISTRICTS = [
    "Agra", "Aligarh", "Prayagraj", "Ambedkar Nagar", "Amethi", "Amroha", "Auraiya", "Ayodhya", "Azamgarh", 
    "Badaun", "Baghpat", "Bahraich", "Ballia", "Balrampur", "Banda", "Barabanki", "Bareilly", "Basti", 
    "Bhadohi", "Bijnor", "Bulandshahr", "Chandauli", "Chitrakoot", "Deoria", "Etah", "Etawah", "Farrukhabad", 
    "Fatehpur", "Firozabad", "Gautam Buddha Nagar", "Ghaziabad", "Ghazipur", "Gonda", "Gorakhpur", "Hamirpur", 
    "Hapur", "Hardoi", "Hathras", "Jalaun", "Jaunpur", "Jhansi", "Kannauj", "Kanpur", "Kasganj", "Kaushambi", 
    "Kheri", "Kushinagar", "Lalitpur", "Lucknow", "Maharajganj", "Mahoba", "Mainpuri", "Mathura", "Mau", 
    "Meerut", "Mirzapur", "Moradabad", "Muzaffarnagar", "Pilibhit", "Pratapgarh", "Raebareli", "Rampur", 
    "Saharanpur", "Sambhal", "Sant Kabir Nagar", "Shahjahanpur", "Shamli", "Shravasti", "Siddharthnagar", 
    "Sitapur", "Sonbhadra", "Sultanpur", "Unnao", "Varanasi"
]

def fetch_google_news_for_districts():
    print("Fetching Google News aggregators...")
    article_data = {}
    random.shuffle(UP_DISTRICTS)
    
    # 48 hours ago timestamp
    time_limit = time.time() - (48 * 3600)
    
    for district in UP_DISTRICTS:
        query = urllib.parse.quote(f"{district} politics OR election OR bjp OR sp OR bsp")
        feed_url = f"https://news.google.com/rss/search?q={query}&hl=hi&gl=IN&ceid=IN:hi"
        try:
            parsed = feedparser.parse(feed_url)
            for entry in parsed.entries[:15]: 
                # STRICT PYTHON-LEVEL DATE FILTER (Ignore anything older than 48 hours)
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    pub_time = time.mktime(entry.published_parsed)
                    if pub_time < time_limit:
                        continue # Drop old articles instantly
                
                if hasattr(entry, 'link'):
                    article_data[entry.link] = {
                        "title": entry.get("title", ""),
                        "summary": entry.get("summary", ""),
                        "source_feed": "google_news"
                    }
        except Exception as e:
            pass 
    return article_data

def run_pipeline():
    print("Starting Optimized Pipeline...")
    
    live_articles = fetch_google_news_for_districts()
    print(f"Found {len(live_articles)} recent local links.")
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
            
        print("   -> Extracting Entities via Groq...")
        extracted_data = extract_entities(text)
        if not extracted_data:
            continue
            
        scraped_count += 1
            
        source = "google_news_aggregator"
        for s in ["bhaskar", "patrika", "news18", "zeenews", "livehindustan", "abplive", "ndtv", "jagran", "amarujala", "navbharattimes"]:
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
            text[:10000] # Cap text output to prevent sheet bloat
        ]
        append_to_sheet(SPREADSHEET_ID, row)
        
    print(f"\nPipeline complete. Processed {scraped_count} local articles.")

if __name__ == "__main__":
    run_pipeline()
