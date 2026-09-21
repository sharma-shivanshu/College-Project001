"""
LOCAL EXTRACTOR
Run this file strictly on your local laptop (e.g., inside VS Code).
It reads pending articles from Supabase, asks an LLM to extract the JSON, 
and then syncs to Google Sheets!
"""
import os
import json
import requests
from dotenv import load_dotenv

# Load environment variables from local .env file
load_dotenv()

from database import get_supabase_client
from sheets_sync import append_to_sheet

# If you have a local Ollama server running, it will use this:
LOCAL_LLM_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3" # Or whatever model you downloaded in Ollama

SCHEMA = '''{
  "activity_type": ["rally","statement","government_scheme","inauguration","protest","appointment","election_event","other"],
  "electoral_relevance": "high|medium|low|none",
  "actors": [{"name":"","party":"","designation":"","role":""}],
  "parties": [], "locations": [], "event_date": "YYYY-MM-DD|null", "summary": "1 sentence max"
}'''

def run_local_extraction():
    print("Connecting to Supabase...")
    supabase = get_supabase_client()
    if not supabase:
        print("Failed to connect to Supabase. Check .env file.")
        return
        
    # Get all articles waiting for local extraction
    response = supabase.table("articles").select("*").eq("processing_status", "pending_local").execute()
    pending_articles = response.data
    
    print(f"Found {len(pending_articles)} articles waiting for extraction.")
    
    for article in pending_articles:
        url = article['article_url']
        text = article['scraped_text']
        print(f"\nProcessing locally: {url}")
        
        prompt = f"Analyze this political article. Extract EXACT JSON matching this schema:\n{SCHEMA}\n\nTEXT:\n{text[:6000]}"
        
        payload = {
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False,
            "format": "json"
        }
        
        try:
            # 1. Ask Local LLM to extract JSON
            resp = requests.post(LOCAL_LLM_URL, json=payload, timeout=120)
            if resp.status_code == 200:
                result = resp.json().get('response', '{}')
            else:
                print(f"LLM API Error: {resp.status_code} - Is your local AI server running?")
                continue
                
            parsed = json.loads(result)
            
            # 2. Update Supabase
            supabase.table("articles").update({
                "raw_json": parsed,
                "activity_type": parsed.get("activity_type", "other"),
                "electoral_relevance": parsed.get("electoral_relevance", "none"),
                "summary": parsed.get("summary", ""),
                "processing_status": "completed"
            }).eq("article_url", url).execute()
            
            # 3. Update Google Sheets
            row = [url, article["source"], parsed.get("activity_type", "other"), parsed.get("electoral_relevance", "none"), parsed.get("summary", "")]
            append_to_sheet(os.environ.get("SPREADSHEET_ID"), row)
            
            print("Successfully processed locally and synced!")
            
        except Exception as e:
            print(f"Failed to process locally: {e}. Make sure Ollama/Kilocode API server is running on {LOCAL_LLM_URL}")

if __name__ == "__main__":
    run_local_extraction()
