"""
Universal Political Intelligence Extractor
Handles 12+ event types: rally, press conference, government scheme, protest,
appointment, alliance talks, election prep, condolence, inauguration, legal/court,
caste outreach, party internal matters.

Uses Groq with 5-model fallback. Produces structured JSON + English paraphrase brief.
The brief is an original AI-generated work (fact extraction + paraphrase), NOT a
translation or summary — fully legal under Indian and international IP law.
"""

import os
import json
import time
import re
from groq import Groq

FALLBACK_MODELS = [
    "openai/gpt-oss-120b",    # 120B — primary, best quality
    "qwen/qwen3.8-27b",       # 27B — excellent Hindi comprehension
    "openai/gpt-oss-20b",     # 20B — fast, independent quota
    "groq/compound",           # Groq native, independent quota
    "groq/compound-mini",      # Last resort, independent quota
]

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
  "brief": "3-4 sentence English intelligence brief. Must be YOUR OWN paraphrase covering: what happened, who was involved (with designations), where, key claims or significance. Do NOT start with 'The article says'. Write as an analyst briefing a minister."
}

ARTICLE:
"""


def get_groq_client():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return None
    return Groq(api_key=api_key)


def clean_text(text):
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def extract_intelligence(scraped_text):
    """
    Runs the universal intelligence extraction prompt against all fallback models.
    Returns (intelligence_json, brief_text, model_used) or (None, None, None) on full failure.
    """
    client = get_groq_client()
    if not client:
        return None, None, None

    cleaned = clean_text(scraped_text)
    # Use up to 3000 chars — enough for all key facts, well within token budget
    truncated = cleaned[:3000]
    full_prompt = UNIVERSAL_PROMPT + truncated

    for model_name in FALLBACK_MODELS:
        try:
            completion = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": full_prompt}],
                temperature=0.1,
                response_format={"type": "json_object"},
                max_tokens=1200
            )
            raw = completion.choices[0].message.content.strip()
            parsed = json.loads(raw)
            brief = parsed.get("brief", "")
            print(f"   -> Intelligence extracted via {model_name}")
            return parsed, brief, model_name

        except Exception as e:
            err = str(e).lower()
            if any(x in err for x in ["429", "rate limit", "tokens", "quota"]):
                print(f"   -> Rate limited on {model_name}. Error: {str(e)[:200]}")
                time.sleep(5) # Increase sleep to 5s between models
                continue
            elif "400" in err or "decommission" in err:
                print(f"   -> Model {model_name} unavailable. Trying next...")
                continue
            else:
                print(f"   -> Extraction error on {model_name}: {e}")
                continue

    print("   -> CRITICAL: All models exhausted for this article.")
    return None, None, None
