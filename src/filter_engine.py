import pickle
import os
import re

# Load the ML Model
MODEL_PATH = "relevance_model.pkl"

def is_relevant(text, title=""):
    # 1. Evaluate with the PKL Model
    ml_score = 0
    if os.path.exists(MODEL_PATH):
        try:
            with open(MODEL_PATH, "rb") as f:
                model = pickle.load(f)
            # Assuming it's a binary classifier where class 1 is relevant
            probs = model.predict_proba([text])
            ml_score = probs[0][1] if len(probs[0]) > 1 else 0
        except Exception as e:
            print(f"Model evaluation failed: {e}")
            
    # 2. PnC Keyword Logic
    keywords = ["विधायक", "सांसद", "चुनाव", "भाजपा", "सपा", "कांग्रेस", "bjp", "sp", "congress", "protest", "policy", "scheme"]
    keyword_count = sum(1 for kw in keywords if kw.lower() in text.lower() or kw.lower() in title.lower())
    
    # Threshold logic: Must have a decent ML score OR high keyword density
    if ml_score > 0.6 or keyword_count >= 2:
        return True
    return False
