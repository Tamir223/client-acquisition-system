import os
import json
from datetime import datetime

def append_lead_to_sheet(sheet_id, lead_data):
    """
    Appends a lead row to the client's Google Sheet.
    No-op if GOOGLE_SERVICE_ACCOUNT_JSON is not configured.
    """
    creds_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not creds_json or not sheet_id:
        return

    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        creds_dict = json.loads(creds_json)
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        credentials = service_account.Credentials.from_service_account_info(
            creds_dict, scopes=scopes
        )
        service = build("sheets", "v4", credentials=credentials, cache_discovery=False)

        row = [
            datetime.now().strftime("%Y-%m-%d"),   # A: Date Added
            lead_data.get("first_name", ""),        # B: First Name
            lead_data.get("last_name", ""),         # C: Last Name
            lead_data.get("service_requested", ""), # D: Business Name / Service
            lead_data.get("niche", ""),             # E: Industry
            lead_data.get("email", ""),             # F: Email
            lead_data.get("phone", ""),             # G: Phone
            "Portal",                               # H: Lead Source
        ]

        service.spreadsheets().values().append(
            spreadsheetId=sheet_id,
            range="LEADS!A:H",
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"values": [row]},
        ).execute()
    except Exception as e:
        print(f"[sheets] Failed to append lead to sheet {sheet_id}: {e}")
