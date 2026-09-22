import os
from supabase import create_client
def get_supabase_client():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        print("Warning: Supabase credentials not found.")
        return None
    return create_client(url, key)

def ensure_schema(client):
    """
    Ensures the articles table has all the rich columns we need.
    Uses Supabase RPC to run raw SQL — safe to call every run (idempotent).
    """
    sql = """
    ALTER TABLE articles
      ADD COLUMN IF NOT EXISTS district             TEXT,
      ADD COLUMN IF NOT EXISTS constituency         TEXT,
      ADD COLUMN IF NOT EXISTS local_geography      TEXT,
      ADD COLUMN IF NOT EXISTS parties_involved     TEXT[],
      ADD COLUMN IF NOT EXISTS key_leaders          TEXT[],
      ADD COLUMN IF NOT EXISTS keywords             TEXT[],
      ADD COLUMN IF NOT EXISTS sentiment            TEXT,
      ADD COLUMN IF NOT EXISTS scraped_text         TEXT,
      ADD COLUMN IF NOT EXISTS published_date       DATE,
      ADD COLUMN IF NOT EXISTS sheet_synced         BOOLEAN DEFAULT FALSE;
    """
    try:
        client.rpc("exec_sql", {"query": sql}).execute()
    except Exception:
        pass  # Columns may already exist; non-fatal

def filter_existing_urls(url_list):
    """
    Checks Supabase and returns only URLs that do NOT exist in the database.
    Queries in chunks of 50 to prevent 'URI too long' API errors.
    """
    client = get_supabase_client()
    if not client or not url_list:
        return url_list

    existing_urls = set()
    chunk_size = 50

    try:
        for i in range(0, len(url_list), chunk_size):
            chunk = url_list[i:i + chunk_size]
            response = client.table("articles").select("article_url").in_("article_url", chunk).execute()
            for row in response.data:
                existing_urls.add(row["article_url"])

        new_urls = [u for u in url_list if u not in existing_urls]
        return new_urls
    except Exception as e:
        print(f"Supabase deduplication check failed: {e}")
        return url_list  # Fail-safe

def save_article(record):
    """
    Saves a fully-enriched article record to Supabase.
    Extracts rich fields from raw_json so they are queryable columns
    (not just buried in a JSONB blob).
    """
    client = get_supabase_client()
    if not client:
        return False

    raw = record.get("raw_json", {})

    enriched = {
        "article_url":       record.get("article_url"),
        "source":            record.get("source"),
        "activity_type":     record.get("activity_type"),
        "electoral_relevance": record.get("electoral_relevance"),
        "summary":           record.get("summary", ""),
        "scraped_text":      record.get("scraped_text", ""),
        "district":          raw.get("district"),
        "constituency":      raw.get("constituency"),
        "local_geography":   raw.get("local_geography"),
        "parties_involved":  raw.get("parties_involved", []),
        "key_leaders":       raw.get("key_leaders", []),
        "keywords":          raw.get("keywords", []),
        "sentiment":         raw.get("news_tone"),
        "published_date":    record.get("published_date"),
        "sheet_synced":      record.get("sheet_synced", False),
        "raw_json":          raw,
        "processing_status": "done"
    }

    try:
        res = client.table("articles").insert(enriched).execute()
        if res.data and len(res.data) > 0:
            return res.data[0].get('id')
        return True
    except Exception as e:
        print(f"Failed to save to Supabase: {e}")
        return False
