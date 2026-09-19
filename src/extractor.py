import os
import json
import time
from google import genai

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# Optimized prompt for token saving and strict JSON adherence
SCHEMA = '''{
  "activity_type": ["rally","statement","government_scheme","inauguration","protest","appointment","election_event","other"],
  "electoral_relevance": "high|medium|low|none",
  "actors": [{"name":"","party":"","designation":"","role":""}],
  "parties": [], "locations": [],
  "event_date": "YYYY-MM-DD|null",
  "summary": "1 sentence max"
}'''

def extract_entities(text):
    prompt = f"Analyze this Hindi/English political article. Extract data EXACTLY matching this JSON schema. No markdown, no explanations, just raw JSON.\nSCHEMA:\n{SCHEMA}\n\nTEXT:\n{text[:6000]}"
    try:
        # Upgraded to the modern API and the 2.5-flash model
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        raw = response.text.replace('```json', '').replace('```', '').strip()
        parsed = json.loads(raw)
        
        # Enforce rate limits: Free tier is 15 RPM (1 request every 4 seconds)
        time.sleep(4.5) 
        
        return parsed
    except Exception as e:
        print(f"Gemini Extraction Failed: {e}")
        time.sleep(5) # Cooldown on failure
        return None
