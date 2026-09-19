import os
import json
import re
import gspread
from oauth2client.service_account import ServiceAccountCredentials

def extract_sheet_id(spreadsheet_string):
    # If the user accidentally pasted the full URL, extract just the ID
    match = re.search(r'/d/([a-zA-Z0-9-_]+)', spreadsheet_string)
    if match:
        return match.group(1)
    return spreadsheet_string # Assume it's already the ID

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

def append_to_sheet(raw_spreadsheet_id, data_row):
    client = get_sheets_client()
    if not client: return False
    
    sheet_id = extract_sheet_id(raw_spreadsheet_id)
    
    try:
        sheet = client.open_by_key(sheet_id).sheet1
        sheet.append_row(data_row)
        print("Successfully synced to Google Sheets!")
        return True
    except gspread.exceptions.APIError as e:
        print(f"Failed to append to sheet (API Error): {e}")
        if "404" in str(e):
            print("ERROR 404: The Spreadsheet ID is wrong, OR you forgot to click 'Share' in Google Sheets and share it with 'access-to-ai@access-to-ai.iam.gserviceaccount.com' as an Editor!")
        return False
    except Exception as e:
        print(f"Failed to append to sheet: {e}")
        return False
