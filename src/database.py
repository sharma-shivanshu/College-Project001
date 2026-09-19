import os
from supabase import create_client, Client

def get_supabase_client() -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        print("Warning: Supabase credentials missing!")
        return None
    return create_client(url, key)

def filter_existing_urls(urls):
    """
    Given a list of URLs, queries Supabase and returns a list of URLs 
    that DO NOT already exist in the database. This prevents redundancy.
    """
    supabase = get_supabase_client()
    if not supabase or not urls:
        return urls
        
    try:
        # Fetch existing URLs from our database that match the batch
        # Assuming table is 'articles' and column is 'article_url'
        response = supabase.table("articles").select("article_url").in_("article_url", urls).execute()
        existing_urls = set(row["article_url"] for row in response.data)
        
        # Return only the URLs that are completely new
        new_urls = [url for url in urls if url not in existing_urls]
        print(f"Deduplication: {len(urls)} total -> {len(new_urls)} new articles.")
        return new_urls
    except Exception as e:
        print(f"Supabase deduplication check failed: {e}")
        return urls

def save_article(article_data):
    """
    Saves the extracted article JSON to Supabase.
    """
    supabase = get_supabase_client()
    if not supabase: return False
    
    try:
        supabase.table("articles").insert(article_data).execute()
        return True
    except Exception as e:
        print(f"Failed to save to Supabase: {e}")
        return False
