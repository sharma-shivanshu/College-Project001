"""
Universal Political Intelligence Extractor
Multi-Provider Fallback: Gemini -> Cloudflare -> Groq
"""

import os
import json
import time
import re
import requests

UNIVERSAL_PROMPT = """You are a senior political intelligence analyst covering Uttar Pradesh elections (2027).

Your task: Analyze the article below and extract a structured intelligence brief.
- Extract FACTS only. Do NOT translate verbatim.
- The "brief" field must be YOUR OWN original 3-4 sentence English paraphrase — not a copy or translation.
- Cover ALL applicable fields. Use null for anything not mentioned.

Return ONLY a valid JSON object matching this schema exactly:

{
  "event_category": "one of: rally|press_conference|government_scheme|protest|dharna|appointment|alliance|election_prep|condolence|inauguration|legal_court|caste_outreach|party_internal|counter_attack|other",
  "date_of_event": "YYYY-MM-DD if mentioned, else null",
  "location": {
    "district": "UP district name or null",
    "constituency": "specific UP assembly constituency or null",
    "venue": "specific place, village, block, stadium, etc. or null"
  },
  "primary_actor": {
    "name": "main person who acted or spoke",
    "party": "their party abbreviation (BJP/SP/BSP/INC/RLD etc.)",
    "designation": "their title/post or null"
  },
  "other_actors": [
    {"name": "...", "party": "...", "designation": "..."}
  ],
  "action_taken": "Single precise sentence: WHO did WHAT (paraphrase, not translate)",
  "claim_or_demand": "The specific claim, accusation, or demand made — or null",
  "target_of_attack": "Specific person or party being criticized — or null",
  "issues_raised": ["specific issues: e.g. land acquisition, OBC reservation, unemployment, corruption, bulldozer action"],
  "castes_mentioned": ["caste/community names explicitly mentioned in article"],
  "voter_groups_targeted": ["e.g. farmers, youth, women, minorities, Dalits"],
  "schemes_mentioned": ["government scheme names if any"],
  "numbers_mentioned": {
    "crowd_size": "e.g. 5000 or null",
    "beneficiaries": "e.g. 10000 farmers or null",
    "financial_figure": "e.g. Rs 500 crore or null",
    "vote_count": "e.g. 45000 votes in 2022 or null"
  },
  "electoral_implication": "Why this matters for 2027 UP elections — 1 original sentence",
  "sentiment": {
    "towards_bjp": "positive|negative|neutral",
    "towards_sp": "positive|negative|neutral",
    "towards_bsp": "positive|negative|neutral",
    "towards_inc": "positive|negative|neutral"
  },
  "brief": "3-4 sentence English intelligence brief. Must be YOUR OWN paraphrase covering: what happened, who was involved (with designations), where, key claims or significance. Write as an analyst briefing a minister."
}
"""

def clean_text(text):
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def parse_json_response(text):
    """Clean markdown formatting if models wrap JSON in code blocks"""
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return json.loads(text.strip())

def call_gemini(prompt_text):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key: return None, "Missing GEMINI_API_KEY"
    
    # Using gemini-2.5-flash as the standard fast/free model for 2026
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    
    payload = {
        "contents": [{"parts": [{"text": UNIVERSAL_PROMPT + "\n\nARTICLE:\n" + prompt_text}]}],
        "generationConfig": {"responseMimeType": "application/json"}
    }
    
    resp = requests.post(url, json=payload)
    if resp.status_code != 200:
        return None, f"Gemini API Error: {resp.text}"
        
    data = resp.json()
    try:
        raw_text = data['candidates'][0]['content']['parts'][0]['text']
        return parse_json_response(raw_text), None
    except Exception as e:
        return None, f"Gemini Parsing Error: {str(e)}"

def call_cloudflare(prompt_text):
    account_id = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
    api_token = os.environ.get("CLOUDFLARE_API_TOKEN")
    if not account_id or not api_token: return None, "Missing Cloudflare Credentials"

    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/@cf/meta/llama-3.1-8b-instruct"
    headers = {"Authorization": f"Bearer {api_token}"}
    
    payload = {
        "messages": [
            {"role": "system", "content": UNIVERSAL_PROMPT},
            {"role": "user", "content": f"Extract intelligence from this article in JSON format only:\n\n{prompt_text}"}
        ]
    }
    
    resp = requests.post(url, headers=headers, json=payload)
    if resp.status_code != 200:
        return None, f"Cloudflare API Error: {resp.text}"
        
    try:
        raw_text = resp.json()['result']['response']
        return parse_json_response(raw_text), None
    except Exception as e:
        return None, f"Cloudflare Parsing Error: {str(e)}"

def call_groq(prompt_text):
    from groq import Groq
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key: return None, "Missing GROQ_API_KEY"
    
    client = Groq(api_key=api_key)
    models = ["openai/gpt-oss-120b", "qwen/qwen3.8-27b", "openai/gpt-oss-20b", "groq/compound"]
    
    for model_name in models:
        try:
            completion = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": UNIVERSAL_PROMPT + "\n\nARTICLE:\n" + prompt_text}],
                temperature=0.1,
                response_format={"type": "json_object"},
                max_tokens=1200
            )
            raw = completion.choices[0].message.content.strip()
            return parse_json_response(raw), model_name
        except Exception as e:
            if "429" in str(e):
                time.sleep(2)
                continue
            return None, f"Groq Error: {str(e)}"
            
    return None, "All Groq models rate limited"

def extract_intelligence(scraped_text):
    cleaned = clean_text(scraped_text)[:3000]
    
    # 1. Try Gemini First (Best free limits: 1500 RPD)
    print("   -> Trying Gemini...")
    result, error = call_gemini(cleaned)
    if result:
        print("   -> Intelligence extracted via Gemini")
        return result, result.get("brief", ""), "gemini-2.5-flash"
    print(f"   -> Gemini failed: {error}")
    
    # 2. Try Cloudflare Fallback (10,000 neurons/day)
    print("   -> Trying Cloudflare Workers AI...")
    result, error = call_cloudflare(cleaned)
    if result:
        print("   -> Intelligence extracted via Cloudflare")
        return result, result.get("brief", ""), "cloudflare/llama-3.1-8b"
    print(f"   -> Cloudflare failed: {error}")
    
    # 3. Try Groq Last Resort
    print("   -> Trying Groq (Last Resort)...")
    result, groq_model_or_err = call_groq(cleaned)
    if result:
        print(f"   -> Intelligence extracted via {groq_model_or_err}")
        return result, result.get("brief", ""), groq_model_or_err
    print(f"   -> Groq failed: {groq_model_or_err}")
    
    print("   -> CRITICAL: All fallback models exhausted.")
    return None, None, None
