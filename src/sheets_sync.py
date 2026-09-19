import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials

def get_sheets_client():
    creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    if not creds_json:
        print("Warning: GOOGLE_CREDENTIALS not found.")
        return None
        
    try:
        creds_dict = json.loads(creds_json)
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        print(f"Failed to authorize Google Sheets: {e}")
        return None

def append_to_sheet(spreadsheet_id, data_row):
    client = get_sheets_client()
    if not client: return False
    
    try:
        sheet = client.open_by_key(spreadsheet_id).sheet1
        sheet.append_row(data_row)
        return True
    except Exception as e:
        print(f"Failed to append to sheet: {e}")
        return False
