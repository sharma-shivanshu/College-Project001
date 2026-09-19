import os
import json
from database import get_supabase_client
from extractor import extract_entities
from sheets_sync import append_to_sheet

def run_backlog_processor():
    print("Connecting to Supabase to find old pending articles...")
    supabase = get_supabase_client()
    if not supabase: return
    
    response = supabase.table("articles").select("*").eq("processing_status", "pending_local").execute()
    pending_articles = response.data
    
    print(f"Found {len(pending_articles)} articles waiting in the backlog.")
    
    for article in pending_articles:
        url = article['article_url']
        text = article['scraped_text']
        print(f"\nProcessing Backlog: {url}")
        
        extracted_data = extract_entities(text)
        if not extracted_data:
            print("   -> Groq extraction failed. Skipping.")
            continue
            
        print("   -> Groq extraction successful. Updating Supabase and Sheets...")
        
        # 1. Update Supabase
        supabase.table("articles").update({
            "raw_json": extracted_data,
            "activity_type": extracted_data.get("activity_type", "other"),
            "electoral_relevance": extracted_data.get("electoral_relevance", "none"),
            "summary": extracted_data.get("summary", ""),
            "processing_status": "completed"
        }).eq("article_url", url).execute()
        
        # 2. Update Google Sheets
        row = [url, article["source"], extracted_data.get("activity_type", "other"), extracted_data.get("electoral_relevance", "none"), extracted_data.get("summary", "")]
        append_to_sheet(os.environ.get("SPREADSHEET_ID"), row)
        
    print("\nBacklog Processing Complete.")

if __name__ == "__main__":
    run_backlog_processor()
