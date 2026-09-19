"""
LOCAL KILOCODE EXTRACTOR
Run this file strictly on your local laptop (e.g., inside VS Code).
It reads pending articles from Supabase, asks your local Kilocode/Ollama model 
to extract the JSON, and then syncs to Google Sheets!
"""
import os
import json
import requests
from database import get_supabase_client
from sheets_sync import append_to_sheet

# Set your local API endpoint here (e.g., standard OpenAI compatible endpoint provided by local extensions)
LOCAL_LLM_URL = "http://localhost:11434/v1/chat/completions" # Change this to Kilocode's endpoint if different
MODEL_NAME = "your-favourite-hindi-model" 
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID", "YOUR_SPREADSHEET_ID_HERE")

SCHEMA = '''{
  "activity_type": ["rally","statement","government_scheme","inauguration","protest","appointment","election_event","other"],
  "electoral_relevance": "high|medium|low|none",
  "actors": [{"name":"","party":"","designation":"","role":""}],
  "parties": [], "locations": [], "event_date": "YYYY-MM-DD|null", "summary": "1 sentence max"
}'''

def run_local_extraction():
    print("Connecting to Supabase...")
    supabase = get_supabase_client()
    
    # Get all articles waiting for local extraction
    response = supabase.table("articles").select("*").eq("processing_status", "pending_local").execute()
    pending_articles = response.data
    
    print(f"Found {len(pending_articles)} articles waiting for local Kilocode extraction.")
    
    for article in pending_articles:
        url = article['article_url']
        text = article['scraped_text']
        print(f"\nProcessing locally: {url}")
        
        prompt = f"Analyze this political article. Extract EXACT JSON matching this schema:\n{SCHEMA}\n\nTEXT:\n{text[:6000]}"
        
        # NOTE: You will need to adjust the payload structure below based on how Kilocode accepts API requests.
        payload = {
            "model": MODEL_NAME,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1
        }
        
        try:
            # 1. Ask Kilocode to extract JSON
            # resp = requests.post(LOCAL_LLM_URL, json=payload)
            # result = resp.json()['choices'][0]['message']['content']
            
            # (MOCK RESULT FOR NOW until Kilocode endpoint is confirmed)
            result = '{"summary": "Local extraction pending actual Kilocode API structure."}'
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
            append_to_sheet(SPREADSHEET_ID, row)
            
            print("Successfully processed locally and synced!")
            
        except Exception as e:
            print(f"Failed to process locally: {e}")

if __name__ == "__main__":
    run_local_extraction()
