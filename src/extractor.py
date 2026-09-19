import os
import json
import time
from groq import Groq

def get_groq_client():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return None
    return Groq(api_key=api_key)

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
    client = get_groq_client()
    if not client:
        print("Groq API key not found. Skipping extraction.")
        return None
        
    prompt = f"Analyze this Hindi/English political article. Extract data EXACTLY matching this JSON schema. Return ONLY a valid JSON object. Do not wrap in markdown or add explanations.\nSCHEMA:\n{SCHEMA}\n\nTEXT:\n{text[:6000]}"
    try:
        completion = client.chat.completions.create(
            model="llama-3.1-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        raw = completion.choices[0].message.content.strip()
        parsed = json.loads(raw)
        
        # Groq is extremely fast and generous with rate limits, but a small delay ensures stability
        time.sleep(2) 
        
        return parsed
    except Exception as e:
        print(f"Groq Extraction Failed: {e}")
        time.sleep(5)
        return None
