import os
import json
import re
import gspread
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
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        print(f"Failed to authorize Google Sheets: {e}")
        return None

def append_to_sheet(raw_spreadsheet_id, data_row):
    client = get_sheets_client()
    if not client: return False
    
    sheet_id = extract_sheet_id(raw_spreadsheet_id)
    
    try:
        sheet = client.open_by_key(sheet_id).sheet1
        # Use table_range="A1" to force it to align to the very first column, preventing blank spacing issues
        sheet.append_row(data_row, table_range="A1")
        print("   -> Successfully synced to Google Sheets!")
        return True
    except Exception as e:
        print(f"   -> Failed to append to sheet: {e}")
        return False
