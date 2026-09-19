import os
import json
import time
import re
from groq import Groq

def get_groq_client():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key: return None
    return Groq(api_key=api_key)

SCHEMA = '''{
  "activity_type": "rally|statement|government_scheme|inauguration|protest|appointment|election_event|other",
  "electoral_relevance": "high|medium|low|none",
  "district": "Name of the UP district where this occurred, or null",
  "constituency": "Name of specific UP assembly constituency if mentioned, or null",
  "local_geography": "Specific village, block, ward, or tehsil mentioned, or null",
  "key_leaders": ["list of major politicians mentioned"],
  "keywords": ["list of 3 to 5 highly relevant political/event tags"],
  "sentiment_ruling_party": "positive|negative|neutral",
  "summary": "1 sentence max"
}'''

def clean_text(text):
    # Strip bizarre encodings and weird gibberish before sending to AI
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\{.*?\}', '', text) 
    return text.strip()

def extract_entities(text):
    client = get_groq_client()
    if not client: return None
        
    cleaned_text = clean_text(text)
    # TRUNCATE TO 1500 CHARACTERS to aggressively save Groq tokens (200k/day limit)
    truncated_text = cleaned_text[:1500] 
    
    prompt = f"Analyze this political article from Uttar Pradesh. Extract data EXACTLY matching this JSON schema. Return ONLY a valid JSON object.\nSCHEMA:\n{SCHEMA}\n\nTEXT:\n{truncated_text}"
    try:
        completion = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        raw = completion.choices[0].message.content.strip()
        parsed = json.loads(raw)
        return parsed
    except Exception as e:
        print(f"Groq Extraction Failed: {e}")
        return None
