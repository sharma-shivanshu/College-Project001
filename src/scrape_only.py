import os
from scraper import scrape_dainik_bhaskar
from filter_engine import is_relevant
from database import filter_existing_urls, get_supabase_client
from main import fetch_live_feed_data

def run_scrape_only_pipeline():
    print("Starting Cloud Scraping Backup Pipeline (No LLM)...")
    
    live_articles = fetch_live_feed_data()
    print(f"Found {len(live_articles)} live articles.")
    if not live_articles: return
    
    new_urls = filter_existing_urls(list(live_articles.keys()))
    if not new_urls:
        print("No new articles. Exiting.")
        return

    supabase = get_supabase_client()
    
    for url in new_urls:
        print(f"\nEvaluating: {url}")
        meta = live_articles[url]
        
        # SMART PRE-FILTER
        combined_meta_text = f"{url} {meta['title']} {meta['summary']}"
        if not is_relevant(combined_meta_text):
            continue 
            
        print("   -> Pre-filter PASSED. Initiating heavy scrape...")
        text = scrape_dainik_bhaskar(url)
        if not text or len(text) < 100: continue
            
        # Save raw text to database for LOCAL processing later
        record = {
            "article_url": url,
            "source": "dainik_bhaskar" if "bhaskar.com" in url else "patrika",
            "scraped_text": text,
            "processing_status": "pending_local"
        }
        
        try:
            supabase.table("articles").insert(record).execute()
            print("   -> Saved raw text to Supabase for local Kilocode extraction.")
        except Exception as e:
            print(f"   -> Database error: {e}")

if __name__ == "__main__":
    run_scrape_only_pipeline()
