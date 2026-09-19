import os
import json
import re
import gspread
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials

def extract_sheet_id(spreadsheet_string):
    match = re.search(r'/d/([a-zA-Z0-9-_]+)', spreadsheet_string)
    if match: return match.group(1)
    return spreadsheet_string 

def get_sheets_client():
    creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    if not creds_json: return None
    try:
        creds_dict = json.loads(creds_json)
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        return gspread.authorize(creds)
    except Exception as e:
        print(f"Failed to authorize Google Sheets: {e}")
        return None

def append_to_sheet(raw_spreadsheet_id, data_row):
    client = get_sheets_client()
    if not client: return False
    
    sheet_id = extract_sheet_id(raw_spreadsheet_id)
    today_str = datetime.now().strftime("%d-%b-%Y") # E.g., 19-Sep-2026
    
    try:
        spreadsheet = client.open_by_key(sheet_id)
        
        # 1. Get or Create today's worksheet
        try:
            worksheet = spreadsheet.worksheet(today_str)
        except gspread.exceptions.WorksheetNotFound:
            print(f"   -> Creating new tab for {today_str}...")
            worksheet = spreadsheet.add_worksheet(title=today_str, rows=1000, cols=15)
            
            # 2. Add Polished Headers
            headers = [
                "Post Date", "Post Time", "Link", "Source", "Activity Type", 
                "Political Relevance", "District", "Constituency", "Local Geography", 
                "Key Leaders", "Keywords", "Summary", "Scraped Content"
            ]
            worksheet.append_row(headers, table_range="A1")
            
            # 3. Format Headers (Bold + Frozen)
            worksheet.freeze(rows=1)
            worksheet.format("A1:M1", {
                "backgroundColor": {"red": 0.9, "green": 0.9, "blue": 0.9},
                "textFormat": {"bold": True, "fontSize": 11}
            })
            
        # 4. Append Data
        worksheet.append_row(data_row, table_range="A1")
        print("   -> Successfully synced to Google Sheets!")
        return True
    except Exception as e:
        print(f"   -> Failed to append to sheet: {e}")
        return False
