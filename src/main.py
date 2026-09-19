import os
import time
from scraper import scrape_dainik_bhaskar
from filter_engine import is_relevant
from extractor import extract_entities
from database import filter_existing_urls, save_article
from sheets_sync import append_to_sheet

SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID", "SET_ME_IN_GITHUB_SECRETS")

def run_pipeline():
    print("Starting Political Intelligence Pipeline...")
    
    # 1. Discover URLs (Mocked for demonstration, replace with actual RSS/Sitemap fetching)
    # E.g. fetch_rss_feeds()
    discovered_urls = [
        "https://www.bhaskar.com/local/uttar-pradesh/lucknow/news/up-bjp-state-president-bhupendra-chaudhary-said-we-will-win-the-upcoming-by-elections-133649514.html",
        "https://www.bhaskar.com/local/uttar-pradesh/varanasi/news/varanasi-news-pm-modi-visit-to-kashi-on-18-june-133182103.html"
    ]
    
    # 2. Deduplication (Check Supabase so we don't process old URLs)
    new_urls = filter_existing_urls(discovered_urls)
    if not new_urls:
        print("No new articles to process. Exiting cleanly.")
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
            "source": "dainik_bhaskar",
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
