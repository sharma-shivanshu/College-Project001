"""
Intelligence Processing Pipeline
Runs independently of the scraping pipeline.
Triggered by cron-job.org at odd hours IST (01:00, 03:00, 05:00... 23:00),
interleaved with scraping at even hours to balance Groq token usage.

Logic:
1. Query Supabase for articles with scraped_text but no intelligence_brief
   (status = 'done', retry_count < 3)
2. Process in batches of 25 per run (token budget ~500 tokens × 25 = 12,500 tokens)
3. On success: mark status = 'complete', write intelligence_brief to Supabase + Sheets
4. On error: increment retry_count, mark status = 'intelligence_error' after 3 failures
5. Sorts by published_date DESC so newest articles get processed first (no stale backlog)
"""

import os
import json
import time
import sys
from datetime import datetime, timedelta
from database import get_supabase_client
from intelligence_extractor import extract_intelligence

try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
    SHEETS_AVAILABLE = True
except ImportError:
    SHEETS_AVAILABLE = False

SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID", "1MlBvANu6ePWqQSWT9GlQbG0ZhrIm8_yvGTiE1_KeztE")
BATCH_SIZE = 25
INTELLIGENCE_BRIEF_COL_LETTER = "O"  # Column O in Sheets
INTELLIGENCE_BRIEF_COL_INDEX = 15    # 0-indexed = column 15 = O


def get_sheets_client_and_map(spreadsheet_id):
    """
    Returns a gspread client + a dict mapping {article_url: (worksheet, row_number)}
    by scanning today's and yesterday's tabs.
    """
    if not SHEETS_AVAILABLE:
        return None, {}

    creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    if not creds_json:
        return None, {}

    try:
        creds_dict = json.loads(creds_json)
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        from oauth2client.service_account import ServiceAccountCredentials
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        gc = gspread.authorize(creds)
        ss = gc.open_by_key(spreadsheet_id)

        url_map = {}  # {url: (worksheet_obj, row_number)}

        # Determine news-day tabs to scan (today + yesterday in IST)
        now_utc = datetime.utcnow()
        ist_hour = (now_utc.hour + 5) % 24
        if ist_hour < 5:
            base_date = now_utc - timedelta(days=1)
        else:
            base_date = now_utc
        tabs_to_check = [
            base_date.strftime("%d-%b-%Y"),
            (base_date - timedelta(days=1)).strftime("%d-%b-%Y"),
            (base_date - timedelta(days=2)).strftime("%d-%b-%Y"),
        ]

        for tab_name in tabs_to_check:
            try:
                ws = ss.worksheet(tab_name)
                all_values = ws.get_all_values()
                if not all_values:
                    continue
                
                headers = all_values[0]
                try:
                    url_idx = headers.index("Link")
                    brief_idx = headers.index("Intelligence Brief")
                except ValueError:
                    continue # Headers missing, skip tab
                    
                for i, row in enumerate(all_values):
                    if i == 0:
                        continue  # skip header
                    if len(row) > url_idx and row[url_idx]:
                        url = row[url_idx].strip()
                        if url and url not in url_map:
                            # gspread is 1-indexed, so brief_idx + 1
                            url_map[url] = (ws, i + 1, brief_idx + 1)
            except Exception:
                pass

        print(f"Sheet URL map built: {len(url_map)} articles found across tabs.")
        return gc, url_map

    except Exception as e:
        print(f"Sheets auth failed: {e}")
        return None, {}


def update_sheet_intelligence(url_map, article_url, brief_text):
    """Update the Intelligence Brief column of the existing row for this article."""
    if article_url not in url_map:
        return False
    ws, row_num, brief_col = url_map[article_url]
    try:
        ws.update_cell(row_num, brief_col, brief_text)
        return True
    except Exception as e:
        print(f"   -> Sheet update failed for row {row_num}: {e}")
        return False


def fetch_pending_articles(client, batch_size):
    """
    Fetch articles that need intelligence processing.
    Uses article_url as the primary key (no 'id' column in this table).
    """
    try:
        response = (
            client.table("articles")
            .select("article_url, scraped_text, source, published_date, retry_count")
            .not_.is_("scraped_text", "null")
            .is_("intelligence_brief", "null")
            .neq("processing_status", "complete")
            .lte("retry_count", 2)
            .order("published_date", desc=True)
            .limit(batch_size)
            .execute()
        )
        return response.data or []
    except Exception as e:
        print(f"Failed to fetch pending articles: {e}")
        return []


def mark_article_done(client, article_url, intelligence_json, brief_text):
    try:
        client.table("articles").update({
            "intelligence_brief": brief_text,
            "intelligence_json": intelligence_json,
            "processing_status": "complete",
            "retry_count": 0
        }).eq("article_url", article_url).execute()
        return True
    except Exception as e:
        print(f"   -> Supabase update failed: {e}")
        return False


def mark_article_error(client, article_url, current_retry_count):
    new_count = (current_retry_count or 0) + 1
    status = "intelligence_error" if new_count >= 3 else "done"
    try:
        client.table("articles").update({
            "retry_count": new_count,
            "processing_status": status
        }).eq("article_url", article_url).execute()
    except Exception as e:
        print(f"   -> Failed to mark error: {e}")



def ensure_intelligence_columns(client):
    """Add new columns to Supabase if they don't exist."""
    sql_statements = [
        "ALTER TABLE articles ADD COLUMN IF NOT EXISTS intelligence_brief TEXT;",
        "ALTER TABLE articles ADD COLUMN IF NOT EXISTS intelligence_json JSONB;",
        "ALTER TABLE articles ADD COLUMN IF NOT EXISTS retry_count INTEGER DEFAULT 0;",
    ]
    for sql in sql_statements:
        try:
            client.rpc("exec_sql", {"query": sql}).execute()
        except Exception:
            pass  # Non-fatal if already exists


def run_intelligence_pipeline():
    print("=" * 65)
    print(f"Intelligence Pipeline — {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 65)

    client = get_supabase_client()
    if not client:
        print("ERROR: No Supabase connection. Exiting.")
        sys.exit(1)

    # Ensure schema is up to date
    ensure_intelligence_columns(client)

    pending = fetch_pending_articles(client, BATCH_SIZE)
    print(f"Found {len(pending)} articles pending intelligence processing.")

    if not pending:
        print("Nothing to process. Pipeline complete.")
        return

    # Build Google Sheets URL map once (efficient — single API call per tab)
    _, url_map = get_sheets_client_and_map(SPREADSHEET_ID)

    success_count = 0
    error_count = 0

    for article in pending:
        url = article["article_url"]
        scraped_text = article.get("scraped_text", "")
        retry_count = article.get("retry_count", 0)

        print(f"\n[{success_count + error_count + 1}/{len(pending)}] {url[:80]}...")

        if not scraped_text or len(scraped_text) < 50:
            print("   -> Scraped text too short. Skipping.")
            mark_article_error(client, url, retry_count)
            error_count += 1
            continue

        intel_json, brief_text, model_used = extract_intelligence(scraped_text)

        if not intel_json or not brief_text:
            print("   -> Intelligence extraction failed. Marking for retry.")
            mark_article_error(client, url, retry_count)
            error_count += 1
            continue

        saved = mark_article_done(client, url, intel_json, brief_text)
        if not saved:
            error_count += 1
            continue

        sheet_updated = update_sheet_intelligence(url_map, url, brief_text)
        if sheet_updated:
            print(f"   -> Supabase ✓ | Sheets ✓ | Model: {model_used}")
        else:
            print(f"   -> Supabase ✓ | Sheets: URL not in recent tabs | Model: {model_used}")

        success_count += 1
        time.sleep(1.5)


    print(f"\n{'=' * 65}")
    print(f"Intelligence Pipeline Complete.")
    print(f"  Processed: {success_count} ✓ | Errors: {error_count} ✗")
    print(f"  Remaining in queue: {len(pending) - success_count - error_count}")
    print(f"{'=' * 65}")


if __name__ == "__main__":
    run_intelligence_pipeline()
