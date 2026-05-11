import os
import json
import logging
from datetime import datetime

from google.oauth2 import service_account
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def append_lead_to_sheet(sheet_id, lead_data):
    creds_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")

    if not creds_json or creds_json == "placeholder":
        logger.warning("[sheets] GOOGLE_SERVICE_ACCOUNT_JSON is not configured — skipping sheet append")
        return None

    try:
        creds_dict = json.loads(creds_json)
        credentials = service_account.Credentials.from_service_account_info(
            creds_dict, scopes=SCOPES
        )
        service = build("sheets", "v4", credentials=credentials, cache_discovery=False)

        today = datetime.now().strftime("%m/%d/%Y")
        empty = ""
        row = [
            today,                                  # A: Date Added
            lead_data.get("first_name", ""),        # B: First Name
            lead_data.get("last_name", ""),         # C: Last Name
            lead_data.get("service_requested", ""), # D: Business Name / Service
            lead_data.get("niche", ""),             # E: Industry
            lead_data.get("email", ""),             # F: Email
            lead_data.get("phone", ""),             # G: Phone
            "Portal",                               # H: Lead Source
            empty, empty, empty, empty, empty,      # I–M
            empty, empty, empty, empty, empty,      # N–R
            empty, empty, empty,                    # S–U
        ]

        service.spreadsheets().values().append(
            spreadsheetId=sheet_id,
            range="LEADS!A:U",
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"values": [row]},
        ).execute()

        return True
    except Exception as e:
        logger.error(f"[sheets] Failed to append lead to sheet {sheet_id}: {e}")
        return None
