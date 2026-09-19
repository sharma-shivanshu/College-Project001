import os
import json
import time
from groq import Groq

def get_groq_client():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return None
    return Groq(api_key=api_key)

# Upgraded schema to proactively capture geospatial and entity data for the future dashboard!
SCHEMA = '''{
  "activity_type": "rally|statement|government_scheme|inauguration|protest|appointment|election_event|other",
  "electoral_relevance": "high|medium|low|none",
  "district": "Name of the UP district where this occurred, or null",
  "assembly_constituency": "Name of specific UP assembly constituency if mentioned, or null",
  "key_leaders": ["list of major politicians mentioned"],
  "sentiment_ruling_party": "positive|negative|neutral",
  "summary": "1 sentence max"
}'''

def extract_entities(text):
    client = get_groq_client()
    if not client:
        return None
        
    prompt = f"Analyze this political article from Uttar Pradesh. Extract data EXACTLY matching this JSON schema. Return ONLY a valid JSON object. Do not wrap in markdown or add explanations.\nSCHEMA:\n{SCHEMA}\n\nTEXT:\n{text[:6000]}"
    try:
        completion = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        raw = completion.choices[0].message.content.strip()
        parsed = json.loads(raw)
        
        time.sleep(2) 
        return parsed
    except Exception as e:
        print(f"Groq Extraction Failed: {e}")
        time.sleep(5)
        return None
