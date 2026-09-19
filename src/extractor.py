import os
import json
import time
import google.generativeai as genai

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
# Gemini 1.5 Flash is highly cost-effective and fast
model = genai.GenerativeModel('gemini-1.5-flash')

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
        response = model.generate_content(prompt)
        raw = response.text.replace('```json', '').replace('```', '').strip()
        parsed = json.loads(raw)
        
        # Enforce rate limits: Free tier is 15 RPM (1 request every 4 seconds)
        time.sleep(4.5) 
        
        return parsed
    except Exception as e:
        print(f"Gemini Extraction Failed: {e}")
        time.sleep(5) # Cooldown on failure
        return None
