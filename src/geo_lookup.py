# UP District and Tehsil mapping
# This resolves sub-district/tehsil names to their parent district to fix AI geo-tagging bugs.

UP_DISTRICTS = {
    "Agra", "Aligarh", "Ambedkar Nagar", "Amethi", "Amroha", "Auraiya", "Ayodhya",
    "Azamgarh", "Baghpat", "Bahraich", "Ballia", "Balrampur", "Banda", "Barabanki",
    "Bareilly", "Basti", "Bhadohi", "Bijnor", "Budaun", "Bulandshahar", "Chandauli",
    "Chitrakoot", "Deoria", "Etah", "Etawah", "Farrukhabad", "Fatehpur", "Firozabad",
    "Gautam Buddha Nagar", "Ghaziabad", "Ghazipur", "Gonda", "Gorakhpur", "Hamirpur",
    "Hapur", "Hardoi", "Hathras", "Jalaun", "Jaunpur", "Jhansi", "Kannauj",
    "Kanpur Dehat", "Kanpur Nagar", "Kasganj", "Kaushambi", "Kushinagar",
    "Lakhimpur Kheri", "Lalitpur", "Lucknow", "Maharajganj", "Mahoba", "Mainpuri",
    "Mathura", "Mau", "Meerut", "Mirzapur", "Moradabad", "Muzaffarnagar", "Pilibhit",
    "Pratapgarh", "Prayagraj", "Raebareli", "Rampur", "Saharanpur", "Sambhal",
    "Sant Kabir Nagar", "Shahjahanpur", "Shamli", "Shravasti", "Siddharthnagar",
    "Sitapur", "Sonbhadra", "Sultanpur", "Unnao", "Varanasi"
}

# A curated list of tehsils/blocks/areas mapping to their parent district.
# This prevents the AI from tagging an article about "Maharajganj area in Jaunpur" as "Maharajganj district".
SUB_DISTRICT_MAP = {
    # Jaunpur tehsils/areas
    "maharajganj": "Jaunpur", # The specific conflict mentioned
    "badlapur": "Jaunpur",
    "shahganj": "Jaunpur",
    "machhlishahr": "Jaunpur",
    "mariyahu": "Jaunpur",
    "kerakat": "Jaunpur",
    "zafrabad": "Jaunpur",
    "mungra badshahpur": "Jaunpur",
    
    # Lucknow tehsils
    "malihabad": "Lucknow",
    "bakshi ka talab": "Lucknow",
    "sarojini nagar": "Lucknow",
    "mohanlalganj": "Lucknow",

    # Varanasi tehsils
    "pindra": "Varanasi",
    "rajatala": "Varanasi",
    "sevapuri": "Varanasi",
    "rohaniya": "Varanasi",

    # Prayagraj (Allahabad) tehsils
    "soraon": "Prayagraj",
    "phulpur": "Prayagraj",
    "handia": "Prayagraj",
    "meja": "Prayagraj",
    "karachhana": "Prayagraj",
    "bara": "Prayagraj",
    "koraon": "Prayagraj",
    "karchhana": "Prayagraj",

    # Kanpur Nagar / Dehat tehsils
    "bilhaur": "Kanpur Nagar",
    "bithoor": "Kanpur Nagar",
    "kalyanpur": "Kanpur Nagar",
    "govindnagar": "Kanpur Nagar",
    "sishamau": "Kanpur Nagar",
    "ghatampur": "Kanpur Nagar",
    "rasulabad": "Kanpur Dehat",
    "akbarpur - raniya": "Kanpur Dehat",
    "sikandra": "Kanpur Dehat",
    "bhognipur": "Kanpur Dehat",

    # Gorakhpur tehsils
    "campierganj": "Gorakhpur",
    "sahajanwa": "Gorakhpur",
    "chauri chaura": "Gorakhpur",
    "bansgaon": "Gorakhpur",
    "khajani": "Gorakhpur",
    "gola": "Gorakhpur",
    
    # Meerut tehsils
    "sardhana": "Meerut",
    "mawana": "Meerut",

    # Agra tehsils
    "etmadpur": "Agra",
    "kheragarh": "Agra",
    "fatehabad": "Agra",
    "bah": "Agra",
    "kiraoli": "Agra",

    # Add other highly conflicting or common tehsils below as needed
    "tundla": "Firozabad",
    "shikohabad": "Firozabad",
    "sirsaganj": "Firozabad",
    "jasrana": "Firozabad",
    
    "biswan": "Sitapur",
    "mahmoodabad": "Sitapur",
    "laharpur": "Sitapur",
    "misrikh": "Sitapur",

    "powayan": "Shahjahanpur",
    "tilhar": "Shahjahanpur",
    "jalalabad": "Shahjahanpur",

    "nighasan": "Lakhimpur Kheri",
    "palia": "Lakhimpur Kheri",
    "gola gokrannath": "Lakhimpur Kheri",
    "mohammdi": "Lakhimpur Kheri",
    "dhaurahra": "Lakhimpur Kheri",

    "najibabad": "Bijnor",
    "chandpur": "Bijnor",
    "dhampur": "Bijnor",
    "nagina": "Bijnor",
    
    "kairana": "Shamli",
    "thana bhawan": "Shamli",
    
    "deoband": "Saharanpur",
    "nakur": "Saharanpur",
    "behat": "Saharanpur",
    
    "kunda": "Pratapgarh",
    "patti": "Pratapgarh",
    "raniganj": "Pratapgarh",
    "lalganj": "Azamgarh",  # Note: Lalganj is also in Raebareli, but context usually helps. We'll map to Azamgarh as default, but we should rely on the text check.
    "mehnagar": "Azamgarh",
    "sagri": "Azamgarh",
}

# Load the constituency map from frontend to augment our lookup
import json
import os

def load_constituencies():
    path = "/Users/shivanshusharma/Documents/AGY_Projects/Jan_Ki_Awaz/prototype/frontend/district_mapping.json"
    if os.path.exists(path):
        with open(path, 'r') as f:
            mapping = json.load(f)
            for dist, consts in mapping.items():
                for c in consts:
                    c_clean = c.replace("(SC)", "").replace("(ST)", "").strip().lower()
                    if c_clean not in SUB_DISTRICT_MAP and c_clean not in [d.lower() for d in UP_DISTRICTS]:
                        SUB_DISTRICT_MAP[c_clean] = dist

load_constituencies()

def normalize(name):
    if not name: return ""
    return name.lower().replace(" district", "").replace("nagar", " nagar").strip()

def resolve_district(extracted_district, text_content):
    """
    Given the district extracted by AI, verify it.
    If it's not a real 75 district, check if it's a tehsil/sub-district.
    If it is a real district, but the text explicitly talks about it in the context of ANOTHER district 
    (e.g. "Maharajganj area of Jaunpur"), override it.
    """
    if not extracted_district:
        return None, None
        
    ext_norm = normalize(extracted_district)
    text_lower = text_content.lower()
    
    # 1. Check for conflicting names where a District name is used as a Tehsil in another District.
    # Example: "Maharajganj" is a District, but also a Tehsil in Jaunpur.
    conflict_overrides = {
        "maharajganj": {"parent": "Jaunpur", "keyword": "jaunpur"},
        "lalganj": {"parent": "Raebareli", "keyword": "raebareli"},
    }
    
    if ext_norm in conflict_overrides:
        rule = conflict_overrides[ext_norm]
        # If the parent district is mentioned in the text, it's likely the sub-district!
        if rule["keyword"] in text_lower:
            return rule["parent"], extracted_district

    # 2. If it exactly matches one of the 75 districts, accept it.
    for d in UP_DISTRICTS:
        if normalize(d) == ext_norm:
            return d, None
            
    # 3. If it's not a known district, check if it's a known tehsil/constituency.
    if ext_norm in SUB_DISTRICT_MAP:
        return SUB_DISTRICT_MAP[ext_norm], extracted_district
        
    # 4. Try partial matching inside the sub-district map
    for sub, parent in SUB_DISTRICT_MAP.items():
        if sub in ext_norm or ext_norm in sub:
            return parent, extracted_district
            
    # 5. Fallback: just return what the AI said, hoping it's a weird spelling of a district.
    # (Capitalize first letters for cleanliness)
    return extracted_district.title(), None
