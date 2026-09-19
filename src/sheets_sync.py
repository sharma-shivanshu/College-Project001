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
    # "News day" logic: before 5:30 AM IST (UTC+5:30 = 00:00 UTC), articles still belong
    # to the previous calendar day because newspapers publish the night's content overnight.
    now_ist = datetime.utcnow()
    # Offset to IST manually (no pytz needed)
    ist_hour = (now_ist.hour + 5) % 24
    ist_minute = (now_ist.minute + 30) % 60
    if ist_hour < 5 or (ist_hour == 5 and ist_minute == 0):
        from datetime import timedelta
        news_day = datetime.utcnow() - timedelta(days=1)
    else:
        news_day = datetime.utcnow()
    today_str = news_day.strftime("%d-%b-%Y")

    
    try:
        spreadsheet = client.open_by_key(sheet_id)
        
        try:
            worksheet = spreadsheet.worksheet(today_str)
        except gspread.exceptions.WorksheetNotFound:
            print(f"   -> Creating new tab for {today_str}...")
            worksheet = spreadsheet.add_worksheet(title=today_str, rows=1000, cols=16)
            
            headers = [
                "Post Date", "Post Time", "Link", "Source", "Activity Type", 
                "Political Relevance", "District", "Constituency", "Local Geography", 
                "Parties Involved", "Key Leaders", "Keywords", "Summary", "Scraped Content"
            ]
            worksheet.append_row(headers, table_range="A1")
            
            worksheet.freeze(rows=1)
            worksheet.format("A1:N1", {
                "backgroundColor": {"red": 0.9, "green": 0.9, "blue": 0.9},
                "textFormat": {"bold": True, "fontSize": 11}
            })
            
        worksheet.append_row(data_row, table_range="A1")
        print("   -> Successfully synced to Google Sheets!")
        return True
    except Exception as e:
        print(f"   -> Failed to append to sheet: {e}")
        return False
