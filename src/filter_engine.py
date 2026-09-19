import re

# Integrated the massive list of specific leaders and parties requested by the user to guarantee they pass the pre-filter
POSITIVE_KEYWORDS_REGEX = r'\b(bjp|sp|bsp|rld|inc|congress|samajwadi|bahujan|aap|aimim|ad\(s\)|sbsp|nishad|asp|ad\(k\)|pecp|iemc)\b'
POSITIVE_HINDI_REGEX = r'(भाजपा|सपा|बसपा|कांग्रेस|रालोद|सुभसपा|निषाद|असपा|अमीम|आइएमसी|आप|चुनाव|मतदान|विधायक|सांसद|मुख्यमंत्री|मंत्री|राजनीति|रैली|गठबंधन|सीट|उम्मीदवार|टिकट|वोट|सरकार|योजना|विपक्ष|प्रदर्शन|धरना|नियुक्ति)'

LEADERS_REGEX = r'(rajnath singh|yogi adityanath|pankaj chaudhary|dharampal singh|bhupendra chaudhary|keshav prasad maurya|brajesh pathak|satish mahana|suresh khanna|pankaj singh|jayant chaudhary|chaudhary charan singh|ajit singh|charu singh|chandan chauhan|gulam mohammad|madan bhaiya|anil kumar|rajkumar sangwan|rajpal singh balyan|ashraf ali khan|anupriya patel|ashish patel|vachaspati saroj|jai kumar singh jaiki|rk patel|rinki kol|om prakash rajbhar|arvind rajbhar|abbas ansari|hansu ram|bedi ram|sanjay nishad|praveen nishad|anil kumar tripathi|rishi tripathi|ramesh singh|vipul dubey|vivekanand pandey|mata prasad pandey|shivpal yadav|dharmendra yadav|akhilesh yadav|awdhesh prasad|tej pratap yadav|dimple yadav|mulayam singh yadav|iqra hasan|ajay rai|rahul gandhi|priyanka gandhi|kishori lal sharma|tanuj punia|rakesh rathore|imran masood|ujjawal raman singh|pramod tiwari|aradhna mishra mona|revati raman singh|virendra chaudhary|mayawati|vishwanath pal|akash anand|umashankar singh|satish mishra|bhim army|chandrashekhar azad|pallavi patel|krishna patel|dr ayyub khan|asaduddin owaisi|shaukat ali|maulana taukeer raza khan|sanjay singh)'

NEGATIVE_KEYWORDS_REGEX = r'\b(rape|murder|suicide|killed|accident|crash|sports|cricket|weather|bollywood|movie|review|recipe|fashion)\b'
NEGATIVE_HINDI_REGEX = r'(हत्या|बलात्कार|सुसाइड|हादसा|खेल|क्रिकेट|मौसम|बॉलीवुड|रेसिपी|फैशन|दुर्घटना)'

def is_relevant(text):
    text_lower = text.lower()
    
    # 1. Reject if negative keywords found
    if re.search(NEGATIVE_KEYWORDS_REGEX, text_lower) or re.search(NEGATIVE_HINDI_REGEX, text_lower):
        return False
        
    # 2. Accept if specific leader is mentioned
    if re.search(LEADERS_REGEX, text_lower):
        return True
        
    # 3. Accept if political keywords/parties found
    if re.search(POSITIVE_KEYWORDS_REGEX, text_lower) or re.search(POSITIVE_HINDI_REGEX, text_lower):
        return True
        
    return False
