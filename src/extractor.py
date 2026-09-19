import os
import json
import google.generativeai as genai

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

SCHEMA = '''
{
  "activity_type": ["rally","statement","government_scheme","inauguration","protest","appointment","election_event","other"],
  "electoral_relevance": "high|medium|low|none",
  "actors": [{"name":"","party":"","designation":"","role":""}],
  "parties": [], "constituencies": [], "locations": [],
  "event_date": "YYYY-MM-DD|null",
  "key_claims": [], "summary": ""
}
'''

def extract_entities(text):
    prompt = f"Extract the following structured data from this political news article. Return ONLY valid JSON matching this schema:\n{SCHEMA}\n\nArticle Text:\n{text[:8000]}"
    try:
        response = model.generate_content(prompt)
        result = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(result)
    except Exception as e:
        print(f"Gemini Extraction Failed: {e}")
        return None
