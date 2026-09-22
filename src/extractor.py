import os
import json
import time
import re
import random
import google.generativeai as genai

SCHEMA = '''{
  "activity_type": "rally|statement|government_scheme|inauguration|protest|appointment|election_event|other",
  "electoral_relevance": "high|medium|low|none",
  "district": "Name of the UP district. If it affects all of UP, use 'Uttar Pradesh (State)'. If it is national context, use 'National'. Else null",
  "constituency": "Name of specific UP assembly constituency if mentioned, or null",
  "local_geography": "Specific village, block, ward, or tehsil mentioned, or null",
  "parties_involved": ["list of standardized party names (e.g. BJP, SP, BSP, INC)"],
  "key_leaders": ["list of major politicians mentioned"],
  "keywords": ["list of 3 to 5 highly relevant political/event tags. Must include party aliases/leaders, do NOT include general terms like 'government' or 'opposition'"],
  "news_tone": "Development|Controversy|Crime & Law|Policy & Politics|Human Interest",
  "summary": "1 sentence max"
}'''

PARTY_MAPPING = """
Use these exact abbreviations for 'parties_involved' if any of their leaders or aliases are mentioned:
- BJP: भाजपा, Bharatiya Janata Party, Rajnath Singh, Yogi Adityanath, Pankaj Chaudhary, Dharampal Singh, Bhupendra Chaudhary, Keshav Prasad Maurya, Brajesh Pathak, Satish Mahana, Suresh Khanna, Pankaj Singh
- RLD: रालोद, Rashtriya Lok Dal, Jayant Chaudhary, Chaudhary Charan Singh, Ajit Singh, Charu Singh, Chandan Chauhan, Gulam Mohammad, Madan Bhaiya, Anil Kumar, Rajkumar Sangwan, Rajpal Singh Balyan, Ashraf Ali Khan
- AD(S): अपना दल (सोनेलाल), Apna Dal (Sonelal), Anupriya Patel, Ashish Patel, Vachaspati Saroj, Jai Kumar Singh Jaiki, RK Patel, Rinki Kol
- SBSP: सुभसपा, Suheldev Bharatiya Samaj Party, Om Prakash Rajbhar, Arvind Rajbhar, Abbas Ansari, Hansu Ram, Bedi Ram
- NISHAD: निषाद, Nirbal Indian Shoshit Hamara Aam Dal, Sanjay Nishad, Praveen Nishad, Anil Kumar Tripathi, Rishi Tripathi, Ramesh Singh, Vipul Dubey, Vivekanand Pandey
- SP: सपा, Samajwadi Party, Mata Prasad Pandey, Shivpal Yadav, Dharmendra Yadav, Akhilesh Yadav, Awdhesh Prasad, Tej Pratap Yadav, Dimple Yadav, Mulayam Singh Yadav, Iqra Hasan
- INC: कांग्रेस, Congress, Ajay Rai, Rahul Gandhi, Priyanka Gandhi, Kishori Lal Sharma, Tanuj Punia, Rakesh Rathore, Imran Masood, Ujjawal Raman Singh, Pramod Tiwari, Aradhna Mishra Mona, Revati Raman Singh, Virendra Chaudhary
- BSP: बसपा, Bahujan Samaj Party, Mayawati, Vishwanath Pal, Akash Anand, Umashankar Singh, Satish Mishra
- ASP: असपा, Azad Samaj Party, Bhim Army, Chandrashekhar Azad
- AD(K): अपना दल (कमेरावादी), Apna Dal (Kamerawadi), Pallavi Patel, Krishna Patel
- PECP: पीस पार्टी, Peace Party, Dr Ayyub Khan
- AIMIM: अमीम, All India Majlis-e-Ittehadul Muslimeen, Asaduddin Owaisi, Shaukat Ali
- IEMC: आइएमसी, Ittehad-e-Millat Council, Maulana Taukeer Raza Khan
- AAP: आप, Aam Aadmi Party, Sanjay Singh
"""

def clean_text(text):
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\{.*?\}', '', text) 
    return text.strip()

def extract_entities(text):
    keys_str = os.environ.get("GEMINI_API_KEYS", os.environ.get("GEMINI_API_KEY", ""))
    if not keys_str: return None
    
    keys = [k.strip() for k in keys_str.split(',') if k.strip()]
    if not keys: return None
    
    # Pick a random key for load balancing
    api_key = random.choice(keys)
    genai.configure(api_key=api_key)
    
    # Use Gemini Flash which is very fast and cheap
    model = genai.GenerativeModel('gemini-1.5-flash-latest', generation_config={"response_mime_type": "application/json"})
    
    cleaned_text = clean_text(text)
    truncated_text = cleaned_text[:3000] # Increased context window since Gemini supports it
    
    prompt = f"Analyze this political article from Uttar Pradesh. Extract data EXACTLY matching this JSON schema. Return ONLY a valid JSON object.\n\nMAPPING RULES:\n{PARTY_MAPPING}\n\nSCHEMA:\n{SCHEMA}\n\nTEXT:\n{truncated_text}"
    
    try:
        response = model.generate_content(prompt)
        raw = response.text.strip()
        
        # Strip potential markdown formatting if Gemini includes it despite JSON mime type
        if raw.startswith("```json"): raw = raw[7:]
        if raw.startswith("```"): raw = raw[3:]
        if raw.endswith("```"): raw = raw[:-3]
        
        parsed = json.loads(raw.strip())
        return parsed
    except Exception as e:
        print(f"Gemini Extraction Error: {e}")
        return None

