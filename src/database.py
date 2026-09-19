import os
from supabase import create_client

def get_supabase_client():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        print("Warning: Supabase credentials not found.")
        return None
    return create_client(url, key)

def filter_existing_urls(url_list):
    """
    Checks Supabase and returns only the URLs that do NOT exist in the database.
    Queries in chunks of 50 to prevent 'URI too long' API errors.
    """
    client = get_supabase_client()
    if not client or not url_list:
        return url_list
        
    existing_urls = set()
    chunk_size = 50
    
    try:
        for i in range(0, len(url_list), chunk_size):
            chunk = url_list[i:i+chunk_size]
            response = client.table("articles").select("article_url").in_("article_url", chunk).execute()
            for row in response.data:
                existing_urls.add(row["article_url"])
                
        new_urls = [u for u in url_list if u not in existing_urls]
        return new_urls
    except Exception as e:
        print(f"Supabase deduplication check failed: {e}")
        return url_list # Fail safe: return all to let pre-filter handle it

def save_article(record):
    client = get_supabase_client()
    if not client: return False
    
    try:
        client.table("articles").insert(record).execute()
        return True
    except Exception as e:
        print(f"Failed to save to Supabase: {e}")
        return False
