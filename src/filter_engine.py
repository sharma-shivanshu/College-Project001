import pickle
import os

MODEL_PATH = "relevance_model.pkl"

# Strong indicators of NON-political content
NEGATIVE_KEYWORDS = [
    "weather", "rain", "storm", "cricket", "sports", "bollywood", "murder", "suicide", "accident", "rape", "crime",
    "मौसम", "बारिश", "क्रिकेट", "खेल", "फिल्म", "हत्या", "आत्महत्या", "दुर्घटना", "रेप", "अपराध"
]

# Strong indicators of political/governance content
POSITIVE_KEYWORDS = [
    "election", "bjp", "congress", "sp", "akhilesh", "yogi", "rally", "protest", "government", "scheme", "policy", "mla", "mp", "cm", "pm",
    "चुनाव", "भाजपा", "सपा", "कांग्रेस", "योगी", "अखिलेश", "रैली", "धरना", "सरकार", "योजना", "नीति", "विधायक", "सांसद", "मुख्यमंत्री", "प्रधानमंत्री", "टिकट", "मोर्चा"
]

def is_relevant(text_to_analyze):
    """
    Evaluates relevance based on URL, Title, and Summary BEFORE scraping.
    Returns True if it's likely political. False if irrelevant.
    """
    text_lower = text_to_analyze.lower()
    
    # 1. Instant Reject: Negative Keywords
    for nkw in NEGATIVE_KEYWORDS:
        if nkw in text_lower:
            print(f"   -> Rejected: Found negative keyword '{nkw}'")
            return False

    # 2. ML Model Scoring (If available)
    ml_score = 0
    if os.path.exists(MODEL_PATH):
        try:
            with open(MODEL_PATH, "rb") as f:
                model = pickle.load(f)
            probs = model.predict_proba([text_lower])
            ml_score = probs[0][1] if len(probs[0]) > 1 else 0
        except Exception as e:
            pass # Fail silently if model loading fails
            
    # 3. Positive Keyword Density
    keyword_count = sum(1 for kw in POSITIVE_KEYWORDS if kw in text_lower)
    
    if ml_score > 0.6 or keyword_count >= 1:
        return True
        
    print(f"   -> Rejected: No political keywords found and ML score low ({ml_score:.2f})")
    return False
